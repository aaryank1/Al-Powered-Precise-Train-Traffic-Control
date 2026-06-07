# Train Traffic Control

Occupancy-first simulator for a single-track railway section with loop-line
crossing behavior.

## Start Here

- Read `docs/problem_statement.md` for the original challenge.
- Read `docs/documentation.md` for how the current engine works.
- Create the local environment with `python -m venv .venv`, then install
  dependencies with `.venv\Scripts\python -m pip install -r requirements.txt`.
- Run `python main.py` to execute the default express/local crossing scenario.
- Run `python -m unittest discover` to check safety behavior.
- Open `notebooks/simulation_walkthrough.ipynb` for an interactive walkthrough.

## Current Milestone

The project now models:

- track block occupancy,
- station main and loop berths,
- safe action validation,
- priority-based loop crossing,
- per-train and simulator metrics.

LangGraph tools and a dashboard are future layers on top of this deterministic
engine.

## To do : 

- future idea : train.next_station_for can incorporate slow and fast train ideas by returning a higher number in the direction.
- Implement UP/DOWN Line Concept for Stations where each platform consists of 2 lines each -> UP Main Line, UP Loop Line, Down Main Line, Down Loop Line.
- Use Streamlit for creating train network visualization for Station master. The UI should contain the overview of the entire network of railways.
Reference Image: ![Control Panel](assets/Railway%20Network.jpg)
- 