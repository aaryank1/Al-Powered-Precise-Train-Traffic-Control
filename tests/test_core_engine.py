import unittest

from models.station import Station
from models.train import Train
from scenarios.scenario_1 import build_trains
from src.planning.actions import Action, ActionType
from src.planning.scheduler import Scheduler
from src.railway.network import (
    DOWN,
    DOWN_LOOP,
    DOWN_MAIN,
    UP,
    UP_LOOP,
    UP_MAIN,
    Network,
    default_network,
)
from src.railway.occupancy import OccupancyState
from src.simulation.simulator import Simulator


class CoreEngineTest(unittest.TestCase):
    """Directional-line occupancy and overtaking safety tests."""

    def test_default_network_maps_virar_to_dadar_as_up(self) -> None:
        up_train = Train("UP", "LOCAL", 1, current_station=0, destination_station=5)
        down_train = Train("DOWN", "LOCAL", 1, current_station=5, destination_station=0)

        self.assertEqual(default_network.direction_for(up_train), UP)
        self.assertEqual(default_network.direction_for(down_train), DOWN)
        self.assertEqual(default_network.main_line_for(up_train), UP_MAIN)
        self.assertEqual(default_network.main_line_for(down_train), DOWN_MAIN)

    def test_opposite_directions_have_independent_parallel_blocks(self) -> None:
        up_block = default_network.block_between(2, 3)
        down_block = default_network.block_between(3, 2)
        state = OccupancyState(default_network)

        state.reserve_block(up_block.key, "UP", 2, 3)
        can_reserve, _ = state.can_reserve_block(down_block.key, "DOWN", 3, 2)

        self.assertNotEqual(up_block.key, down_block.key)
        self.assertTrue(can_reserve)

    def test_only_one_train_can_reserve_each_directional_block_per_tick(self) -> None:
        block = default_network.block_between(0, 1)
        state = OccupancyState(default_network)
        state.reserve_block(block.key, "UP1", 0, 1)

        can_reserve, reason = state.can_reserve_block(block.key, "UP2", 0, 1)

        self.assertFalse(can_reserve)
        self.assertIn("directional block", reason)

    def test_up_and_down_station_mains_are_independent(self) -> None:
        state = OccupancyState(default_network)
        state.occupy_line(0, UP_MAIN, "UP1")
        state.occupy_line(0, DOWN_MAIN, "DOWN1")

        self.assertEqual(state.occupied_train(0, UP_MAIN), "UP1")
        self.assertEqual(state.occupied_train(0, DOWN_MAIN), "DOWN1")

        with self.assertRaises(ValueError):
            state.occupy_line(0, UP_MAIN, "UP2")

    def test_directional_loops_exist_only_where_configured(self) -> None:
        self.assertTrue(default_network.has_loop(2, UP))
        self.assertTrue(default_network.has_loop(2, DOWN))
        self.assertFalse(default_network.has_loop(1, UP))

    def test_train_can_enter_only_its_directional_loop(self) -> None:
        train = Train("UP1", "LOCAL", 1, current_station=2, destination_station=5)
        state = OccupancyState.from_trains(default_network, [train])
        action = Action(
            train_name=train.name,
            action_type=ActionType.ENTER_LOOP,
            reason="test directional loop",
            source_station=2,
            target_station=2,
            source_track=UP_MAIN,
            target_track=UP_LOOP,
        )

        can_apply, _ = state.can_apply(action, train)

        self.assertTrue(can_apply)

    def test_higher_priority_up_train_overtakes_through_up_loop(self) -> None:
        trains = [
            Train("UP_EXP", "EXPRESS", 10, current_station=1, destination_station=5),
            Train("UP_LOC", "LOCAL", 1, current_station=2, destination_station=5),
        ]
        sim = Simulator(trains, Scheduler(), network=default_network, verbose=False)

        actions = sim.step()

        actions_by_train = {action.train_name: action for action in actions}
        self.assertEqual(actions_by_train["UP_LOC"].action_type, ActionType.ENTER_LOOP)
        self.assertEqual(actions_by_train["UP_EXP"].action_type, ActionType.MOVE)
        self.assertEqual(trains[0].current_station, 2)
        self.assertEqual(trains[1].line, UP_LOOP)

    def test_higher_priority_down_train_overtakes_through_down_loop(self) -> None:
        trains = [
            Train("DOWN_EXP", "EXPRESS", 10, current_station=3, destination_station=0),
            Train("DOWN_LOC", "LOCAL", 1, current_station=2, destination_station=0),
        ]
        sim = Simulator(trains, Scheduler(), network=default_network, verbose=False)

        actions = sim.step()

        actions_by_train = {action.train_name: action for action in actions}
        self.assertEqual(actions_by_train["DOWN_LOC"].action_type, ActionType.ENTER_LOOP)
        self.assertEqual(actions_by_train["DOWN_EXP"].action_type, ActionType.MOVE)
        self.assertEqual(trains[0].current_station, 2)
        self.assertEqual(trains[1].line, DOWN_LOOP)

    def test_movement_rejects_a_block_from_the_wrong_direction(self) -> None:
        train = Train("UP1", "LOCAL", 1, current_station=2, destination_station=5)
        state = OccupancyState.from_trains(default_network, [train])
        wrong_block = default_network.block_between(3, 2).key
        action = Action(
            train_name=train.name,
            action_type=ActionType.MOVE,
            reason="invalid test movement",
            source_station=2,
            target_station=3,
            source_track=UP_MAIN,
            target_track=UP_MAIN,
            block=wrong_block,
        )

        can_apply, reason = state.can_apply(action, train)

        self.assertFalse(can_apply)
        self.assertIn("must reserve directional block", reason)

    def test_default_mixed_direction_scenario_completes_safely(self) -> None:
        sim = Simulator(build_trains(), Scheduler(), network=default_network, verbose=False)

        metrics = sim.run(max_ticks=20)

        self.assertEqual(metrics["arrived_trains"], 3)
        self.assertEqual(metrics["active_trains"], 0)
        self.assertGreater(metrics["loop_usage"], 0)
        self.assertGreater(metrics["trains"]["UP_LOC1"]["loop_entries"], 0)

        for tick in sim.history:
            movements = [
                action.block
                for action in tick["actions"]
                if action.action_type in {ActionType.MOVE, ActionType.ARRIVE}
            ]
            self.assertEqual(len(movements), len(set(movements)))

    def test_no_directional_loop_causes_an_explained_wait(self) -> None:
        network = Network([Station("A"), Station("B"), Station("C"), Station("D")])
        trains = [
            Train("UP_EXP", "EXPRESS", 10, current_station=1, destination_station=3),
            Train("UP_LOC", "LOCAL", 1, current_station=2, destination_station=3),
        ]
        sim = Simulator(trains, Scheduler(), network=network, verbose=False)

        actions = sim.step()
        waits = [action for action in actions if action.action_type == ActionType.WAIT]

        self.assertGreaterEqual(len(waits), 1)
        self.assertGreater(sim.conflict_count, 0)
        self.assertTrue(any("occupied" in action.reason for action in waits))


if __name__ == "__main__":
    unittest.main()
