from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from models.train import Train
from src.planning.actions import Action, ActionType
from src.railway.network import (
    DOWN,
    DOWN_LOOP,
    DOWN_MAIN,
    UP,
    UP_LOOP,
    UP_MAIN,
    BlockKey,
    Network,
)


class OccupancyState:
    """Current station, arrival-line, and persistent block occupancy."""

    def __init__(self, network: Network) -> None:
        """Initialize empty line and block occupancy for a network."""

        self.network = network
        self.station_lines: dict[tuple[int, str], str | None] = {}
        self.station_line_reservations: dict[tuple[int, str], str] = {}
        self.block_reservations: dict[BlockKey, str] = {}
        self.block_movements: dict[BlockKey, tuple[int, int, str]] = {}

        for station_index, station in enumerate(network.stations):
            self.station_lines[(station_index, UP_MAIN)] = None
            self.station_lines[(station_index, DOWN_MAIN)] = None
            if station.has_loop(UP):
                self.station_lines[(station_index, UP_LOOP)] = None
            if station.has_loop(DOWN):
                self.station_lines[(station_index, DOWN_LOOP)] = None

    @classmethod
    def from_trains(cls, network: Network, trains: Iterable[Train]) -> OccupancyState:
        """Build occupancy from all unfinished trains."""

        state = cls(network)
        for train in trains:
            if train.finished:
                continue
            line = network.normalize_train_line(train)
            if train.is_in_transit:
                if train.target_station is None:
                    raise ValueError(f"{train.name} has incomplete transit state.")
                block = network.block_between(train.current_station, train.target_station)
                state.reserve_block(
                    block.key,
                    train.name,
                    train.current_station,
                    train.target_station,
                )
                state.reserve_line(train.target_station, line, train.name)
            else:
                state.occupy_line(train.current_station, line, train.name)
        return state

    def clone(self) -> OccupancyState:
        """Return an independent copy for scheduler what-if planning."""

        cloned = OccupancyState(self.network)
        cloned.station_lines = deepcopy(self.station_lines)
        cloned.station_line_reservations = deepcopy(self.station_line_reservations)
        cloned.block_reservations = deepcopy(self.block_reservations)
        cloned.block_movements = deepcopy(self.block_movements)
        return cloned

    def line_exists(self, station_index: int, line: str) -> bool:
        """Return whether the requested directional line exists."""

        return (station_index, line) in self.station_lines

    def occupied_train(self, station_index: int, line: str) -> str | None:
        """Return the train occupying a station line, if any."""

        return self.station_lines.get((station_index, line))

    def is_line_empty(self, station_index: int, line: str) -> bool:
        """Return whether a station line has no train."""

        return self.occupied_train(station_index, line) is None

    def reserved_for(self, station_index: int, line: str) -> str | None:
        """Return the train holding an arrival reservation for a line."""

        return self.station_line_reservations.get((station_index, line))

    def is_line_available(self, station_index: int, line: str) -> bool:
        """Return whether a line is neither occupied nor reserved."""

        return self.is_line_empty(station_index, line) and self.reserved_for(
            station_index, line
        ) is None

    def occupy_line(self, station_index: int, line: str, train_name: str) -> None:
        """Mark a station line as occupied by a train."""

        if not self.line_exists(station_index, line):
            raise ValueError(f"{line} does not exist at station {station_index}.")
        if not self.is_line_available(station_index, line):
            raise ValueError(f"{line} at station {station_index} is occupied or reserved.")
        self.station_lines[(station_index, line)] = train_name

    def reserve_line(self, station_index: int, line: str, train_name: str) -> None:
        """Reserve a destination line while a train traverses its block."""

        if not self.line_exists(station_index, line):
            raise ValueError(f"{line} does not exist at station {station_index}.")
        if not self.is_line_available(station_index, line):
            raise ValueError(f"{line} at station {station_index} is occupied or reserved.")
        self.station_line_reservations[(station_index, line)] = train_name

    def release_line(self, station_index: int, line: str, train_name: str) -> None:
        """Release a line currently occupied by a train."""

        if self.occupied_train(station_index, line) != train_name:
            raise ValueError(f"{train_name} does not occupy {line} at station {station_index}.")
        self.station_lines[(station_index, line)] = None

    def can_reserve_block(
        self,
        block_key: BlockKey,
        train_name: str,
        source_station: int,
        target_station: int,
    ) -> tuple[bool, str]:
        """Check whether one directional block is available this tick."""

        if block_key in self.block_movements:
            _, _, existing_train = self.block_movements[block_key]
            return False, f"directional block already reserved by {existing_train}"
        return True, "directional block available"

    def reserve_block(
        self,
        block_key: BlockKey,
        train_name: str,
        source_station: int,
        target_station: int,
    ) -> None:
        """Reserve one directional block for a train movement this tick."""

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
        """Check whether an action is safe against current occupancy."""

        if action.action_type == ActionType.WAIT:
            return True, "waits do not reserve resources"

        if action.action_type == ActionType.DWELL:
            if train.is_in_transit:
                return False, "a train cannot dwell while in transit"
            if train.dwell_remaining_ticks <= 0:
                return False, "scheduled dwell is already complete"
            if self.occupied_train(train.current_station, train.line) != train.name:
                return False, "dwelling train does not occupy its station line"
            return True, "scheduled dwell in progress"

        direction = self.network.direction_for(train)
        main_line = self.network.main_line_for(train)
        loop_line = self.network.loop_line_for(train)

        if action.action_type == ActionType.ENTER_LOOP:
            if not self.network.has_loop(train.current_station, direction):
                return False, f"station has no {direction.upper()} loop line"
            if action.source_track != main_line or action.target_track != loop_line:
                return False, f"loop entry must move from {main_line} to {loop_line}"
            if self.occupied_train(train.current_station, main_line) != train.name:
                return False, f"train is not on {main_line}"
            if not self.is_line_available(train.current_station, loop_line):
                return False, f"{loop_line} is already occupied"
            return True, f"{loop_line} available"

        if action.action_type == ActionType.EXIT_LOOP:
            if not self.network.has_loop(train.current_station, direction):
                return False, f"station has no {direction.upper()} loop line"
            if action.source_track != loop_line or action.target_track != main_line:
                return False, f"loop exit must move from {loop_line} to {main_line}"
            if self.occupied_train(train.current_station, loop_line) != train.name:
                return False, f"train is not in {loop_line}"
            if not self.is_line_available(train.current_station, main_line):
                return False, f"{main_line} is occupied"
            return True, f"{main_line} available"

        if action.action_type == ActionType.MOVE:
            if (
                action.source_station is None
                or action.target_station is None
                or action.source_track is None
                or action.target_track is None
                or action.block is None
            ):
                return False, "movement action is missing a station, line, or block"
            if action.source_track != main_line or action.target_track != main_line:
                return False, f"movement must remain on {main_line}"
            try:
                expected_block = self.network.block_between(
                    action.source_station,
                    action.target_station,
                ).key
            except ValueError as error:
                return False, str(error)
            if action.block != expected_block:
                return False, f"movement must reserve directional block {expected_block}"
            if self.occupied_train(action.source_station, main_line) != train.name:
                return False, f"train must start movement from {main_line}"
            if not self.is_line_available(action.target_station, main_line):
                occupant = self.occupied_train(action.target_station, main_line)
                reserver = self.reserved_for(action.target_station, main_line)
                blocker = occupant or reserver
                return False, f"target station {main_line} occupied or reserved by {blocker}"
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
        """Apply a safe action to occupancy and optionally to train state."""

        can_apply, reason = self.can_apply(action, train)
        if not can_apply:
            raise ValueError(reason)

        if action.action_type == ActionType.WAIT:
            if mutate_train:
                train.waiting_time += 1
            return

        if action.action_type == ActionType.DWELL:
            if mutate_train:
                train.dwell_remaining_ticks -= 1
            return

        main_line = self.network.main_line_for(train)
        loop_line = self.network.loop_line_for(train)

        if action.action_type == ActionType.ENTER_LOOP:
            self.release_line(train.current_station, main_line, train.name)
            self.occupy_line(train.current_station, loop_line, train.name)
            if mutate_train:
                train.line = loop_line
                train.loop_entries += 1
                if train.dwell_remaining_ticks > 0:
                    train.dwell_remaining_ticks -= 1
            return

        if action.action_type == ActionType.EXIT_LOOP:
            self.release_line(train.current_station, loop_line, train.name)
            self.occupy_line(train.current_station, main_line, train.name)
            if mutate_train:
                train.line = main_line
            return

        if action.action_type == ActionType.MOVE:
            if action.source_station is None or action.target_station is None or action.block is None:
                raise ValueError("movement action is missing source, target, or block")

            self.release_line(action.source_station, main_line, train.name)
            self.reserve_block(action.block, train.name, action.source_station, action.target_station)
            self.reserve_line(action.target_station, main_line, train.name)

            if mutate_train:
                train.line = main_line
                train.begin_movement(action.target_station)

    def snapshot(self) -> dict[str, object]:
        """Return a serializable view of line and block occupancy."""

        stations = []
        for station_index, station in enumerate(self.network.stations):
            row = {
                "station": station.name,
                UP_MAIN: self.occupied_train(station_index, UP_MAIN),
                DOWN_MAIN: self.occupied_train(station_index, DOWN_MAIN),
            }
            if station.has_loop(UP):
                row[UP_LOOP] = self.occupied_train(station_index, UP_LOOP)
            if station.has_loop(DOWN):
                row[DOWN_LOOP] = self.occupied_train(station_index, DOWN_LOOP)
            stations.append(row)

        return {
            "stations": stations,
            "blocks": dict(self.block_reservations),
            "line_reservations": dict(self.station_line_reservations),
        }
