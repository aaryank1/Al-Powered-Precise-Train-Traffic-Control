# Train Traffic Control

Occupancy-first simulator for a directional double-line railway section with
loop-line overtaking behavior.

## Start Here

- Read `docs/problem_statement.md` for the original challenge.
- Read `docs/documentation.md` for how the current engine works.
- Read `docs/network_lines.md` for UP/DOWN terminology, the implemented topology,
  and research sources.
- Create the local environment with `python -m venv .venv`, then install
  dependencies with `.venv\Scripts\python -m pip install -r requirements.txt`.
- Run `python main.py` to execute the default mixed-direction overtaking scenario.
- Run `python -m unittest discover` to check safety behavior.
- Open `notebooks/simulation_walkthrough.ipynb` for an interactive walkthrough.

## Current Milestone

The project now models:

- directional UP/DOWN block occupancy,
- UP/DOWN station main and loop lines,
- safe action validation,
- priority-based loop overtaking,
- per-train and simulator metrics.

LangGraph tools and a dashboard are future layers on top of this deterministic
engine.

## To Do

- Add running and dwell times so fast trains can catch slower trains naturally : 
  - Change later implementation so overtaking requires an explicit reason, such as:
faster running time
different stopping pattern
timetable precedence
predicted conflict/delay
manual controller instruction, as currently the reason for overtake in scenario1 is that express's immediate route is occupied so it forces an overatake.
- Add explicit fast/slow corridors and crossover locations.
- Use Streamlit for creating train network visualization for Station master. The UI should contain the overview of the entire network of railways.
Reference Image: ![Control Panel](assets/Railway%20Network.jpg)
