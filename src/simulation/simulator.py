from __future__ import annotations

from typing import TypedDict

from models.train import Train
from src.planning.actions import Action, ActionType, wait_action
from src.planning.scheduler import Scheduler
from src.railway.network import Network
from src.railway.occupancy import OccupancyState

TICK_SECONDS = 30


class TrainMetrics(TypedDict):
    """Metrics collected for a single train."""

    finished: bool
    waiting_time: int
    completion_time: int | None
    completion_time_seconds: int | None
    current_station: str
    target_station: str | None
    line: str
    train_type: str
    status: str
    remaining_travel_ticks: int
    dwell_remaining_ticks: int
    waiting_seconds: int
    loop_entries: int


class SimulationMetrics(TypedDict):
    """Top-level simulator metrics."""

    total_ticks: int
    tick_seconds: int
    total_time_seconds: int
    arrived_trains: int
    active_trains: int
    throughput: float
    throughput_per_hour: float
    conflict_count: int
    loop_usage: int
    trains: dict[str, TrainMetrics]


class TickHistory(TypedDict):
    """Serializable simulator state captured after one tick."""

    time: int
    elapsed_seconds: int
    actions: list[Action]
    occupancy: dict[str, object]
    metrics: SimulationMetrics


class Simulator:
    """Discrete-tick simulator that validates and applies train actions."""

    def __init__(
        self,
        trains: list[Train],
        scheduler: Scheduler,
        network: Network,
        verbose: bool = True,
    ) -> None:
        """Create a simulator for trains, scheduler, and network."""

        self.trains = trains
        self.scheduler = scheduler
        self.network = network
        self.verbose = verbose
        self.time = 0
        self.history: list[TickHistory] = []
        self.conflict_count = 0
        self.loop_usage = 0
        self.occupancy_state = OccupancyState.from_trains(self.network, self.trains)

    def active_trains(self) -> list[Train]:
        """Return unfinished trains."""
        
        return [train for train in self.trains if not train.finished]

    def step(self) -> list[Action]:
        """Advance the simulation by one tick.

        Returns:
            The list of actions applied during this tick.
        """

        if not self.active_trains():
            return []

        tick_start = self.time
        if self.verbose:
            print(
                f"\nTIME tick={tick_start} "
                f"elapsed={self._format_seconds(tick_start * TICK_SECONDS)}"
            )

        self.occupancy_state = OccupancyState.from_trains(self.network, self.trains)
        actions = self.scheduler.decide_moves(
            self.trains,
            self.network,
            self.occupancy_state,
        )

        applied_actions = []
        trains_by_name = {train.name: train for train in self.trains}

        for action in actions:
            train = trains_by_name[action.train_name]
            if train.finished:
                continue

            can_apply, reason = self.occupancy_state.can_apply(action, train)
            if not can_apply:
                action = wait_action(
                    train,
                    f"invalid planned action blocked safely: {reason}",
                    conflict=True,
                )

            if action.conflict:
                self.conflict_count += 1
            if action.action_type == ActionType.ENTER_LOOP:
                self.loop_usage += 1

            self.occupancy_state.apply_action(
                action,
                train,
                mutate_train=True,
                current_time=self.time,
            )
            applied_actions.append(action)
            if self.verbose:
                print(self._format_action(action))

        arrival_actions = self._advance_in_transit()
        applied_actions.extend(arrival_actions)
        if self.verbose:
            for action in arrival_actions:
                print(self._format_action(action))

        self.time += 1
        self.occupancy_state = OccupancyState.from_trains(self.network, self.trains)
        self.history.append(
            {
                "time": tick_start,
                "elapsed_seconds": self.time * TICK_SECONDS,
                "actions": applied_actions,
                "occupancy": self.occupancy_state.snapshot(),
                "metrics": self.get_metrics(),
            }
        )
        return applied_actions

    def _advance_in_transit(self) -> list[Action]:
        """Advance all block traversals by one tick and complete arrivals."""

        arrivals = []
        for train in self.trains:
            if train.finished or not train.is_in_transit:
                continue

            train.remaining_travel_ticks -= 1
            if train.remaining_travel_ticks > 0:
                continue

            source_station = train.current_station
            target_station = train.target_station
            if target_station is None:
                raise ValueError(f"{train.name} has incomplete transit state.")

            block = self.network.block_between(source_station, target_station)
            train.current_station = target_station
            train.target_station = None
            train.remaining_travel_ticks = 0

            reached_destination = target_station == train.destination_station
            if reached_destination:
                train.finished = True
                train.completion_time = self.time + 1
                reason = "arrived at destination and left controlled section"
            elif train.stops_at(target_station):
                train.dwell_remaining_ticks = train.profile.dwell_ticks
                reason = f"arrived for scheduled {train.profile.dwell_ticks}-tick stop"
            else:
                train.dwell_remaining_ticks = 0
                reason = "passed station without a scheduled dwell"

            arrivals.append(
                Action(
                    train_name=train.name,
                    action_type=ActionType.ARRIVE,
                    reason=reason,
                    source_station=source_station,
                    target_station=target_station,
                    source_track=train.line,
                    target_track=train.line,
                    block=block.key,
                )
            )

        return arrivals

    def run(self, max_ticks: int = 100) -> SimulationMetrics:
        """Run ticks until every train arrives or a safety limit is reached.

        Returns:
            The final metrics dictionary from `get_metrics()`.

        Raises:
            RuntimeError: If active trains remain at `max_ticks`.
        """

        while self.active_trains():
            if self.time >= max_ticks:
                raise RuntimeError("Simulation did not finish before max_ticks.")
            self.step()
        return self.get_metrics()

    def get_metrics(self) -> SimulationMetrics:
        """Return current simulator and per-train metrics.

        Returns:
            A dictionary containing ticks, throughput, conflicts, loop usage,
            and per-train status.
        """

        arrived = [train for train in self.trains if train.finished]
        elapsed_seconds = self.time * TICK_SECONDS
        return {
            "total_ticks": self.time,
            "tick_seconds": TICK_SECONDS,
            "total_time_seconds": elapsed_seconds,
            "arrived_trains": len(arrived),
            "active_trains": len(self.trains) - len(arrived),
            "throughput": len(arrived) / self.time if self.time else 0,
            "throughput_per_hour": (
                len(arrived) * 3600 / elapsed_seconds if elapsed_seconds else 0
            ),
            "conflict_count": self.conflict_count,
            "loop_usage": self.loop_usage,
            "trains": {
                train.name: {
                    "finished": train.finished,
                    "waiting_time": train.waiting_time,
                    "waiting_seconds": train.waiting_time * TICK_SECONDS,
                    "completion_time": train.completion_time,
                    "completion_time_seconds": (
                        train.completion_time * TICK_SECONDS
                        if train.completion_time is not None
                        else None
                    ),
                    "current_station": self.network.station_name(train.current_station),
                    "target_station": (
                        self.network.station_name(train.target_station)
                        if train.target_station is not None
                        else None
                    ),
                    "line": train.line,
                    "train_type": train.train_type,
                    "status": self._train_status(train),
                    "remaining_travel_ticks": train.remaining_travel_ticks,
                    "dwell_remaining_ticks": train.dwell_remaining_ticks,
                    "loop_entries": train.loop_entries,
                }
                for train in self.trains
            },
        }

    def _format_action(self, action: Action) -> str:
        """Format an action for console output.

        Returns:
            A readable one-line action description.
        """

        source = (
            self.network.station_name(action.source_station)
            if action.source_station is not None
            else "-"
        )
        target = (
            self.network.station_name(action.target_station)
            if action.target_station is not None
            else "-"
        )

        if action.action_type == ActionType.MOVE:
            return f"{action.train_name}: departed {source} -> {target} ({action.reason})"

        if action.action_type == ActionType.ARRIVE:
            return f"{action.train_name}: arrived {source} -> {target} ({action.reason})"

        if action.action_type == ActionType.ENTER_LOOP:
            return (
                f"{action.train_name}: {source} {action.source_track} -> "
                f"{action.target_track} ({action.reason})"
            )

        if action.action_type == ActionType.EXIT_LOOP:
            return (
                f"{action.train_name}: {source} {action.source_track} -> "
                f"{action.target_track} ({action.reason})"
            )

        if action.action_type == ActionType.DWELL:
            return f"{action.train_name}: dwelling at {source} ({action.reason})"

        return f"{action.train_name}: waiting at {source} ({action.reason})"

    @staticmethod
    def _format_seconds(total_seconds: int) -> str:
        """Format elapsed simulation time as `HH:MM:SS`."""

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _train_status(train: Train) -> str:
        """Return a concise operational status for metrics and notebooks."""

        if train.finished:
            return "FINISHED"
        if train.is_in_transit:
            return "IN_TRANSIT"
        if train.dwell_remaining_ticks > 0:
            return "DWELLING"
        return "AT_STATION"
