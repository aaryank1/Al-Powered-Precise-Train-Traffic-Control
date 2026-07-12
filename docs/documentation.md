# Train Traffic Control Technical Documentation

## Current Goal

This repository now models the first safety layer of a train traffic control engine:
track occupancy. The simulator is still intentionally small and discrete-tick based,
but it now treats railway movement as allocation of scarce resources instead of
just moving train indexes in a list.

The current scenario is a single-track section:

```text
Virar -- Bhayandar -- Borivali -- Andheri -- Bandra -- Dadar
                         loop        loop
```

## Core Concepts

- A `tick` is one simulator decision cycle. During a tick, trains may wait, enter
  a loop, exit a loop, move across one block, or arrive at their destination.
- A `Block` is the track between two adjacent stations. Only one train may reserve
  a block in a tick.
- A station has one `main` berth. Stations with `has_loop=True` also have one
  `loop` berth.
- A `Train` is always at a station between ticks. It is either on the station
  `main` line or in the `loop`.
- An `Action` is an explicit scheduler decision: `MOVE`, `WAIT`, `ENTER_LOOP`,
  `EXIT_LOOP`, or `ARRIVE`.
- `OccupancyState` validates safety. The scheduler and router can suggest actions,
  but unsafe actions are converted to safe waits by the simulator.

## Repository Structure

- `models/train.py` defines train state, including current station, destination,
  track, waiting time, completion time, and loop usage.
- `models/station.py` defines station metadata, including loop availability.
- `src/railway/network.py` defines `Network`, `Block`, and the default
  Virar-Dadar section.
- `src/railway/occupancy.py` owns station berth occupancy and per-tick block
  reservations.
- `src/planning/actions.py` defines action types and action payloads.
- `src/planning/router.py` creates safe candidate actions for one train.
- `src/planning/scheduler.py` chooses action order using priority, waiting time,
  and crossing needs.
- `src/simulation/simulator.py` runs ticks, applies actions, records history, and
  reports metrics. It accepts `verbose=False` for clean automated test runs.
- `scenarios/scenario_1.py` defines the express/local crossing example.
- `tests/test_core_engine.py` checks safety, loop crossing, unresolved conflicts,
  and metrics.
- `notebooks/simulation_walkthrough.ipynb` is an interactive walkthrough for
  inspecting tick-by-tick behavior.
- `.gitignore` excludes Python bytecode caches and notebook checkpoints generated
  while running tests or notebooks.
- `requirements.txt` lists the notebook and Streamlit visualization packages.
  The core simulator and test suite use only the Python standard library.
- `streamlit_app.py` renders the default scenario as a tick-by-tick network
  visualization with station, loop, block reservation, action, and metrics views.
- Every function and method has a return annotation plus a docstring with a
  `Returns:` note, so IDEs and readers can quickly see expected outputs.

## Source Package Layout

The `src` folder is split by responsibility:

- `src/railway`: physical railway model and resource occupancy.
- `src/planning`: actions, routing, and scheduling decisions.
- `src/simulation`: the tick runner that validates and applies decisions.

## Tick Flow

1. The simulator rebuilds `OccupancyState` from unfinished trains.
2. The scheduler looks for higher-priority trains blocked by lower-priority trains
   at loop-capable stations.
3. Lower-priority blockers are ordered first so they can enter the loop.
4. Regular trains are ordered by priority, then waiting time, then name.
5. `route()` returns the next safe action for each train against a working copy of
   occupancy.
6. The simulator validates each action against the real occupancy state and applies
   it.
7. Metrics and history are stored for inspection.

## Crossing Behavior

In `scenario_1`, `EXP1` starts at Virar and `LOC1` starts at Dadar. They meet near
Borivali and Andheri. Since Andheri has a loop and `EXP1` has higher priority,
`LOC1` enters the Andheri loop. `EXP1` then moves through the Andheri main line.
After the main line clears, `LOC1` exits the loop and continues toward Virar.

The old unsafe behavior allowed this same pair to swap across the Borivali-Andheri
block in opposite directions during the same tick. That is now blocked by resource
reservation.

## Metrics

`Simulator.get_metrics()` returns:

- `total_ticks`
- `arrived_trains`
- `active_trains`
- `throughput`
- `conflict_count`
- `loop_usage`
- Per-train status: `finished`, `waiting_time`, `completion_time`,
  `current_station`, `track`, and `loop_entries`

## How To Run

Create and populate the local virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Run the simulator and tests:

```powershell
.venv\Scripts\python main.py
.venv\Scripts\python -m unittest discover
```

Launch Jupyter from the same environment, then open
`notebooks/simulation_walkthrough.ipynb` and run the cells from top to bottom:

```powershell
.venv\Scripts\python -m notebook
```

## Future Path

The right next step after this engine is stable is not an LLM agent yet. First,
make routing richer:

- Add variable travel times and dwell times.
- Add headway windows.
- Add platform capacity beyond one berth.
- Add branching graph networks.
- Add disruption inputs and re-routing.

Once those deterministic tools are tested, they can become dashboard controls and
LangGraph tools such as `route_tool`, `simulate_scenario_tool`,
`get_conflicts_tool`, and `explain_decision_tool`.
