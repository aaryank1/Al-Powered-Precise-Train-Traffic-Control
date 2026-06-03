from __future__ import annotations

from models.train import Train
from src.planning.actions import Action, ActionType, wait_action
from src.planning.scheduler import Scheduler
from src.railway.network import Network, default_network
from src.railway.occupancy import OccupancyState


class Simulator:
    """Discrete-tick simulator that validates and applies train actions."""

    def __init__(
        self,
        trains: list[Train],
        scheduler: Scheduler,
        network: Network | None = None,
        verbose: bool = True,
    ) -> None:
        """Create a simulator for trains, scheduler, and network."""

        self.trains = trains
        self.scheduler = scheduler
        self.network = network or default_network
        self.verbose = verbose
        self.time = 0
        self.history: list[dict[str, object]] = []
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

        if self.verbose:
            print(f"\nTIME {self.time}")

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

        self.history.append(
            {
                "time": self.time,
                "actions": applied_actions,
                "occupancy": self.occupancy_state.snapshot(),
                "metrics": self.get_metrics(),
            }
        )
        self.time += 1
        return applied_actions

    def run(self, max_ticks: int = 100) -> dict[str, object]:
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

    def get_metrics(self) -> dict[str, object]:
        """Return current simulator and per-train metrics.

        Returns:
            A dictionary containing ticks, throughput, conflicts, loop usage,
            and per-train status.
        """

        arrived = [train for train in self.trains if train.finished]
        return {
            "total_ticks": self.time,
            "arrived_trains": len(arrived),
            "active_trains": len(self.trains) - len(arrived),
            "throughput": len(arrived) / self.time if self.time else 0,
            "conflict_count": self.conflict_count,
            "loop_usage": self.loop_usage,
            "trains": {
                train.name: {
                    "finished": train.finished,
                    "waiting_time": train.waiting_time,
                    "completion_time": train.completion_time,
                    "current_station": self.network.station_name(train.current_station),
                    "track": train.track,
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

        if action.action_type in {ActionType.MOVE, ActionType.ARRIVE}:
            suffix = " arrived" if action.action_type == ActionType.ARRIVE else ""
            return f"{action.train_name}: {source} -> {target}{suffix} ({action.reason})"

        if action.action_type == ActionType.ENTER_LOOP:
            return f"{action.train_name}: {source} main -> loop ({action.reason})"

        if action.action_type == ActionType.EXIT_LOOP:
            return f"{action.train_name}: {source} loop -> main ({action.reason})"

        return f"{action.train_name}: waiting at {source} ({action.reason})"
