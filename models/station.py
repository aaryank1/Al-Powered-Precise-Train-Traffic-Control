from dataclasses import dataclass


@dataclass
class Station:
    """Static station metadata used by the railway network."""

    name: str
    has_up_loop: bool = False
    has_down_loop: bool = False
    platform_count: int = 2

    def has_loop(self, direction: str) -> bool:
        """Return whether this station has a loop for the given direction."""

        if direction == "up":
            return self.has_up_loop
        if direction == "down":
            return self.has_down_loop
        raise ValueError(f"Unknown railway direction: {direction}.")
