from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Train:
    """Mutable state for one train inside the controlled railway section."""

    name: str
    train_type: str
    priority: int

    current_station: int
    destination_station: int
    line: str = "main"

    waiting_time: int = 0
    finished: bool = False
    completion_time: Optional[int] = None
    loop_entries: int = 0

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
