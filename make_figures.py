"""Create every figure from results/results.json.  Usage: python make_figures.py"""
import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Circle
import numpy as np
import config as C

R = json.load(open("results/results.json"))
plt.rcParams.update({"font.size": 6.5, "axes.titlesize": 7, "axes.labelsize": 6.5, "legend.fontsize": 5.8,
                     "xtick.labelsize": 6, "ytick.labelsize": 6, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25, "figure.dpi": 100})
COL = {"A": "#c0392b", "B": "#e67e22", "C": "#8e44ad", "D": "#1e8449", "E": "#2471a3"}
SHORT = {"A": "A Baseline", "B": "B Best split", "C": "C Dynamic", "D": "D Split+dyn.", "E": "E Floating"}
W = 3.45
def save(fig, name): fig.savefig(f"figures/{name}.png", dpi=300, bbox_inches="tight"); plt.close(fig)

# ---- Fig 1: demand profile -------------------------------------------------------------
def fig_demand():
    fig, axs = plt.subplots(1, 2, figsize=(W, 1.7), sharey=True)
    for ax, peak in zip(axs, C.PEAKS):
        for rt, c in [("STC", "#1f4e79"), ("MainGate", "#2e86c1")]:
            xs, ys = [], []
            for s, e, r in C.PEAKS[peak]["profile"][rt]: xs += [s, e]; ys += [r, r]
            ax.plot(xs, ys, color=c, lw=1.4, label=rt)
        ax.set_title(peak.capitalize()); ax.set_xlabel("Minutes from window start")
    axs[0].set_ylabel("Arrivals / min"); axs[0].legend(loc="upper left"); fig.tight_layout(); save(fig, "fig_demand")

# ---- Fig 2: state transition diagrams -----------------------------------------------------
def box(ax, x, y, w, h, t, fc="#eaf2f8", ec="#1f4e79"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=.8))
    ax.text(x, y, t, ha="center", va="center", fontsize=4.9)
def arr(ax, p, q, txt="", rad=0.0, off=(0, 0.1)):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=6, lw=.7, color="#333", connectionstyle=f"arc3,rad={rad}"))
    if txt: ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], txt, fontsize=4.9, ha="center", color="#7b241c")
def fig_states():
    fig, axs = plt.subplots(2, 1, figsize=(W, 3.3), gridspec_kw={"height_ratios": [1, 1.25]})
    ax = axs[0]; ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(-.2, 2.6); ax.set_title("(a) Passenger state transitions", loc="left", fontsize=6.5)
    box(ax, 1, 1.7, 1.7, .9, "Not yet\narrived"); box(ax, 3.7, 1.7, 1.9, .9, "Waiting in\nFIFO queue"); box(ax, 6.5, 1.7, 1.6, .9, "On board", "#e9f7ef", "#1e8449"); box(ax, 9.1, 1.7, 1.6, .9, "Served\n(wait logged)", "#e9f7ef", "#1e8449")
    box(ax, 6.5, .2, 3.0, .6, "Left behind at end (queue not empty)", "#fdedec", "#c0392b")
    arr(ax, (1.85, 1.7), (2.75, 1.7), "Poisson\narrival", off=(0, .38)); arr(ax, (4.65, 1.7), (5.7, 1.7), "seat free\nat departure", off=(0, .38)); arr(ax, (7.3, 1.7), (8.3, 1.7), "trip", off=(0, .2))
    arr(ax, (3.7, 1.25), (5.0, .35), "window + drain ends", off=(-.9, -.1))
    ax = axs[1]; ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 4.2); ax.set_title("(b) Bus state transitions", loc="left", fontsize=6.5)
    box(ax, 1.4, 3.0, 2.2, .9, "At terminal:\ndwell / hold"); box(ax, 5, 3.0, 2.4, .9, "Boarding\n(up to 50, FIFO)"); box(ax, 8.6, 3.0, 2.2, .9, "Travelling\nto campus")
    box(ax, 8.6, .9, 2.2, .9, "At campus:\nchoose route"); box(ax, 4.6, .9, 2.6, .9, "Travelling back\nto terminal")
    arr(ax, (2.5, 3.0), (3.8, 3.0), "release rule", off=(0, .3)); arr(ax, (6.2, 3.0), (7.5, 3.0), "depart", off=(0, .3)); arr(ax, (8.6, 2.55), (8.6, 1.35), "arrive", off=(.55, 0))
    arr(ax, (7.5, .9), (5.9, .9), "chosen terminal", off=(0, .3)); arr(ax, (3.3, 1.2), (1.4, 2.55), "arrive", off=(-.5, 0), rad=-.1)
    ax.text(5, 4.0, "Release: fixed 5 min (A,B) or full / timeout (C,D,E). Route: same (A-D) or largest deficit (E).", ha="center", fontsize=5, style="italic")
    fig.tight_layout(); save(fig, "fig_states")

# ---- Fig 3: simulation flowchart ---------------------------------------------------------
def fig_flow():
    fig, ax = plt.subplots(figsize=(W, 4.3)); ax.axis("off"); ax.set_xlim(-1.2, 11.2); ax.set_ylim(0.5, 14)
    def dia(x, y, w, h, t):
        ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)], fc="#fef9e7", ec="#b7950b", lw=.8)); ax.text(x, y, t, ha="center", va="center", fontsize=5)
    def line(xs, ys, head=False):
        ax.plot(xs, ys, color="#333", lw=.7)
        if head: arr(ax, (xs[-2], ys[-2]), (xs[-1], ys[-1]))
    box(ax, 5, 13.3, 6.6, .8, "Start: read CONFIG, choose scenario and seed", "#d6eaf8")
    box(ax, 5, 12.1, 6.6, .8, "Draw day factors: demand level, traffic delays")
    box(ax, 5, 10.9, 6.6, .9, "Create terminals (FIFO queues) and 12 buses\n(scenario allocation, staggered start)")
    box(ax, 5, 9.6, 6.6, .8, "Start SimPy processes: 2 arrival + 12 bus loops")
    dia(5, 8.0, 6.4, 1.7, "More events before\nwindow + drain ends?")
    box(ax, 1.5, 5.9, 3.0, 1.1, "Arrival:\nadd to queue,\nupdate max queue"); box(ax, 5, 5.9, 3.0, 1.1, "Bus at terminal:\nhold, board FIFO,\nlog waits"); box(ax, 8.5, 5.9, 3.0, 1.1, "Bus at campus:\npick next route\n(scenario rule)")
    box(ax, 5, 4.0, 6.6, .8, "Update clocks, queue area, counters")
    box(ax, 5, 2.7, 6.6, .9, "Compute mean / P95 wait, served, left behind,\nload factor, queue length, route gaps", "#e9f7ef", "#1e8449")
    box(ax, 5, 1.4, 6.6, .8, "Repeat for 50 seeds: mean, 95% CI, paired diff.", "#e9f7ef", "#1e8449")
    for p, q in [((5, 12.9), (5, 12.5)), ((5, 11.7), (5, 11.35)), ((5, 10.45), (5, 10.0)), ((5, 9.2), (5, 8.85))]: arr(ax, p, q)
    arr(ax, (4.0, 7.4), (1.8, 6.45)); arr(ax, (5, 7.15), (5, 6.45)); arr(ax, (6.0, 7.4), (8.2, 6.45))
    arr(ax, (1.5, 5.35), (3.6, 4.4)); arr(ax, (5, 5.35), (5, 4.4)); arr(ax, (8.5, 5.35), (6.4, 4.4))
    line([8.3, 10.6, 10.6, 8.2], [4.0, 4.0, 8.0, 8.0], head=True); ax.text(10.9, 6.0, "yes", fontsize=5, color="#7b241c", rotation=90, va="center")
    line([1.8, -0.6, -0.6, 1.7], [8.0, 8.0, 2.7, 2.7], head=True); ax.text(-0.95, 5.3, "no", fontsize=5, color="#7b241c", rotation=90, va="center")
    arr(ax, (5, 3.55), (5, 3.2)); arr(ax, (5, 2.2), (5, 1.8)); save(fig, "fig_flow")

# ---- Fig 4: queue over time ----------------------------------------------------------------
def fig_trace():
    fig, axs = plt.subplots(2, 1, figsize=(W, 2.9), sharex=True)
    for ax, rt in zip(axs, ["STC", "MainGate"]):
        for key in ["A", "D", "E"]:
            t, q = zip(*R["traces"]["morning"][key][rt]); ax.plot(t, q, color=COL[key], lw=1, label=SHORT[key])
        ax.set_ylabel(f"{rt} queue"); 
    axs[0].legend(ncol=3, loc="upper right"); axs[1].set_xlabel("Minutes from 07:30 (morning window, one representative day)")
    fig.tight_layout(); save(fig, "fig_trace")

# ---- Fig 5/6: wait and P95 by scenario --------------------------------------------------
def fig_bars(metric, ylab, name):
    fig, ax = plt.subplots(figsize=(W, 2.0)); keys = list(C.SCENARIOS); x = np.arange(len(keys)); w = .38
    for i, peak in enumerate(C.PEAKS):
        v = [R["main"][peak][k][metric]["mean"] for k in keys]; e = [R["main"][peak][k][metric]["ci"] for k in keys]
        b = ax.bar(x + (i - .5) * w, v, w, yerr=e, capsize=1.5, color=[COL[k] for k in keys], alpha=1 if i == 0 else .55, error_kw=dict(lw=.6))
        for xi, vi, ee in zip(x + (i - .5) * w, v, e): ax.text(xi, vi + ee + .25, f"{vi:.1f}", ha="center", fontsize=5)
    ax.set_xticks(x); ax.set_xticklabels([SHORT[k] for k in keys], rotation=0, fontsize=5); ax.set_ylabel(ylab)
    ax.text(.01, .96, "left bar: morning, right bar: afternoon (lighter); whiskers: 95% CI", transform=ax.transAxes, fontsize=5, va="top")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.08); fig.tight_layout(); save(fig, name)

# ---- Fig 7: allocation search -------------------------------------------------------------------
def fig_search():
    fig, axs = plt.subplots(1, 2, figsize=(W, 1.9), sharey=True)
    for ax, peak in zip(axs, C.PEAKS):
        for tag, c, lab in [("search_static", COL["A"], "fixed dwell"), ("search_dynamic", COL["D"], "dynamic dispatch")]:
            row = R["search"][peak][tag]; s = sorted(int(k) for k in row); y = [row[str(k)]["mean_wait"] for k in s]
            ax.plot(s, y, "o-", color=c, ms=2.5, lw=1, label=lab); b = int(R["best"][peak][tag]); ax.plot(b, row[str(b)]["mean_wait"], "k*", ms=7, zorder=5)
        ax.set_title(peak.capitalize()); ax.set_xlabel("Buses on STC (rest on MG)")
    axs[0].set_ylabel("Mean wait (min)"); axs[0].legend(); fig.tight_layout(); save(fig, "fig_search")

# ---- Fig 8: per-route wait and load factor ---------------------------------------------------
def fig_routes():
    fig, axs = plt.subplots(1, 2, figsize=(W, 1.9)); keys = list(C.SCENARIOS); x = np.arange(len(keys)); w = .38
    for ax, m, lab in [(axs[0], "mean_wait", "Mean wait (min)"), (axs[1], "load_factor", "Load factor (served / seats)")]:
        for j, (rt, c) in enumerate([("STC", "#1f4e79"), ("MainGate", "#5dade2")]):
            v = [np.mean([R["main"][p][k]["routes"][rt][m] for p in C.PEAKS]) for k in keys]
            ax.bar(x + (j - .5) * w, v, w, color=c, label=rt)
        ax.set_xticks(x); ax.set_xticklabels(keys); ax.set_ylabel(lab); ax.set_xlabel("Scenario")
    axs[0].legend(); fig.tight_layout(); save(fig, "fig_routes")

# ---- Fig 9/10: sensitivity -----------------------------------------------------------------
def fig_sens():
    fig, axs = plt.subplots(1, 2, figsize=(W, 1.9))
    ms = sorted(float(m) for m in R["sens_demand"]["morning"])
    for key in ["A", "D", "E"]:
        axs[0].plot([(m - 1) * 100 for m in ms], [R["sens_demand"]["morning"][str(m)][key]["mean_wait"] for m in ms], "o-", ms=2.5, lw=1, color=COL[key], label=SHORT[key])
    axs[0].set_xlabel("Demand change (%)"); axs[0].set_ylabel("Mean wait (min), morning"); axs[0].legend()
    ns = sorted(int(n) for n in R["sens_fleet"])
    for key in ["A", "E"]:
        axs[1].plot(ns, [R["sens_fleet"][str(n)][key]["mean_wait"] for n in ns], "o-", ms=2.5, lw=1, color=COL[key], label=SHORT[key])
    axs[1].axvline(12, color="grey", ls=":", lw=.8); axs[1].set_xlabel("Fleet size (buses)"); axs[1].set_ylabel("Mean wait (min), both peaks"); axs[1].legend()
    fig.tight_layout(); save(fig, "fig_sens")

if __name__ == "__main__":
    fig_demand(); fig_states(); fig_flow(); fig_trace()
    fig_bars("mean_wait", "Mean wait (min)", "fig_wait"); fig_bars("p95", "95th-percentile wait (min)", "fig_p95")
    fig_search(); fig_routes(); fig_sens(); print("figures written")
