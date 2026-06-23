from scenarios.scenario_1 import build_trains

from src.planning.scheduler import Scheduler
from src.railway.network import default_network
from src.simulation.simulator import Simulator


def main() -> None:
    """Run the default scenario and print final metrics.

    Returns:
        `None`; output is printed to the console.
    """

    scheduler = Scheduler()
    sim = Simulator(
        build_trains(),
        scheduler,
        network=default_network,
    )

    metrics = sim.run(max_ticks=50)

    print("\nFINAL METRICS")
    for train_name, train_metrics in metrics["trains"].items():
        print(
            f"{train_name}: "
            f"type={train_metrics['train_type']}, "
            f"finished={train_metrics['finished']}, "
            f"waiting={train_metrics['waiting_seconds']}s, "
            f"completion={train_metrics['completion_time_seconds']}s, "
            f"loop_entries={train_metrics['loop_entries']}"
        )
    print(f"total_ticks={metrics['total_ticks']}")
    print(f"tick_seconds={metrics['tick_seconds']}")
    print(f"total_time_seconds={metrics['total_time_seconds']}")
    print(f"conflict_count={metrics['conflict_count']}")
    print(f"loop_usage={metrics['loop_usage']}")


if __name__ == "__main__":
    main()
