# Modelling, Simulating and Optimising the MUET Point Bus System

PBL – Simulation & Modelling, Department of Software Engineering, MUET Jamshoro.
Authors: **Zaheer Ahmed (22SW077), Aisha Khan (22SW017), Sunjay Kumar (22SW050), Tufail Ahmed (22SW071)** – Instructor: Engr. Umar Farooq

A SimPy discrete-event simulation of the MUET Point buses (STC and Main Gate routes, morning and
afternoon peaks). It compares five scenarios that all use the **same 12 buses**:

| Key | Scenario |
|---|---|
| A | Baseline: 6+6 buses, fixed 5-minute dwell |
| B | Best static split (found by search), fixed dwell |
| C | Queue-triggered dispatch (full-or-timeout), 6+6 |
| D | Best split + queue-triggered dispatch |
| E | Floating fleet (bus-deficit rule at the campus) + queue-triggered dispatch |

## Files
| File | Purpose |
|---|---|
| `config.py` | **All parameters** (demand profiles, trip times, traffic, rules, seeds). Replace with real data here. |
| `model.py` | SimPy model: arrivals, buses, terminals, dispatch rules, floating-fleet rule, metrics |
| `analytics.py` | Closed-form checks: seat supply, offered load rho, buses needed, M/M/1 |
| `experiments.py` | Allocation search, 50-day scenario runs, sensitivity tests -> `results/results.json` |
| `validate.py` | Verification & validation (M/M/1, Little's law, conservation, CRN) -> `results/validation.json` |
| `make_figures.py` | All figures in `figures/` |

## Run
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python experiments.py          # ~1-2 min; add a number to change replications, e.g. python experiments.py 30
python validate.py             # prints ALL CHECKS PASSED
python make_figures.py         # writes figures/*.png
```

## Important notes
* **Parameters are assumptions**, not measured MUET data (none was supplied with the brief). Put counted arrival
  rates and GPS/logbook trip times into `config.py` and re-run; no other code changes are needed.
* Common random numbers: every scenario sees the same arrivals and the same bus-by-bus traffic luck for a given seed.
  Tuning seeds (5000-5029) are separate from evaluation seeds (1000-1049).
* The results shipped in `results/` were produced in an offline sandbox with a minimal SimPy-compatible event loop.
  With the official SimPy 4 the numbers can differ slightly (event tie-breaking); conclusions do not change.
  Re-run `experiments.py` to regenerate everything with your own SimPy.

## Publish on GitHub
```bash
git init
git add .
git commit -m "MUET Point bus simulation (PBL, 22SW077)"
git branch -M main
git remote add origin https://github.com/zaheer-ahmed77/MUET_Point_Bus_Simulation.git
git push -u origin main
```
