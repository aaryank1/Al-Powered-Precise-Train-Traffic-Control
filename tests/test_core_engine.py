import unittest

from models.station import Station
from models.train import EXPRESS, FAST, SLOW, TRAIN_PROFILES, Train
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
        up_train = Train("UP", SLOW, 1, current_station=0, destination_station=5)
        down_train = Train("DOWN", SLOW, 1, current_station=5, destination_station=0)

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

    def test_only_one_train_can_hold_each_directional_block(self) -> None:
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
        train = Train("UP1", SLOW, 1, current_station=2, destination_station=5)
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
            Train("UP_EXP", EXPRESS, 10, current_station=1, destination_station=5),
            Train("UP_LOC", SLOW, 1, current_station=2, destination_station=5),
        ]
        sim = Simulator(trains, Scheduler(), network=default_network, verbose=False)

        actions = sim.step()

        actions_by_train = {
            action.train_name: action
            for action in actions
            if action.action_type != ActionType.ARRIVE
        }
        self.assertEqual(actions_by_train["UP_LOC"].action_type, ActionType.ENTER_LOOP)
        self.assertEqual(actions_by_train["UP_EXP"].action_type, ActionType.MOVE)
        self.assertEqual(trains[0].current_station, 2)
        self.assertEqual(trains[1].line, UP_LOOP)

    def test_higher_priority_down_train_overtakes_through_down_loop(self) -> None:
        trains = [
            Train("DOWN_EXP", EXPRESS, 10, current_station=3, destination_station=0),
            Train("DOWN_LOC", SLOW, 1, current_station=2, destination_station=0),
        ]
        sim = Simulator(trains, Scheduler(), network=default_network, verbose=False)

        actions = sim.step()

        actions_by_train = {
            action.train_name: action
            for action in actions
            if action.action_type != ActionType.ARRIVE
        }
        self.assertEqual(actions_by_train["DOWN_LOC"].action_type, ActionType.ENTER_LOOP)
        self.assertEqual(actions_by_train["DOWN_EXP"].action_type, ActionType.MOVE)
        self.assertEqual(trains[0].current_station, 2)
        self.assertEqual(trains[1].line, DOWN_LOOP)

    def test_movement_rejects_a_block_from_the_wrong_direction(self) -> None:
        train = Train("UP1", SLOW, 1, current_station=2, destination_station=5)
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
        self.assertGreater(metrics["trains"]["UP_SLOW1"]["loop_entries"], 0)

        for tick in sim.history:
            movements = [
                action.block
                for action in tick["actions"]
                if action.action_type == ActionType.MOVE
            ]
            self.assertEqual(len(movements), len(set(movements)))

    def test_no_directional_loop_causes_an_explained_wait(self) -> None:
        network = Network([Station("A"), Station("B"), Station("C"), Station("D")])
        trains = [
            Train("UP_EXP", EXPRESS, 10, current_station=1, destination_station=3),
            Train("UP_LOC", SLOW, 1, current_station=2, destination_station=3),
        ]
        sim = Simulator(trains, Scheduler(), network=network, verbose=False)

        actions = sim.step()
        waits = [action for action in actions if action.action_type == ActionType.WAIT]

        self.assertGreaterEqual(len(waits), 1)
        self.assertGreater(sim.conflict_count, 0)
        self.assertTrue(any("occupied" in action.reason for action in waits))

    def test_train_profiles_keep_locals_equal_and_express_faster(self) -> None:
        self.assertEqual(TRAIN_PROFILES[SLOW].running_ticks, 2)
        self.assertEqual(TRAIN_PROFILES[FAST].running_ticks, 2)
        self.assertEqual(TRAIN_PROFILES[EXPRESS].running_ticks, 1)

    def test_stop_patterns_distinguish_slow_fast_and_express(self) -> None:
        slow = Train("S", SLOW, 1, 0, 5)
        fast = Train("F", FAST, 5, 0, 5, scheduled_stops=(2, 5))
        express = Train("E", EXPRESS, 10, 0, 5, scheduled_stops=(5,))

        self.assertTrue(slow.stops_at(1))
        self.assertFalse(fast.stops_at(1))
        self.assertTrue(fast.stops_at(2))
        self.assertFalse(express.stops_at(2))
        self.assertTrue(express.stops_at(5))

    def test_slow_train_occupies_block_for_two_thirty_second_ticks(self) -> None:
        network = Network([Station("A"), Station("B")])
        train = Train("S", SLOW, 1, current_station=0, destination_station=1)
        sim = Simulator([train], Scheduler(), network=network, verbose=False)

        first_actions = sim.step()

        self.assertTrue(train.is_in_transit)
        self.assertEqual(train.remaining_travel_ticks, 1)
        self.assertIn(network.block_between(0, 1).key, sim.occupancy_state.block_reservations)
        self.assertNotIn(ActionType.ARRIVE, [action.action_type for action in first_actions])

        second_actions = sim.step()
        metrics = sim.get_metrics()

        self.assertTrue(train.finished)
        self.assertIn(ActionType.ARRIVE, [action.action_type for action in second_actions])
        self.assertEqual(metrics["total_ticks"], 2)
        self.assertEqual(metrics["total_time_seconds"], 60)
        self.assertEqual(metrics["trains"]["S"]["completion_time_seconds"], 60)

    def test_express_crosses_one_block_in_one_tick(self) -> None:
        network = Network([Station("A"), Station("B")])
        train = Train("E", EXPRESS, 10, current_station=0, destination_station=1)
        sim = Simulator([train], Scheduler(), network=network, verbose=False)

        actions = sim.step()
        metrics = sim.get_metrics()

        self.assertTrue(train.finished)
        self.assertIn(ActionType.ARRIVE, [action.action_type for action in actions])
        self.assertEqual(metrics["total_ticks"], 1)
        self.assertEqual(metrics["total_time_seconds"], 30)

    def test_slow_dwells_where_fast_service_skips(self) -> None:
        network = Network([Station("A"), Station("B"), Station("C")])
        slow = Train("S", SLOW, 1, current_station=0, destination_station=2)
        fast = Train("F", FAST, 5, current_station=0, destination_station=2)

        slow_sim = Simulator([slow], Scheduler(), network=network, verbose=False)
        slow_sim.step()
        slow_sim.step()
        slow_actions = slow_sim.step()

        fast_sim = Simulator([fast], Scheduler(), network=network, verbose=False)
        fast_sim.step()
        fast_sim.step()
        fast_actions = fast_sim.step()

        self.assertEqual(slow_actions[0].action_type, ActionType.DWELL)
        self.assertEqual(fast_actions[0].action_type, ActionType.MOVE)

    def test_arrival_line_reservation_blocks_loop_exit(self) -> None:
        network = Network(
            [Station("A"), Station("B", has_up_loop=True), Station("C")]
        )
        arriving = Train("ARRIVING", SLOW, 1, current_station=0, destination_station=2)
        arriving.begin_movement(1)
        loop_train = Train(
            "LOOP",
            SLOW,
            1,
            current_station=1,
            destination_station=2,
            line=UP_LOOP,
        )
        state = OccupancyState.from_trains(network, [arriving, loop_train])
        action = Action(
            train_name=loop_train.name,
            action_type=ActionType.EXIT_LOOP,
            reason="test reserved arrival line",
            source_station=1,
            target_station=1,
            source_track=UP_LOOP,
            target_track=UP_MAIN,
        )

        can_apply, reason = state.can_apply(action, loop_train)

        self.assertFalse(can_apply)
        self.assertIn("occupied", reason)

    def test_unknown_train_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Train("UNKNOWN", "LOCAL", 1, current_station=0, destination_station=1)


if __name__ == "__main__":
    unittest.main()
