from __future__ import annotations

from models.train import Train
from src.planning.actions import Action
from src.planning.router import route
from src.railway.network import Network
from src.railway.occupancy import OccupancyState


class Scheduler:
    """Priority scheduler that also creates loop-crossing opportunities."""

    def decide_moves(
        self,
        trains: list[Train],
        network: Network,
        occupancy_state: OccupancyState,
    ) -> list[Action]:
        """Decide one action per active train for the current tick.

        Returns:
            A list of proposed `Action` objects in application order.
        """

        active = [train for train in trains if not train.finished]
        active_by_name = {train.name: train for train in active}
        forced_loop_reasons = self._forced_loop_reasons(active, active_by_name, network, occupancy_state)
        working_state = occupancy_state.clone()

        ordered_trains = self._ordered_trains(active, forced_loop_reasons)
        actions = []

        for train in ordered_trains:
            action = route(
                train,
                network,
                working_state,
                force_loop=train.name in forced_loop_reasons,
                force_loop_reason=forced_loop_reasons.get(train.name),
            )
            can_apply, _ = working_state.can_apply(action, train)
            if can_apply:
                working_state.apply_action(action, train, mutate_train=False)
            actions.append(action)

        return actions

    def _ordered_trains(self, active: list[Train], forced_loop_reasons: dict[str, str]) -> list[Train]:
        """Order trains so loop-clearing actions happen before regular moves.

        Returns:
            A train list ordered for safe action planning.
        """

        forced = [
            train
            for train in active
            if train.name in forced_loop_reasons
        ]
        regular = [
            train
            for train in active
            if train.name not in forced_loop_reasons
        ]

        forced.sort(key=lambda train: (train.priority, -train.waiting_time, train.name))
        regular.sort(key=lambda train: (-train.priority, -train.waiting_time, train.name))
        return forced + regular

    def _forced_loop_reasons(
        self,
        active: list[Train],
        active_by_name: dict[str, Train],
        network: Network,
        occupancy_state: OccupancyState,
    ) -> dict[str, str]:
        """Find lower-priority trains that should enter loops for crossings.

        Returns:
            A mapping from train name to the reason it should enter a loop.
        """

        forced = {}
        high_priority_order = sorted(
            active,
            key=lambda train: (-train.priority, -train.waiting_time, train.name),
        )

        for train in high_priority_order:
            if train.track != "main":
                continue

            next_station = network.next_station_for(train)
            if not network.is_valid_station(next_station):
                continue

            occupant_name = occupancy_state.occupied_train(next_station, "main")
            if occupant_name is None or occupant_name == train.name:
                continue

            blocker = active_by_name.get(occupant_name)
            if blocker is None:
                continue

            if blocker.priority >= train.priority:
                continue
            if blocker.track != "main":
                continue
            if blocker.direction() != -train.direction():
                continue
            if not network.has_loop(next_station):
                continue
            if not occupancy_state.is_berth_empty(next_station, "loop"):
                continue

            forced[blocker.name] = (
                f"enter loop at {network.station_name(next_station)} "
                f"to allow {train.name} to cross"
            )

        return forced
