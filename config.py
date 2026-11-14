"""All model parameters live here. They are ASSUMPTIONS (no operational data was supplied
with the brief). Replace them with counted/GPS data and re-run; no other code changes needed."""

SEATS = 50                      # seats per bus (capacity)
FLEET = 12                      # total buses, never changed in any scenario
MIN_DWELL = 1.0                 # min minutes a bus stays at the terminal (unload/ready)
STATIC_DWELL = 5.0              # baseline: fixed terminal dwell (minutes)
DYN_STEP = 0.5                  # dynamic rule re-checks the queue every 0.5 min
DYN_LIMIT_NORMAL = 4.0          # dynamic rule: max hold when queue <= BUSY_Q
DYN_LIMIT_BUSY = 2.0            # dynamic rule: max hold when queue >  BUSY_Q
BUSY_Q = 30
MIN_BUSES_PER_ROUTE = 2         # fleet balancing never abandons a route
DRAIN = 45                      # minutes buses keep running after arrivals stop

# One-way travel time terminal <-> campus: triangular(low, mode, high) minutes
ROUTES = {
    "STC":      {"tri": (18, 25, 35)},
    "MainGate": {"tri": (12, 17, 25)},
}
# Traffic: each day a random share of trips suffers an extra delay (unexpected traffic)
DELAY_PROB_RANGE = (0.10, 0.30)     # daily probability of a delayed trip (mean 0.20)
DELAY_RANGE = (5.0, 12.0)           # extra minutes when delayed
DAY_DEMAND_SIGMA = 0.10             # day-to-day demand variation (lognormal, mean 1)

# Time-varying passenger arrival rates (passengers per minute) per route.
# (start_min, end_min, rate) measured from the start of the simulated window.
PEAKS = {
    "morning": {
        "label": "Morning (07:30-09:30, peak 08:00-09:00)", "length": 120, "clock": "07:30",
        "profile": {
            "STC":      [(0, 30, 2.8), (30, 90, 5.5), (90, 120, 2.8)],
            "MainGate": [(0, 30, 2.0), (30, 90, 4.0), (90, 120, 2.0)],
        },
    },
    "afternoon": {
        "label": "Afternoon (13:30-16:00, peak 14:00-15:30)", "length": 150, "clock": "13:30",
        "profile": {
            "STC":      [(0, 30, 2.5), (30, 120, 5.0), (120, 150, 2.5)],
            "MainGate": [(0, 30, 1.8), (30, 120, 3.6), (120, 150, 1.8)],
        },
    },
}

# Scenarios (the fleet is 12 buses in all of them)
SCENARIOS = {
    "A": dict(name="A: Baseline (6+6, fixed dwell)", alloc=None, dispatch="static",  floating=False),
    "B": dict(name="B: Best static split",           alloc="search_static",  dispatch="static",  floating=False),
    "C": dict(name="C: Dynamic dispatch (6+6)",      alloc=None, dispatch="dynamic", floating=False),
    "D": dict(name="D: Best split + dynamic dispatch", alloc="search_dynamic", dispatch="dynamic", floating=False),
    "E": dict(name="E: Floating fleet + dynamic dispatch", alloc=None, dispatch="dynamic", floating=True),
}

SEEDS_EVAL = list(range(1000, 1050))    # 50 replications (= 50 simulated days), shared by all scenarios
SEEDS_SEARCH = list(range(5000, 5030))  # different seeds for tuning: avoids selection bias
SEEDS_SENS = list(range(3000, 3030))
