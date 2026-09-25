# -*- coding: utf-8 -*-
"""Our drain factor against long-channel Level 1, at FULL gate drive, in normalised units.

PMOS pulling the output up, source on VDD, input held at 0 (full drive):
    overdrive   V_ov  = VDD - |V_th|        -> normalised  ov = 1 - vth_n
    headroom    |V_DS| = VDD - V_out        -> normalised  1 - v
    saturated while  headroom >= overdrive  ->  1 - v >= ov  ->  v <= vth_n
    in triode   I/I_sat = r(2-r),  r = headroom/overdrive

Ours:
    saturated while  1 - v >= x_lin
    in triode   I/I_sat = (1-v)/x_lin
"""
import numpy as np

VDD, VTHP = 3.3, 0.4064886       # buffers/models/hspice.mod, PMOS VTH0
vth_n = VTHP / VDD               # threshold as a fraction of the swing
ov = 1.0 - vth_n                 # normalised overdrive at full gate drive
XLIN = 0.45

print(f"V_DD {VDD} V, |V_th| {VTHP:.3f} V  ->  vth/VDD = {vth_n:.3f},  overdrive = {ov:.3f}")
print(f"book leaves saturation at v = {vth_n:.3f}   (triode for {100*(1-vth_n):.0f} % of travel)")
print(f"ours leaves saturation at v = {1-XLIN:.3f}   (triode for {100*XLIN:.0f} % of travel)\n")

def book(v):
    r = np.minimum((1 - v) / ov, 1.0)
    return np.where((1 - v) >= ov, 1.0, r * (2 - r))

def ours(v):
    return np.minimum(1.0, (1 - v) / XLIN)

print(f"{'v':>6} {'1-v':>6} | {'book':>7} {'ours':>7} | who passes more")
for v in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99):
    b, o = float(book(np.array(v))), float(ours(np.array(v)))
    who = "ours" if o > b + 1e-9 else ("book" if b > o + 1e-9 else "equal")
    print(f"{v:6.2f} {1-v:6.2f} | {b:7.3f} {o:7.3f} | {who}")

g = np.linspace(0, 1, 20001)
b, o = book(g), ours(g)
print(f"\narea under book = {np.trapezoid(b, g):.4f}")
print(f"area under ours = {np.trapezoid(o, g):.4f}")
print(f"ours / book     = {np.trapezoid(o, g) / np.trapezoid(b, g):.3f}")
cross = g[np.argmin(np.abs(b - o))]
print(f"the two cross near v = {cross:.3f}")
