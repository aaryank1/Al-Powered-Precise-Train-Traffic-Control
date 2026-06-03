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
