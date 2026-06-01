from scenarios.scenario_1 import trains

from src.scheduler import Scheduler
from src.simulator import Simulator

scheduler = Scheduler()

sim = Simulator(
    trains,
    scheduler
)

while True:
    active = [
        t for t in trains
        if not t.finished
    ]
    if not active:
        break

    sim.step()