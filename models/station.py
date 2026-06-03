from dataclasses import dataclass


@dataclass
class Station:
    """Static station metadata used by the railway network."""

    name: str
    has_loop: bool
    platform_count: int = 1
