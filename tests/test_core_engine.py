import unittest

from models.station import Station
from models.train import Train
from scenarios.scenario_1 import build_trains
from src.planning.actions import Action, ActionType
from src.planning.scheduler import Scheduler
from src.railway.network import Network, default_network
from src.railway.occupancy import MAIN, OccupancyState
from src.simulation.simulator import Simulator


class CoreEngineTest(unittest.TestCase):
    """Safety and crossing tests for the core engine."""

    def test_scenario_1_does_not_swap_opposite_directions_on_same_block(self) -> None:
        """Verify crossing uses a loop instead of an unsafe block swap.

        Returns:
            `None`; assertions validate the expected behavior.
        """

        sim = Simulator(build_trains(), Scheduler(), network=default_network, verbose=False)

        sim.step()
        sim.step()
        actions = sim.step()

        block_movements = [
            action
            for action in actions
            if action.action_type in {ActionType.MOVE, ActionType.ARRIVE}
        ]
        used_blocks = [action.block for action in block_movements]

        self.assertEqual(len(used_blocks), len(set(used_blocks)))
        self.assertIn(ActionType.ENTER_LOOP, [action.action_type for action in actions])

    def test_only_one_train_can_reserve_a_block_per_tick(self) -> None:
        """Verify duplicate block reservations are rejected.

        Returns:
            `None`; assertions validate the expected behavior.
        """

        state = OccupancyState(default_network)
        state.reserve_block((0, 1), "T1", 0, 1)

        can_reserve, reason = state.can_reserve_block((0, 1), "T2", 1, 0)

        self.assertFalse(can_reserve)
        self.assertIn("opposite-direction", reason)

    def test_only_one_train_can_occupy_station_main_berth(self) -> None:
        """Verify station main berths are single-occupancy resources.

        Returns:
            `None`; assertions validate the expected behavior.
        """

        state = OccupancyState(default_network)
        state.occupy_berth(0, MAIN, "T1")

        with self.assertRaises(ValueError):
            state.occupy_berth(0, MAIN, "T2")

    def test_train_can_enter_loop_only_at_loop_station(self) -> None:
        """Verify loop entry is blocked at stations without loops.

        Returns:
            `None`; assertions validate the expected behavior.
        """

        train = Train("T1", "LOCAL", 1, current_station=0, destination_station=5)
        state = OccupancyState.from_trains(default_network, [train])
        action = Action(
            train_name="T1",
            action_type=ActionType.ENTER_LOOP,
            reason="test loop entry",
            source_station=0,
            target_station=0,
            source_track="main",
            target_track="loop",
        )

        can_apply, reason = state.can_apply(action, train)

        self.assertFalse(can_apply)
        self.assertEqual(reason, "station has no loop line")

    def test_express_local_crossing_completes_safely_through_loop(self) -> None:
        """Verify the default scenario completes through a loop crossing.

        Returns:
            `None`; assertions validate the expected behavior.
        """

        sim = Simulator(build_trains(), Scheduler(), network=default_network, verbose=False)

        metrics = sim.run(max_ticks=20)

        self.assertEqual(metrics["arrived_trains"], 2)
        self.assertEqual(metrics["active_trains"], 0)
        self.assertGreater(metrics["loop_usage"], 0)
        self.assertGreater(metrics["trains"]["LOC1"]["loop_entries"], 0)
        self.assertEqual(metrics["conflict_count"], 0)

        for tick in sim.history:
            movements = [
                action.block
                for action in tick["actions"]
                if action.action_type in {ActionType.MOVE, ActionType.ARRIVE}
            ]
            self.assertEqual(len(movements), len(set(movements)))

    def test_no_loop_conflict_waits_safely_and_is_explained(self) -> None:
        """Verify unresolved no-loop crossings become safe waits.

        Returns:
            `None`; assertions validate the expected behavior.
        """

        network = Network(
            [
                Station("A", False),
                Station("B", False),
                Station("C", False),
                Station("D", False),
            ]
        )
        trains = [
            Train("EXP", "EXPRESS", 10, current_station=1, destination_station=3),
            Train("LOC", "LOCAL", 1, current_station=2, destination_station=0),
        ]
        sim = Simulator(trains, Scheduler(), network=network, verbose=False)

        actions = sim.step()
        waits = [action for action in actions if action.action_type == ActionType.WAIT]

        self.assertGreaterEqual(len(waits), 1)
        self.assertGreater(sim.conflict_count, 0)
        self.assertTrue(any("occupied" in action.reason for action in waits))
        self.assertEqual(trains[0].current_station, 1)
        self.assertEqual(trains[1].current_station, 2)

    def test_final_metrics_report_arrivals_waits_and_total_ticks(self) -> None:
        """Verify final metrics include arrivals, waits, and tick count.

        Returns:
            `None`; assertions validate the expected behavior.
        """

        sim = Simulator(build_trains(), Scheduler(), network=default_network, verbose=False)

        metrics = sim.run(max_ticks=20)

        self.assertIn("total_ticks", metrics)
        self.assertIn("waiting_time", metrics["trains"]["LOC1"])
        self.assertIsNotNone(metrics["trains"]["EXP1"]["completion_time"])
        self.assertIsNotNone(metrics["trains"]["LOC1"]["completion_time"])
        self.assertGreater(metrics["total_ticks"], 0)


if __name__ == "__main__":
    unittest.main()
