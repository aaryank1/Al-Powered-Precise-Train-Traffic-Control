from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.train import Train


class ActionType(str, Enum):
    """Allowed decisions that the scheduler can request for a train."""

    MOVE = "MOVE"
    WAIT = "WAIT"
    ENTER_LOOP = "ENTER_LOOP"
    EXIT_LOOP = "EXIT_LOOP"
    ARRIVE = "ARRIVE"


@dataclass(frozen=True)
class Action:
    """A validated or proposed train decision for one simulator tick."""

    train_name: str
    action_type: ActionType
    reason: str
    source_station: int | None = None
    target_station: int | None = None
    source_track: str | None = None
    target_track: str | None = None
    block: tuple[int, int] | None = None
    reservations: tuple[str, ...] = field(default_factory=tuple)
    conflict: bool = False

    def is_movement(self) -> bool:
        """Return whether this action moves across a track block.

        Returns:
            `True` for `MOVE` and `ARRIVE`; otherwise `False`.
        """

        return self.action_type in {ActionType.MOVE, ActionType.ARRIVE}


def wait_action(train: Train, reason: str, conflict: bool = False) -> Action:
    """Build a wait action for the train's current position.

    Returns:
        An `Action` with type `WAIT` and no resource reservations.
    """

    return Action(
        train_name=train.name,
        action_type=ActionType.WAIT,
        reason=reason,
        source_station=train.current_station,
        target_station=train.current_station,
        source_track=train.track,
        target_track=train.track,
        conflict=conflict,
    )
