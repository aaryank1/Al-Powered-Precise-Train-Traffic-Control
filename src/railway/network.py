from __future__ import annotations
from dataclasses import dataclass
from models.station import Station
from models.train import Train

UP = "up"
DOWN = "down"
UP_MAIN = "up_main"
DOWN_MAIN = "down_main"
UP_LOOP = "up_loop"
DOWN_LOOP = "down_loop"

BlockKey = tuple[int, int, str]


@dataclass(frozen=True)
class Block:
    """One directional running-line section between adjacent stations."""

    start: int
    end: int
    direction: str

    @property
    def key(self) -> BlockKey:
        """Return the physical section and directional line identifier.

        Returns:
            A key such as `(2, 3, "up")`. UP and DOWN blocks between the
            same stations are distinct parallel resources.
        """

        return (min(self.start, self.end), max(self.start, self.end), self.direction)


class Network:
    """Ordered stations and directional tracks for one controlled section."""

    def __init__(self, stations: list[Station], up_index_direction: int = 1) -> None:
        """Create a network from stations ordered along the section.

        `up_index_direction` declares which station-index step is railway UP.
        For the default Virar-Dadar section, increasing indexes run toward
        Churchgate and are therefore UP.

        Returns:
            `None`; the network stores the station list on `self.stations`.
        """

        if up_index_direction not in {-1, 1}:
            raise ValueError("up_index_direction must be either 1 or -1.")
        self.stations = stations
        self.up_index_direction = up_index_direction

    def station_name(self, station_index: int) -> str:
        """Return the display name for a station index."""

        return self.stations[station_index].name

    def direction_for_step(self, index_step: int) -> str:
        """Map a station-index step to the designated UP or DOWN direction."""

        if index_step not in {-1, 1}:
            raise ValueError("A train direction step must be either 1 or -1.")
        return UP if index_step == self.up_index_direction else DOWN

    def direction_for(self, train: Train) -> str:
        """Return the designated railway direction for a train."""

        return self.direction_for_step(train.direction())

    def main_line_for(self, train: Train) -> str:
        """Return the directional main line used by a train."""

        return UP_MAIN if self.direction_for(train) == UP else DOWN_MAIN

    def loop_line_for(self, train: Train) -> str:
        """Return the directional loop line used by a train."""

        return UP_LOOP if self.direction_for(train) == UP else DOWN_LOOP

    def normalize_train_line(self, train: Train) -> str:
        """Resolve the legacy `main` value and validate a directional line."""

        expected_main = self.main_line_for(train)
        expected_loop = self.loop_line_for(train)
        if train.line == "main":
            train.line = expected_main
        if train.line not in {expected_main, expected_loop}:
            raise ValueError(
                f"{train.name} travels {self.direction_for(train).upper()} but is on {train.line}."
            )
        return train.line

    def has_loop(self, station_index: int, direction: str) -> bool:
        """Return whether a station has a loop for one direction."""

        return self.stations[station_index].has_loop(direction)

    def is_valid_station(self, station_index: int) -> bool:
        """Return whether the station index exists in this network."""

        return 0 <= station_index < len(self.stations)

    def next_station_for(self, train: Train) -> int:
        """Return the next station index on a train's path."""

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
        direction = self.direction_for_step(target_station - source_station)
        return Block(source_station, target_station, direction)

    def describe_block(self, block_key: BlockKey) -> str:
        """Return a human-readable block name.

        Returns:
            A string like `Borivali-Andheri:UP`.
        """

        source, target, direction = block_key
        return f"{self.station_name(source)}-{self.station_name(target)}:{direction.upper()}"


default_network = Network(
    [
        Station("Virar"),
        Station("Bhayandar"),
        Station("Borivali", has_up_loop=True, has_down_loop=True),
        Station("Andheri", has_up_loop=True, has_down_loop=True),
        Station("Bandra"),
        Station("Dadar"),
    ],
    up_index_direction=1,
)

stations = default_network.stations
