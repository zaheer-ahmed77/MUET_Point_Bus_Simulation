"""Closed-form queueing checks used alongside the simulation."""
import config as C
from model import mean_leg

def cycle_time(route, dwell=C.STATIC_DWELL, p_delay=0.2):
    return 2 * mean_leg(route, p_delay) + dwell            # minutes

def seat_supply(route, buses, dwell=C.STATIC_DWELL):
    """mu = c*K/T in seats per hour."""
    return buses * C.SEATS / (cycle_time(route, dwell) / 60)

def offered_load(peak, route, buses, dwell=C.STATIC_DWELL):
    """rho = peak-hour arrival rate / seat supply rate (per hour)."""
    lam_h = max(r for _, _, r in C.PEAKS[peak]["profile"][route]) * 60
    return lam_h / seat_supply(route, buses, dwell), lam_h

def buses_needed(peak, route, dwell=C.STATIC_DWELL):
    lam_h = max(r for _, _, r in C.PEAKS[peak]["profile"][route]) * 60
    return lam_h / (C.SEATS * 60 / cycle_time(route, dwell))

def mm1_wq(lam, mu):
    return lam / (mu * (mu - lam))
