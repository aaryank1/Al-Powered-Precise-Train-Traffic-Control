# Train Traffic Control

Occupancy-first simulator for a directional double-line railway section with
loop-line overtaking behavior.

## Start Here

- Read `docs/problem_statement.md` for the original challenge.
- Read `docs/documentation.md` for how the current engine works.
- Read `docs/network_lines.md` for UP/DOWN terminology, the implemented topology,
  and research sources.
- Read `docs/timing_model.md` for tick duration, train types, stop patterns, and
  current timing assumptions.
- Create the local environment with `python -m venv .venv`, then install
  dependencies with `.venv\Scripts\python -m pip install -r requirements.txt`.
- Run `python main.py` to execute the default mixed-direction overtaking scenario.
- Run `python -m unittest discover` to check safety behavior.
- Open `notebooks/simulation_walkthrough.ipynb` for an interactive walkthrough.

## Current Milestone

The project now models:

- directional UP/DOWN block occupancy,
- UP/DOWN station main and loop lines,
- persistent multi-tick block traversal and arrival-line reservations,
- SLOW, FAST, and EXPRESS profiles with scheduled-stop dwell,
- safe action validation,
- priority-based loop overtaking,
- per-train and simulator metrics.

LangGraph tools and a dashboard are future layers on top of this deterministic
engine.

## To Do

- Replace uniform block times with actual station distances and per-block running
  times.
- Later evaluate overtaking using catch-up, delay, timetable precedence, and
  controller instructions instead of only immediate occupancy and priority.
- Add headway windows.
- Add platform capacity beyond one line.
- Add branching graph networks.
- Add fast/slow directional corridors and explicit crossovers.
- Add disruption inputs and re-routing.
- Use Streamlit to visualize the network for a station master or section
  controller. Reference: ![Control Panel](assets/Railway%20Network.jpg)

Once those deterministic tools are tested, they can become LangGraph tools such as
`route_tool`, `simulate_scenario_tool`, `get_conflicts_tool`, and
`explain_decision_tool`.
