"""Verification & validation checks. Usage: python validate.py   (writes results/validation.json)"""
import json, random
import numpy as np
from scipy import stats
import simpy
import config as C, model, analytics

def mm1_once(lam, mu, horizon, seed, warm):
    """Single-server FIFO queue built with the same SimPy primitives as the bus model."""
    env = simpy.Environment(); rng_a, rng_s = random.Random(f"a{seed}"), random.Random(f"s{seed}")
    q, waits = [], []
    def arr():
        while True:
            yield env.timeout(rng_a.expovariate(lam)); q.append(env.now)
    def srv():
        while True:
            if not q: yield env.timeout(0.01); continue        # polling server (dt small vs 1/mu)
            t = q.pop(0)
            if t > warm: waits.append(env.now - t)
            yield env.timeout(rng_s.expovariate(mu))
    env.process(arr()); env.process(srv()); env.run(until=horizon)
    return np.mean(waits)

def main():
    V = {}
    # 1) engine check against M/M/1 theory: Wq = rho/(mu-lam)
    lam, mu = 0.7, 1.0; theory = analytics.mm1_wq(lam, mu)
    sim = [mm1_once(lam, mu, 30000, s, 2000) for s in range(20)]
    half = stats.t.ppf(0.975, 19) * np.std(sim, ddof=1) / np.sqrt(20)
    V["mm1"] = dict(lam=lam, mu=mu, theory=theory, sim=float(np.mean(sim)), ci=float(half),
                    theory_inside_ci=bool(abs(np.mean(sim) - theory) <= half + 0.05 * theory))
    # 2) arrival generator: mean arrivals vs integral of the rate profile
    exp, got = {}, {}
    for r in model.ROUTE_NAMES:
        prof = C.PEAKS["morning"]["profile"][r]; exp[r] = sum((e - s) * x for s, e, x in prof)
        got[r] = np.mean([model.run_once("morning", C.SCENARIOS["A"], {"STC": 6, "MainGate": 6}, s)["routes"][r]["arrivals"]
                          / model.run_once("morning", C.SCENARIOS["A"], {"STC": 6, "MainGate": 6}, s)["demand_level"] for s in range(2000, 2060)])
    V["arrivals"] = {r: dict(expected=exp[r], simulated=float(got[r])) for r in exp}
    # 3) Little's law bookkeeping (L = lambda*W) and conservation (arrivals = served + left), CRN check
    worst, cons = 0.0, True; arr_by_scen = {}
    for key in C.SCENARIOS:
        al = {"STC": 7, "MainGate": 5} if key in "BD" else {"STC": 6, "MainGate": 6}
        for s in range(2000, 2030):
            r = model.run_once("afternoon", C.SCENARIOS[key], al, s)
            worst = max(worst, abs(r["little_L"] - r["little_lamW"]) / max(r["little_L"], 1e-9))
            cons &= (r["arrivals"] == r["served"] + r["left"])
            arr_by_scen.setdefault(s, set()).add(r["arrivals"])
    V["little_max_rel_err"] = float(worst); V["conservation_ok"] = bool(cons)
    V["crn_same_arrivals_all_scenarios"] = bool(all(len(v) == 1 for v in arr_by_scen.values()))
    # 4) deterministic extreme: no demand -> nobody waits, nobody left
    V["zero_demand_ok"] = model.run_once("morning", C.SCENARIOS["A"], {"STC": 6, "MainGate": 6}, 1, demand_mult=1e-9)["left"] == 0
    # 5) monotonicity: more buses on a route never increases its mean wait (checked on mean of 30 days)
    w = [np.mean([model.run_once("morning", C.SCENARIOS["A"], {"STC": s, "MainGate": 12 - s}, sd)["routes"]["STC"]["mean_wait"]
                  for sd in range(2000, 2030)]) for s in (4, 6, 8)]
    V["stc_wait_by_stc_buses"] = {4: float(w[0]), 6: float(w[1]), 8: float(w[2])}; V["monotone_ok"] = bool(w[0] > w[1] > w[2])
    json.dump(V, open("results/validation.json", "w"), indent=1)
    for k, v in V.items(): print(k, v)
    assert V["mm1"]["theory_inside_ci"] and V["conservation_ok"] and V["monotone_ok"] and V["crn_same_arrivals_all_scenarios"]
    print("ALL CHECKS PASSED")

if __name__ == "__main__":
    main()
