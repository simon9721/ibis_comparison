# -*- coding: utf-8 -*-
"""Does the book's Level-1 drain current factor into a gate term times a drain term?

Book (Leventhal & Green 3.8 p.89, eq. 3-24/3-25), dropping LAMBDA:
    saturation (V_DS >= V_ov):  I = (KP/2)(W/L) * V_ov^2
    triode     (V_DS <  V_ov):  I = (KP/2)(W/L) * V_DS*(2*V_ov - V_DS)
with V_ov = V_GS - V_th.

Claim: I / I_sat depends on V_DS and V_ov only through r = V_DS / V_ov, as q(2-q) with
q = min(r, 1).  NOT min(1, r*(2-r)): r*(2-r) is a downward parabola peaking at r=1, so
above saturation it falls (0.75 at r=1.5, 0 at r=2) and min() would take the falling
branch.  Clamp r, not the result.  The code below has always clamped r; the wording
was wrong from 2026-09-25 to 2026-09-28.
"""
import numpy as np

k = 0.5 * 3.7e-4 * 20.0          # (KP/2)(W/L), value irrelevant
rng = np.random.default_rng(0)
vov = rng.uniform(0.2, 2.5, 20000)
vds = rng.uniform(0.0, 4.0, 20000)

I = np.where(vds >= vov, k * vov ** 2, k * vds * (2 * vov - vds))
I_sat = k * vov ** 2
ratio = I / I_sat

r = vds / vov
predicted = np.where(r >= 1.0, 1.0, r * (2 - r))

err = np.abs(ratio - predicted).max()
print(f"max |I/I_sat  -  q(2-q)|, q = min(r,1)  =  {err:.3e}   over {len(r)} random (V_ov, V_DS)")
print(f"   ({np.mean(r > 1):.0%} of them in saturation, where the clamp is what matters)")
print(f"so the book's current DOES factor as  I_sat(V_GS) * g(r),  r = V_DS/(V_GS-V_th)\n")

for rr in (0.25, 0.50, 0.75, 1.00):
    print(f"   r = {rr:.2f}:   book g = {rr*(2-rr):.3f}     ours g = {rr:.3f}")

print("\nour law uses  g = min(1, (1-v)/x_lin), i.e. r' = (1-v)/x_lin with x_lin CONSTANT,")
print("where the book's normaliser is the overdrive V_ov, which in our variables is (u - vt).")
