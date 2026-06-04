from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from models.train import Train
from src.planning.actions import Action, ActionType
from src.railway.network import Network

MAIN = "main"
LOOP = "loop"

class OccupancyState:
    """Current station occupancy and per-tick block reservations."""

    def __init__(self, network: Network) -> None:
        """Initialize empty line and block occupancy for a network.

        Returns:
            `None`; empty occupancy maps are stored on the instance.
        """

        self.network = network
        self.station_lines: dict[tuple[int, str], str | None] = {}
        self.block_reservations: dict[tuple[int, int], str] = {}
        self.block_movements: dict[tuple[int, int], tuple[int, int, str]] = {}

        for station_index, station in enumerate(network.stations):
            self.station_lines[(station_index, MAIN)] = None
            if station.has_loop:
                self.station_lines[(station_index, LOOP)] = None

    @classmethod
    def from_trains(cls, network: Network, trains: Iterable[Train]) -> OccupancyState:
        """Build occupancy from all unfinished trains.

        Returns:
            An `OccupancyState` with current train lines occupied.
        """

        state = cls(network)
        for train in trains:
            if train.finished:
                continue
            state.occupy_line(train.current_station, train.line, train.name)
        return state

    def clone(self) -> OccupancyState:
        """Return a deep copy used for scheduler what-if planning.

        Returns:
            A cloned `OccupancyState` with independent occupancy maps.
        """

        cloned = OccupancyState(self.network)
        cloned.station_lines = deepcopy(self.station_lines)
        cloned.block_reservations = deepcopy(self.block_reservations)
        cloned.block_movements = deepcopy(self.block_movements)
        return cloned

    def line_exists(self, station_index: int, line: str) -> bool:
        """Return whether the station has the requested line.

        Returns:
            `True` when the lines key exists.
        """

        return (station_index, line) in self.station_lines

    def occupied_train(self, station_index: int, line: str = MAIN) -> str | None:
        """Return the train occupying a station line.

        Returns:
            The train name, or `None` when the line is empty or absent.
        """

        return self.station_lines.get((station_index, line))

    def is_line_empty(self, station_index: int, line: str = MAIN) -> bool:
        """Return whether a station line has no train.

        Returns:
            `True` when `occupied_train()` returns `None`.
        """

        return self.occupied_train(station_index, line) is None

    def occupy_line(self, station_index: int, line: str, train_name: str) -> None:
        """Mark a station line as occupied by a train.

        Returns:
            `None`; the line map is updated in place.
        """

        if not self.line_exists(station_index, line):
            raise ValueError(f"{line} line does not exist at station {station_index}.")
        if not self.is_line_empty(station_index, line):
            raise ValueError(f"{line} line at station {station_index} is already occupied.")
        self.station_lines[(station_index, line)] = train_name

    def release_lines(self, station_index: int, line: str, train_name: str) -> None:
        """Release a line currently occupied by a train.

        Returns:
            `None`; the lines map is updated in place.

        Raises:
            ValueError: If another train or no train occupies the lines.
        """

        if self.occupied_train(station_index, line) != train_name:
            raise ValueError(f"{train_name} does not occupy {line} at station {station_index}.")
        self.station_lines[(station_index, line)] = None

    def can_reserve_block(
        self,
        block_key: tuple[int, int],
        train_name: str,
        source_station: int,
        target_station: int,
    ) -> tuple[bool, str]:
        """Check whether a train may reserve a block this tick.

        Returns:
            `(True, reason)` when available, otherwise `(False, reason)`.
        """

        if block_key in self.block_movements:
            existing_source, existing_target, existing_train = self.block_movements[block_key]
            if existing_source == target_station and existing_target == source_station:
                return (
                    False,
                    f"opposite-direction block swap blocked by {existing_train}",
                )
            return False, f"block already reserved by {existing_train}"
        return True, "block available"

    def reserve_block(
        self,
        block_key: tuple[int, int],
        train_name: str,
        source_station: int,
        target_station: int,
    ) -> None:
        """Reserve a block for one train movement during this tick.

        Returns:
            `None`; block reservation maps are updated in place.

        Raises:
            ValueError: If the block is already reserved.
        """

        can_reserve, reason = self.can_reserve_block(
            block_key,
            train_name,
            source_station,
            target_station,
        )
        if not can_reserve:
            raise ValueError(reason)

        self.block_reservations[block_key] = train_name
        self.block_movements[block_key] = (source_station, target_station, train_name)

    def can_apply(self, action: Action, train: Train) -> tuple[bool, str]:
        """Check whether an action is safe against current occupancy.

        Returns:
            `(True, reason)` when the action is safe, otherwise `(False, reason)`.
        """

        if action.action_type == ActionType.WAIT:
            return True, "waits do not reserve resources"

        if action.action_type == ActionType.ENTER_LOOP:
            if not self.network.has_loop(train.current_station):
                return False, "station has no loop line"
            if self.occupied_train(train.current_station, MAIN) != train.name:
                return False, "train is not on station main line"
            if not self.is_line_empty(train.current_station, LOOP):
                return False, "loop line is already occupied"
            return True, "loop line available"

        if action.action_type == ActionType.EXIT_LOOP:
            if not self.network.has_loop(train.current_station):
                return False, "station has no loop line"
            if self.occupied_train(train.current_station, LOOP) != train.name:
                return False, "train is not in loop line"
            if not self.is_line_empty(train.current_station, MAIN):
                return False, "station main line is occupied"
            return True, "main line available"

        if action.action_type in {ActionType.MOVE, ActionType.ARRIVE}:
            if action.source_station is None or action.target_station is None or action.block is None:
                return False, "movement action is missing source, target, or block"
            if self.occupied_train(action.source_station, MAIN) != train.name:
                return False, "train must start movement from station main line"
            if not self.is_line_empty(action.target_station, MAIN):
                occupant = self.occupied_train(action.target_station, MAIN)
                return False, f"target station main line occupied by {occupant}"
            can_reserve, reason = self.can_reserve_block(
                action.block,
                train.name,
                action.source_station,
                action.target_station,
            )
            if not can_reserve:
                return False, reason
            return True, "movement resources available"

        return False, "unknown action type"

    def apply_action(
        self,
        action: Action,
        train: Train,
        mutate_train: bool = True,
        current_time: int = 0,
    ) -> None:
        """Apply a safe action to occupancy and optionally to train state.

        Returns:
            `None`; occupancy and optionally train fields are mutated.

        Raises:
            ValueError: If `can_apply()` rejects the action.
        """

        can_apply, reason = self.can_apply(action, train)
        if not can_apply:
            raise ValueError(reason)

        if action.action_type == ActionType.WAIT:
            if mutate_train:
                train.waiting_time += 1
            return

        if action.action_type == ActionType.ENTER_LOOP:
            self.release_lines(train.current_station, MAIN, train.name)
            self.occupy_line(train.current_station, LOOP, train.name)
            if mutate_train:
                train.line = LOOP
                train.loop_entries += 1
            return

        if action.action_type == ActionType.EXIT_LOOP:
            self.release_lines(train.current_station, LOOP, train.name)
            self.occupy_line(train.current_station, MAIN, train.name)
            if mutate_train:
                train.line = MAIN
            return

        if action.action_type in {ActionType.MOVE, ActionType.ARRIVE}:
            if action.source_station is None or action.target_station is None or action.block is None:
                raise ValueError("movement action is missing source, target, or block")

            self.release_lines(action.source_station, MAIN, train.name)
            self.reserve_block(action.block, train.name, action.source_station, action.target_station)
            self.occupy_line(action.target_station, MAIN, train.name)

            if mutate_train:
                train.current_station = action.target_station
                train.line = MAIN
                if action.action_type == ActionType.ARRIVE:
                    train.finished = True
                    train.completion_time = current_time + 1

    def snapshot(self) -> dict[str, object]:
        """Return a serializable view of station and block occupancy.

        Returns:
            A dictionary with `stations` and `blocks` entries for debugging.
        """

        stations = []
        for station_index, station in enumerate(self.network.stations):
            row = {
                "station": station.name,
                MAIN: self.occupied_train(station_index, MAIN),
            }
            if station.has_loop:
                row[LOOP] = self.occupied_train(station_index, LOOP)
            stations.append(row)

        return {
            "stations": stations,
            "blocks": dict(self.block_reservations),
        }
