# Train Traffic Control Technical Documentation

## Current Goal

This repository now models the first safety layer of a train traffic control engine:
track occupancy. The simulator is still intentionally small and discrete-tick based,
but it now treats railway movement as allocation of scarce resources instead of
just moving train indexes in a list.

The current scenario is a directional double-line section:

```text
UP:    Virar -> Bhayandar -> Borivali -> Andheri -> Bandra -> Dadar
DOWN:  Virar <- Bhayandar <- Borivali <- Andheri <- Bandra <- Dadar
                              loops       loops
```

## Core Concepts

- A `tick` is 30 simulated seconds. During a tick, trains may wait, dwell, enter
  or exit a loop, depart into a block, continue travelling, or arrive.
- A `Block` is one directional track between adjacent stations. UP and DOWN
  blocks over the same station pair are independent physical resources.
- Every station has `up_main` and `down_main`. Borivali and Andheri also have
  independently represented `up_loop` and `down_loop` lines.
- A `Train` may be at a station or `IN_TRANSIT`. In-transit trains reserve their
  directional block and destination line until arrival.
- An `Action` is an explicit event or scheduler decision: `MOVE`, `WAIT`,
  `DWELL`, `ENTER_LOOP`, `EXIT_LOOP`, or `ARRIVE`.
- `OccupancyState` validates safety. The scheduler and router can suggest actions,
  but unsafe actions are converted to safe waits by the simulator.

## Repository Structure

- `models/train.py` defines SLOW, FAST, and EXPRESS timing profiles, stop
  patterns, transit state, waiting, completion time, and loop usage.
- `models/station.py` defines station metadata, including UP/DOWN loop availability.
- `src/railway/network.py` defines `Network`, `Block`, and the default
  Virar-Dadar section.
- `src/railway/occupancy.py` owns station-line occupancy, persistent directional
  block reservations, and destination-line reservations.
- `src/planning/actions.py` defines action types and action payloads.
- `src/planning/router.py` creates safe candidate actions for one train.
- `src/planning/scheduler.py` chooses action order using priority, waiting time,
  and directional overtaking needs.
- `src/simulation/simulator.py` runs ticks, applies actions, records history, and
  reports metrics. It accepts `verbose=False` for clean automated test runs.
- `scenarios/scenario_1.py` defines the mixed-direction overtaking example.
- `tests/test_core_engine.py` checks directional safety, loop overtaking,
  unresolved conflicts, and metrics.
- `notebooks/simulation_walkthrough.ipynb` is an interactive walkthrough for
  inspecting tick-by-tick behavior.
- `docs/timing_model.md` documents timing assumptions and train profiles.
- `.gitignore` excludes Python bytecode caches and notebook checkpoints generated
  while running tests or notebooks.
- `requirements.txt` lists the notebook-related third-party packages. The core
  simulator and test suite use only the Python standard library.
- Every function and method has a return annotation plus a docstring with a
  `Returns:` note, so IDEs and readers can quickly see expected outputs.

## Source Package Layout

The `src` folder is split by responsibility:

- `src/railway`: physical railway model and resource occupancy.
- `src/planning`: actions, routing, and scheduling decisions.
- `src/simulation`: the tick runner that validates and applies decisions.

## Tick Flow

1. The simulator rebuilds occupancy from station trains and active traversals.
2. In-transit trains retain their block and destination-line reservations.
3. The scheduler looks for a higher-priority train following a lower-priority
   train in the same direction at a loop-capable station.
4. Lower-priority blockers are ordered first so they can enter the loop.
5. Regular station trains are ordered by priority, waiting time, then name.
6. `route()` returns the next safe action for each train against a working copy of
   occupancy.
7. A departure releases the source line and reserves the block and arrival line.
8. Every in-transit train advances one tick; completed traversals produce ARRIVE.
9. Scheduled stops receive a dwell counter; skipped stations do not.
10. Occupancy, metrics, history, and elapsed seconds are stored for inspection.

## Directional Overtaking Behavior

In `scenario_1`, `UP_EXP1` starts behind `UP_SLOW1` toward Dadar while
`DOWN_FAST1` travels independently toward Virar. Locals take two ticks per block
and the express takes one, so the express catches the slow at Borivali. The slow
enters `up_loop`, allowing the express to use `up_main`, then returns after the
express clears it.

An UP and a DOWN train may occupy parallel blocks between the same stations.
Two trains cannot hold the same directional block at once, even across ticks.

## Metrics

`Simulator.get_metrics()` returns:

- `total_ticks`
- `tick_seconds` and `total_time_seconds`
- `arrived_trains`
- `active_trains`
- `throughput` and `throughput_per_hour`
- `conflict_count`
- `loop_usage`
- Per-train status, type, source/target station, travel and dwell counters,
  waiting/completion values in ticks and seconds, line, and loop entries.

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

- Replace uniform profile times with actual per-block running times.
- Add headway windows.
- Add platform capacity beyond one line.
- Add branching graph networks.
- Add fast/slow directional corridors and explicit crossovers.
- Add disruption inputs and re-routing.

Once those deterministic tools are tested, they can become LangGraph tools such as
`route_tool`, `simulate_scenario_tool`, `get_conflicts_tool`, and
`explain_decision_tool`.
