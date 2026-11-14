"""Run every experiment and write results/results.json.  Usage: python experiments.py [reps]"""
import json, sys, time
import numpy as np
from scipy import stats
import config as C, model, analytics

METRICS = ["mean_wait", "p95", "max_wait", "left", "served", "arrivals", "load_factor", "full_share",
           "denied_share", "max_queue", "wait_gap", "lf_gap", "mean_wait_cens"]

def ci95(x):
    x = np.asarray(x, float); n = len(x)
    if n < 2: return 0.0
    return float(stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n))

def alloc_for(key, peak, best, n_fleet=C.FLEET):
    a = C.SCENARIOS[key]["alloc"]
    if a is None: return model.split_even(n_fleet)
    s = best[peak][a]; return {"STC": s, "MainGate": n_fleet - s}

def run_many(peak, key, alloc, seeds, **kw):
    return [model.run_once(peak, C.SCENARIOS[key], alloc, s, **kw) for s in seeds]

def agg(runs):
    out = {m: dict(mean=float(np.mean([r[m] for r in runs])), ci=ci95([r[m] for r in runs]),
                   sd=float(np.std([r[m] for r in runs], ddof=1))) for m in METRICS}
    out["routes"] = {}
    for rt in model.ROUTE_NAMES:
        out["routes"][rt] = {m: float(np.mean([r["routes"][rt][m] for r in runs]))
                             for m in ["mean_wait", "p95", "served", "left", "max_queue", "load_factor"]}
    return out

def paired(base, other, m="mean_wait"):
    d = np.array([b[m] - o[m] for b, o in zip(base, other)])
    pct = d / np.array([b[m] for b in base])
    return dict(diff=float(d.mean()), ci=ci95(d), pct=float(100 * d.mean() / np.mean([b[m] for b in base])),
                better_in=float((d > 0).mean()))

def main(reps=len(C.SEEDS_EVAL)):
    t0 = time.time(); R = {"config": {"seats": C.SEATS, "fleet": C.FLEET, "reps": reps}}
    ev, tune = C.SEEDS_EVAL[:reps], C.SEEDS_SEARCH
    # 1) allocation search (tuning seeds, disjoint from evaluation seeds)
    R["search"] = {}; best = {}
    for peak in C.PEAKS:
        R["search"][peak] = {}; best[peak] = {}
        for tag, key in [("search_static", "A"), ("search_dynamic", "C")]:
            row = {}
            for s in range(3, C.FLEET - 2):                       # STC buses 3..10 (MainGate >= 2)
                runs = run_many(peak, key, {"STC": s, "MainGate": C.FLEET - s}, tune)
                row[s] = dict(mean_wait=float(np.mean([r["mean_wait"] for r in runs])),
                              p95=float(np.mean([r["p95"] for r in runs])))
            R["search"][peak][tag] = row
            best[peak][tag] = min(row, key=lambda s: row[s]["mean_wait"])
    R["best"] = best
    # 2) main evaluation (common random numbers: same seeds in every scenario)
    R["main"] = {}; raw = {}
    for peak in C.PEAKS:
        raw[peak] = {}; R["main"][peak] = {}
        for key in C.SCENARIOS:
            al = alloc_for(key, peak, best)
            raw[peak][key] = run_many(peak, key, al, ev)
            R["main"][peak][key] = agg(raw[peak][key]); R["main"][peak][key]["alloc"] = al
        for key in C.SCENARIOS:
            R["main"][peak][key]["vs_A"] = {m: paired(raw[peak]["A"], raw[peak][key], m)
                                            for m in ["mean_wait", "p95", "max_queue"]}
    # 3) traces for the queue-over-time figure (one representative day)
    R["traces"] = {}
    for peak in C.PEAKS:
        R["traces"][peak] = {}
        for key in ["A", "D", "E"]:
            r = model.run_once(peak, C.SCENARIOS[key], alloc_for(key, peak, best), ev[3], trace=True)
            R["traces"][peak][key] = r["trace"]
    # 4) sensitivity: demand level and traffic disruption (fresh seeds)
    R["sens_demand"] = {}
    for peak in C.PEAKS:
        R["sens_demand"][peak] = {}
        for mult in [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]:
            R["sens_demand"][peak][mult] = {}
            for key in ["A", "D", "E"]:
                runs = run_many(peak, key, alloc_for(key, peak, best), C.SEEDS_SENS, demand_mult=mult)
                R["sens_demand"][peak][mult][key] = dict(mean_wait=float(np.mean([r["mean_wait"] for r in runs])),
                    p95=float(np.mean([r["p95"] for r in runs])), left=float(np.mean([r["left"] for r in runs])))
    R["sens_traffic"] = {}
    for scale in [1.0, 2.0]:
        R["sens_traffic"][scale] = {}
        for key in ["A", "D", "E"]:
            rs = [x for peak in C.PEAKS for x in run_many(peak, key, alloc_for(key, peak, best), C.SEEDS_SENS, traffic_scale=scale)]
            R["sens_traffic"][scale][key] = dict(mean_wait=float(np.mean([r["mean_wait"] for r in rs])),
                                                 p95=float(np.mean([r["p95"] for r in rs])))
    # 5) fleet-size sensitivity: is buying buses necessary?
    R["sens_fleet"] = {}
    for n in range(8, 17, 1):
        R["sens_fleet"][n] = {}
        for key in ["A", "E"]:
            rs = [x for peak in C.PEAKS for x in run_many(peak, key, model.split_even(n), C.SEEDS_SENS)]
            R["sens_fleet"][n][key] = dict(mean_wait=float(np.mean([r["mean_wait"] for r in rs])),
                                           p95=float(np.mean([r["p95"] for r in rs])))
    # 6) analytic offered load
    R["analytic"] = {}
    for peak in C.PEAKS:
        R["analytic"][peak] = {}
        for rt in model.ROUTE_NAMES:
            R["analytic"][peak][rt] = dict(cycle=analytics.cycle_time(rt), needed=analytics.buses_needed(peak, rt),
                rho={c: analytics.offered_load(peak, rt, c)[0] for c in range(2, 11)},
                lam_h=analytics.offered_load(peak, rt, 6)[1])
    R["runtime_s"] = time.time() - t0
    json.dump(R, open("results/results.json", "w"), indent=1)
    print("done in %.1fs; best splits: %s" % (R["runtime_s"], best))

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else len(C.SEEDS_EVAL))
