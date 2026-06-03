from __future__ import annotations

from dataclasses import dataclass

from models.station import Station
from models.train import Train


@dataclass(frozen=True)
class Block:
    """A single-track section between two adjacent stations."""

    start: int
    end: int

    @property
    def key(self) -> tuple[int, int]:
        """Return the direction-independent identifier for this block.

        Returns:
            A sorted pair of station indexes, for example `(2, 3)`.
        """

        return tuple(sorted((self.start, self.end)))


class Network:
    """Ordered stations and block helpers for one controlled section."""

    def __init__(self, stations: list[Station]) -> None:
        """Create a network from stations ordered along the section.

        Returns:
            `None`; the network stores the station list on `self.stations`.
        """

        self.stations = stations

    def station_name(self, station_index: int) -> str:
        """Return the display name for a station index.

        Returns:
            The station name string.
        """

        return self.stations[station_index].name

    def has_loop(self, station_index: int) -> bool:
        """Return whether a station has a loop berth.

        Returns:
            `True` when the station supports loop-line holding.
        """

        return self.stations[station_index].has_loop

    def is_valid_station(self, station_index: int) -> bool:
        """Return whether the station index exists in this network.

        Returns:
            `True` if the index is inside the station list bounds.
        """

        return 0 <= station_index < len(self.stations)

    def next_station_for(self, train: Train) -> int:
        """Return the next station index on a train's path.

        Returns:
            The adjacent station index in the train's direction of travel.
        """

        return train.current_station + train.direction()

    def block_between(self, source_station: int, target_station: int) -> Block:
        """Return the adjacent block connecting two station indexes.

        Returns:
            A `Block` between the source and target stations.

        Raises:
            ValueError: If the stations are invalid or not adjacent.
        """

        if abs(source_station - target_station) != 1:
            raise ValueError("Blocks only exist between adjacent stations.")
        if not self.is_valid_station(source_station):
            raise ValueError("Source station is outside the network.")
        if not self.is_valid_station(target_station):
            raise ValueError("Target station is outside the network.")
        return Block(source_station, target_station)

    def describe_block(self, block_key: tuple[int, int]) -> str:
        """Return a human-readable block name.

        Returns:
            A string like `Borivali-Andheri`.
        """

        source, target = block_key
        return f"{self.station_name(source)}-{self.station_name(target)}"


default_network = Network(
    [
        Station("Virar", False),
        Station("Bhayandar", False),
        Station("Borivali", True),
        Station("Andheri", True),
        Station("Bandra", False),
        Station("Dadar", False),
    ]
)

stations = default_network.stations
