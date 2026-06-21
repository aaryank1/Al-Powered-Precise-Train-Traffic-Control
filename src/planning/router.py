from __future__ import annotations

from models.train import Train
from src.planning.actions import Action, ActionType, wait_action
from src.railway.network import BlockKey, Network
from src.railway.occupancy import OccupancyState


def _resource_names(
    network: Network,
    block_key: BlockKey | None,
    target_station: int | None = None,
    target_track: str | None = None,
) -> tuple[str, ...]:
    """Build human-readable resource reservation names.

    Returns:
        A tuple of strings such as `block:Borivali-Andheri`.
    """

    resources = []
    if block_key is not None:
        resources.append(f"block:{network.describe_block(block_key)}")
    if target_station is not None and target_track is not None:
        resources.append(f"station:{network.station_name(target_station)}:{target_track}")
    return tuple(resources)


def _movement_conflict(train: Train, network: Network, occupancy_state: OccupancyState) -> bool:
    """Detect whether the train's desired movement is a conflict.

    Returns:
        `True` when the next station or next block is unavailable.
    """

    next_station = network.next_station_for(train)
    if not network.is_valid_station(next_station):
        return False

    main_line = network.main_line_for(train)
    occupant = occupancy_state.occupied_train(next_station, main_line)
    if occupant is not None and occupant != train.name:
        return True

    block = network.block_between(train.current_station, next_station)
    can_reserve, reason = occupancy_state.can_reserve_block(
        block.key,
        train.name,
        train.current_station,
        next_station,
    )
    return not can_reserve


def candidate_actions(
    train: Train,
    network: Network,
    occupancy_state: OccupancyState,
    force_loop: bool = False,
    force_loop_reason: str | None = None,
) -> list[Action]:
    """Return safe action candidates for a train in the current tick.

    Returns:
        A list containing the best current action; the list shape leaves room
        for future multi-candidate routing.
    """

    if train.finished:
        return [wait_action(train, "train already finished")]

    main_line = network.main_line_for(train)
    loop_line = network.loop_line_for(train)

    if train.line == loop_line:
        action = Action(
            train_name=train.name,
            action_type=ActionType.EXIT_LOOP,
            reason="exit directional loop after overtaking path is clear",
            source_station=train.current_station,
            target_station=train.current_station,
            source_track=loop_line,
            target_track=main_line,
            reservations=_resource_names(
                network,
                None,
                train.current_station,
                main_line,
            ),
        )
        can_apply, reason = occupancy_state.can_apply(action, train)
        if can_apply:
            return [action]
        return [wait_action(train, reason, conflict=True)]

    if force_loop:
        action = Action(
            train_name=train.name,
            action_type=ActionType.ENTER_LOOP,
            reason=force_loop_reason or "enter directional loop to allow overtaking",
            source_station=train.current_station,
            target_station=train.current_station,
            source_track=main_line,
            target_track=loop_line,
            reservations=_resource_names(
                network,
                None,
                train.current_station,
                loop_line,
            ),
        )
        can_apply, reason = occupancy_state.can_apply(action, train)
        if can_apply:
            return [action]
        return [wait_action(train, reason, conflict=True)]

    next_station = network.next_station_for(train)
    if not network.is_valid_station(next_station):
        return [wait_action(train, "next station is outside the network", conflict=True)]

    block = network.block_between(train.current_station, next_station)
    action_type = ActionType.ARRIVE if next_station == train.destination_station else ActionType.MOVE
    reason = (
        "move into destination and leave controlled section"
        if action_type == ActionType.ARRIVE
        else "advance toward destination"
    )
    action = Action(
        train_name=train.name,
        action_type=action_type,
        reason=reason,
        source_station=train.current_station,
        target_station=next_station,
        source_track=main_line,
        target_track=main_line,
        block=block.key,
        reservations=_resource_names(network, block.key, next_station, main_line),
    )
    can_apply, blocked_reason = occupancy_state.can_apply(action, train)
    if can_apply:
        return [action]

    return [wait_action(train, blocked_reason, conflict=_movement_conflict(train, network, occupancy_state))]


def route(
    train: Train,
    network: Network,
    occupancy_state: OccupancyState,
    force_loop: bool = False,
    force_loop_reason: str | None = None,
) -> Action:
    """Choose the best safe action for a train.

    Returns:
        The first action from `candidate_actions()` for the current v1 router.
    """

    return candidate_actions(
        train,
        network,
        occupancy_state,
        force_loop=force_loop,
        force_loop_reason=force_loop_reason,
    )[0]
