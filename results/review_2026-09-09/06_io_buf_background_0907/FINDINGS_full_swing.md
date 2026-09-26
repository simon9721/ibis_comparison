# The transistor's own coefficients at full swing

*2026-09-07*

The reference that never existed. The stress matrix carries `silicon_ku` /
`silicon_kd` for stressed cases only, so every full-swing coefficient comparison
in this project has leaned on native. Two HSPICE runs of the transistor into the
IBIS fixtures (50 ohm to 0 V and to VCC) on the campaign's own `long_control`
case — rise 5 ns, fall 15 ns — close that.

It answers the open question from `../pu_off_scale_2026-09-07/` and produces one
result that changes how native should be used.

---

## 1. Yes, the transistor's Ku really does overshoot — early and briefly

| grid | Ku before | Ku peak | t of peak | overshoot | cond max |
|---|---:|---:|---:|---:|---:|
| union | — | 1.5016 | 52 ps | — | 3.2 |
| 1 ps | 0.9797 | 1.4889 | 52 | +0.509 | 3.2 |
| 2 ps | 0.9797 | 1.3801 | 52 | +0.400 | 3.2 |
| **5 ps** | 0.9797 | **1.1672** | **25** | +0.187 | 3.2 |
| 10 ps | 0.9797 | 1.1474 | 30 | +0.168 | 3.2 |

The **existence** of the overshoot is robust — every grid shows Ku rising above
its settled 0.98. The **magnitude** is not converged (1.15 to 1.49), because the
peak sits inside the region the `C_comp dV/dt` finite difference dominates. The
two coarsest grids agree to 0.02, so ~1.15–1.17 at +25–30 ps is the defensible
reading.

**This settles the open question:** "preserve the reversal overshoot" is a
legitimate objective, not an artifact of our own model's phasing. The `pu_off`
conflict does not dissolve.

Convergence check, spread across the 1/2/5/10 ps solves — the same +90 ps boundary
as the stressed cases:

| window | Ku spread | Kd spread |
|---|---:|---:|
| 0..50 ps | 0.0300 | 0.0208 |
| 50..100 ps | 0.0540 | 0.0331 |
| **90..140 ps** | **0.0031** | 0.0003 |
| 150..200 ps | 0.0007 | 0.0001 |

## 2. Both IBIS models make the overshoot **late and broad**

| t−fall | transistor | native | ours x0.70 | ours x0.10 |
|---:|---:|---:|---:|---:|
| 0 | 0.9005 | 1.0000 | 0.9931 | 0.9931 |
| **30** | **1.1572** | 1.0000 | 0.9936 | 0.9936 |
| 70 | 0.8766 | 1.0695 | 1.1621 | 0.9474 |
| 90 | 0.7798 | 1.1675 | 0.9095 | 0.7003 |
| 150 | 0.4813 | 0.7689 | 0.5545 | 0.3773 |
| 250 | 0.2009 | 0.3141 | 0.2475 | 0.1478 |

The transistor peaks at **+25–30 ps** and is already below its settled value by
+70 ps. Native peaks at **+83 ps** and is still at 1.17 at +90 ps. Ours peaks at
+70 ps.

**The transistor's Ku overshoot is early and narrow; both IBIS models make it late
and broad.** That is the full-swing coefficient defect, and it has not been stated
before because the reference did not exist.

It also explains the `pu_off` conflict in the transistor's own terms rather than
native's. `pu_off` delays the gate turn-off, which is what pushes our overshoot
late. Shortening it moves the overshoot earlier *and removes it*, because the
residual spike then lands on an already-falling gate. The transistor wants the
overshoot **early and present**; the parameter can deliver early-and-absent or
late-and-present, never both.

## 3. Native's Ku is 1.52x the transistor at full swing

Ku ratio to the transistor over +90..+400 ps, both stress levels:

| pu_off scale | stressed | full swing |
|---:|---:|---:|
| 0.10 | **1.07** | 0.80 |
| 0.20 | 1.14 | 0.86 |
| 0.29 | 1.21 | 0.91 |
| **0.40** | 1.30 | **0.97** |
| 0.50 | 1.40 | 1.03 |
| 0.70 | 1.60 | 1.15 |
| 1.00 | 1.94 | 1.36 |
| **native** | **1.07** | **1.52** |

Two things follow.

**Native is not a uniformly reliable coefficient reference.** It tracks the
transistor to 1.07x under stress and is **1.52x too high at full swing** — worse
in that window than any of our settings between 0.10 and 0.70. Previous statements
of the form "native tracks the transistor closely" were measured on stressed cases
and do not transfer.

**The optimal `pu_off` is state-dependent.** The scale giving a ratio of 1.00 is
**0.10 or below when stressed** and **0.45 at full swing**. A single fixed value
cannot serve both, and this is measured against the transistor rather than
inferred from an overshoot trade. It is the same structural gap as everywhere
else: a fixed parameter standing in for something the real device varies with
state.

## Caveats

* io_buf only, typical corner, one stimulus per stress level.
* The overshoot magnitude is grid-limited; only its existence, timing and rough
  size (~1.15–1.17) are defensible.
* HSPICE's adaptive output gives 30 samples in the first 150 ps (median 2.7 ps)
  and 10–28 ps through +90..+400 ps, comparable to the stressed fixture runs, so
  the two stress levels are compared on equal footing.
* The Ku ratio in +90..+400 ps is a coefficient measure. Ku multiplies `I_pu(V)`,
  which is small late in a fall, so a 1.5x error there does not imply a 1.5x pad
  error — and indeed native's full-swing **pad** is close. The two should not be
  conflated.
* The `UNIFORM_GRID_PS` comment in `extract_silicon_kukd.py` already documented
  the grid mechanism and the "conditioning is not the problem" result. The
  conditioning work in `../silicon_kukd_conditioning_2026-09-07/` re-derived it
  independently; credit belongs to the original note.
