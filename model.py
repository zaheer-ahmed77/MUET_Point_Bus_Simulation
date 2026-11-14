"""Discrete-event simulation of the MUET Point bus system (SimPy).
One run = one simulated day of one peak window."""
import math, random
import numpy as np
import simpy
import config as C

ROUTE_NAMES = list(C.ROUTES)

def tri_inv(u, a, m, b):
    """Inverse CDF of the triangular distribution (lets every bus use its own random stream)."""
    c = (m - a) / (b - a)
    return a + math.sqrt(u * (b - a) * (m - a)) if u < c else b - math.sqrt((1 - u) * (b - a) * (b - m))

def rate_at(profile, t):
    for s, e, r in profile:
        if s <= t < e:
            return r
    return 0.0

def mean_leg(route, p_delay=0.2):
    a, m, b = C.ROUTES[route]["tri"]
    return (a + m + b) / 3 + p_delay * sum(C.DELAY_RANGE) / 2

def split_even(n):
    return {"STC": (n + 1) // 2, "MainGate": n // 2}


class Terminal:
    """FIFO queue of arrival times, with exact bookkeeping."""
    def __init__(self, env, name):
        self.env, self.name = env, name
        self.queue = []; self.waits = []
        self.arrivals = 0; self.max_queue = 0
        self.area = 0.0; self._last = 0.0
        self.departures = 0; self.full_dep = 0; self.denied_dep = 0
        self.served = 0; self.seats_offered = 0
        self.inbound = 0                      # buses present at, or heading to, this terminal
        self.served_w = 0; self.seats_w = 0   # only departures inside the demand window (load factor)
        self.window = 0.0

    def _tick(self):
        self.area += len(self.queue) * (self.env.now - self._last); self._last = self.env.now

    def add(self):
        self._tick(); self.queue.append(self.env.now); self.arrivals += 1
        self.max_queue = max(self.max_queue, len(self.queue))

    def depart(self, seats):
        """Bus leaves now: board up to `seats` passengers FIFO."""
        self._tick()
        n = min(seats, len(self.queue))
        now = self.env.now
        self.waits.extend(now - t for t in self.queue[:n]); del self.queue[:n]
        self.served += n; self.departures += 1; self.seats_offered += seats
        if now <= self.window:
            self.served_w += n; self.seats_w += seats
        if n == seats: self.full_dep += 1
        if self.queue: self.denied_dep += 1   # somebody was left behind by a departing bus
        self.inbound -= 1
        return n


class Bus:
    def __init__(self, i, home, offset, seed):
        self.id, self.home, self.offset = i, home, offset
        self.rng = random.Random(f"{seed}-bus-{i}")      # same 'luck' for bus i in every scenario


class System:
    def __init__(self, env, peak, scen, alloc, seed, demand_mult, traffic_scale):
        self.env, self.scen, self.peak = env, scen, C.PEAKS[peak]
        self.end = self.peak["length"] + C.DRAIN
        day = random.Random(f"{seed}-day")
        s = C.DAY_DEMAND_SIGMA
        self.demand = day.lognormvariate(-s * s / 2, s) * demand_mult      # day-to-day demand level
        self.p_delay = min(0.95, day.uniform(*C.DELAY_PROB_RANGE) * traffic_scale)
        self.terms = {r: Terminal(env, r) for r in ROUTE_NAMES}
        self.profile = self.peak["profile"]
        self.buses = []
        k = 0
        for r in ROUTE_NAMES:                                              # stagger the fleet
            cycle = 2 * mean_leg(r) + C.STATIC_DWELL
            for j in range(alloc[r]):
                self.buses.append(Bus(k, r, j * cycle / max(1, alloc[r]), seed)); k += 1
                self.terms[r].inbound += 1
        self.trace = {r: [] for r in ROUTE_NAMES}
        for t in self.terms.values(): t.window = self.peak["length"]

    def leg(self, bus, route):
        a, m, b = C.ROUTES[route]["tri"]
        u1, u2, u3 = bus.rng.random(), bus.rng.random(), bus.rng.random()
        t = tri_inv(u1, a, m, b)
        if u2 < self.p_delay:
            t += C.DELAY_RANGE[0] + u3 * (C.DELAY_RANGE[1] - C.DELAY_RANGE[0])
        return t

    def choose_next(self, home_term, now):
        """Decision taken at the campus. Fixed fleet: go back to the same route.
        Floating fleet: go where the bus deficit is largest."""
        if not self.scen["floating"]:
            return home_term
        starved = [t for t in self.terms.values() if t.inbound < C.MIN_BUSES_PER_ROUTE]
        if starved:
            return min(starved, key=lambda t: t.inbound)
        def deficit(t):
            eta = mean_leg(t.name); cycle = 2 * eta + C.STATIC_DWELL
            lam = rate_at(self.profile[t.name], now + eta - 0.0) * self.demand
            return (lam * cycle + len(t.queue)) / C.SEATS - t.inbound   # buses needed - buses committed
        best = max(self.terms.values(), key=deficit)
        return home_term if deficit(home_term) >= deficit(best) - 1e-9 else best


def arrivals(env, term, S, rng):
    """Non-homogeneous Poisson process by thinning; stream is independent of the scenario."""
    prof = S.profile[term.name]
    lam_max = max(r for _, _, r in prof) * S.demand * 1.5
    end = S.peak["length"]
    while True:
        yield env.timeout(rng.expovariate(lam_max))
        if env.now >= end:
            return
        if rng.random() * lam_max <= rate_at(prof, env.now) * S.demand:
            term.add()


def bus_process(env, bus, S):
    yield env.timeout(bus.offset)
    term = S.terms[bus.home]
    while env.now < S.end:
        arrived = env.now
        yield env.timeout(C.MIN_DWELL)
        if S.scen["dispatch"] == "static":                  # baseline: fixed dwell
            yield env.timeout(C.STATIC_DWELL - C.MIN_DWELL)
        else:                                               # queue-triggered dispatch
            while True:
                q = len(term.queue); waited = env.now - arrived
                limit = C.DYN_LIMIT_BUSY if q > C.BUSY_Q else C.DYN_LIMIT_NORMAL
                if q >= C.SEATS or waited >= limit:
                    break
                yield env.timeout(C.DYN_STEP)
        term.depart(C.SEATS)
        yield env.timeout(S.leg(bus, term.name))            # terminal -> campus
        nxt = S.choose_next(term, env.now)                  # decision at the campus
        nxt.inbound += 1
        yield env.timeout(S.leg(bus, nxt.name))             # campus -> terminal
        term = nxt


def sampler(env, S, step=1.0):
    while True:
        for r, t in S.terms.items():
            S.trace[r].append((env.now, len(t.queue)))
        yield env.timeout(step)


def run_once(peak, scen, alloc, seed, demand_mult=1.0, traffic_scale=1.0, trace=False):
    env = simpy.Environment()
    S = System(env, peak, scen, alloc, seed, demand_mult, traffic_scale)
    for r, t in S.terms.items():
        env.process(arrivals(env, t, S, random.Random(f"{seed}-arr-{r}")))
    for b in S.buses:
        env.process(bus_process(env, b, S))
    if trace:
        env.process(sampler(env, S))
    env.run(until=S.end)
    for t in S.terms.values():
        t._tick()
    return summarise(S, trace)


def summarise(S, trace):
    end = S.end
    out = {"routes": {}}
    allw, tot_arr, tot_srv, seats, srv_w, dep, full, denied, left = [], 0, 0, 0, 0, 0, 0, 0, 0
    resid = 0.0; area = 0.0
    for r, t in S.terms.items():
        w = np.array(t.waits) if t.waits else np.array([0.0])
        l = len(t.queue); rs = sum(end - a for a in t.queue)
        out["routes"][r] = dict(mean_wait=float(w.mean()), p95=float(np.percentile(w, 95)),
            served=t.served, arrivals=t.arrivals, left=l, max_queue=t.max_queue,
            load_factor=t.served_w / t.seats_w if t.seats_w else 0.0, departures=t.departures)
        allw.extend(t.waits); tot_arr += t.arrivals; tot_srv += t.served; seats += t.seats_w; srv_w += t.served_w
        dep += t.departures; full += t.full_dep; denied += t.denied_dep; left += l; resid += rs; area += t.area
    w = np.array(allw) if allw else np.array([0.0])
    ro = out["routes"]
    out.update(mean_wait=float(w.mean()), p95=float(np.percentile(w, 95)), max_wait=float(w.max()),
        served=tot_srv, arrivals=tot_arr, left=left,
        load_factor=srv_w / seats if seats else 0.0,
        full_share=full / dep if dep else 0.0, denied_share=denied / dep if dep else 0.0,
        max_queue=max(x["max_queue"] for x in ro.values()),
        wait_gap=abs(ro["STC"]["mean_wait"] - ro["MainGate"]["mean_wait"]),
        lf_gap=abs(ro["STC"]["load_factor"] - ro["MainGate"]["load_factor"]),
        mean_wait_cens=float((w.sum() + resid) / max(1, tot_srv + left)),
        demand_level=S.demand, p_delay=S.p_delay,
        # Little's law bookkeeping check: L (time-average queue) vs lambda*W
        little_L=area / end, little_lamW=(w.sum() + resid) / end,
        )
    if trace:
        out["trace"] = S.trace
    return out
