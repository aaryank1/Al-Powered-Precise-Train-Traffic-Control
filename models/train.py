from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SLOW = "SLOW"
FAST = "FAST"
EXPRESS = "EXPRESS"


@dataclass(frozen=True)
class TrainProfile:
    """Simple timing characteristics shared by one train type."""

    running_ticks: int
    dwell_ticks: int


TRAIN_PROFILES = {
    SLOW: TrainProfile(running_ticks=2, dwell_ticks=1),
    FAST: TrainProfile(running_ticks=2, dwell_ticks=1),
    EXPRESS: TrainProfile(running_ticks=1, dwell_ticks=1),
}


@dataclass
class Train:
    """Mutable state for one train inside the controlled railway section."""

    name: str
    train_type: str
    priority: int

    current_station: int
    destination_station: int
    line: str = "main"
    scheduled_stops: tuple[int, ...] = ()

    waiting_time: int = 0
    finished: bool = False
    completion_time: Optional[int] = None
    loop_entries: int = 0
    target_station: Optional[int] = None
    remaining_travel_ticks: int = 0
    dwell_remaining_ticks: int = 0

    def __post_init__(self) -> None:
        """Normalize and validate the configured train type."""

        self.train_type = self.train_type.upper()
        if self.train_type not in TRAIN_PROFILES:
            allowed = ", ".join(TRAIN_PROFILES)
            raise ValueError(f"train_type must be one of: {allowed}.")

    @property
    def profile(self) -> TrainProfile:
        """Return the timing profile for this train type."""

        return TRAIN_PROFILES[self.train_type]

    @property
    def is_in_transit(self) -> bool:
        """Return whether the train currently occupies a directional block."""

        return self.target_station is not None

    def stops_at(self, station_index: int) -> bool:
        """Return whether this service is scheduled to stop at a station."""

        if station_index == self.destination_station:
            return True
        if self.train_type == SLOW:
            return True
        return station_index in self.scheduled_stops

    def begin_movement(self, target_station: int) -> None:
        """Place the train in transit toward an adjacent station."""

        if self.is_in_transit:
            raise ValueError(f"{self.name} is already in transit.")
        self.target_station = target_station
        self.remaining_travel_ticks = self.profile.running_ticks

    def direction(self) -> int:
        """Return the station-index step toward the destination.

        Returns:
            `1` for increasing station indexes, `-1` for decreasing indexes.
            The network maps this step to the railway's UP or DOWN direction.
        """

        if self.destination_station > self.current_station:
            return 1
        return -1

    def at_destination(self) -> bool:
        """Return whether the train is currently at its destination station.

        Returns:
            `True` when `current_station` equals `destination_station`.
        """

        return self.current_station == self.destination_station
