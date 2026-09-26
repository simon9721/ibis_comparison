# The transistor's coefficient spike is a differentiation artifact, not ill-conditioning

*2026-09-07*

`pu_off_scale_2026-09-07` claimed the transistor's stressed Ku near a reversal
(1.2892 at +49 ps on io_buf 1792 ps, from a pull-up that entered the fall at 0.48)
is a solve artifact that cannot anchor a delay. The claim was right. **The
mechanism given for it was wrong**, and it is corrected here.

---

## The stated mechanism is falsified

`solve_silicon_kukd` records `cond(M)` in column 3. Re-solving the stressed
two-fixture transistor runs and reading it out:

| width | cond at the reversal | cond baseline (+150..+400 ps) | ratio |
|---|---:|---:|---:|
| 2354 | 2.6 | 1.5 | 1.7 |
| 1989 | 2.4 | 1.5 | 1.6 |
| 1792 | 2.3 | 1.5 | 1.6 |
| 1505 | 2.0 | 1.4 | 1.4 |

**The 2x2 system is well conditioned everywhere** — never above 2.7, and only
1.4–1.8x its own baseline at the reversal. This agrees with the standing negative
result in `two_fixture_conditioning.py` (io_buf's characterisation tables: 2.7
median, 3.1 max) rather than contradicting it, and it kills "ill-conditioned
solve" as the explanation.

## The actual mechanism: the `C_comp dV/dt` finite difference

The solver's own docstring warns that differentiating across grids amplifies the
interpolation staircase. Re-solving the same runs at different grids:

**Ku peak in a −20..+300 ps window about the reversal**

| width | MATRIX csv | union | 1 ps | 2 ps | 5 ps | 10 ps |
|---|---:|---:|---:|---:|---:|---:|
| 2354 | 0.9988 | 1.2660 | 1.2618 | 1.1564 | 0.9919 | 0.9800 |
| 1989 | 1.0661 | 1.4147 | 1.1124 | 1.0913 | 0.8654 | 0.8432 |
| 1792 | **1.2892** | 1.3488 | 1.0605 | 0.9307 | 0.8831 | 0.7808 |
| 1505 | 1.1604 | 1.3576 | 1.1826 | 0.9761 | 0.7028 | 0.6878 |

**Kd minimum, same window**

| width | MATRIX csv | union | 1 ps | 2 ps | 5 ps | 10 ps |
|---|---:|---:|---:|---:|---:|---:|
| 1792 | −1.1858 | −2.0162 | −1.6781 | −1.5482 | −0.8276 | −0.4149 |
| 1505 | −0.3727 | −1.5585 | −1.3322 | −1.3154 | −0.7231 | −0.3820 |

**The value does not converge.** It grows monotonically as the grid refines — the
signature of a quantity dominated by differentiation noise, not of a converged
physical measurement. A real coefficient would settle as the grid refines; this
diverges. The excursion is set by the numerics, so no number read from that region
means anything about the buffer.

## The +90 ps window is validated independently

Grid dependence does not extend into the window this investigation scores in. RMS
spread across the 1 / 2 / 5 / 10 ps solves, io_buf 1792 ps, by 50 ps slice:

| window | Ku spread | Kd spread |
|---|---:|---:|
| 0..50 ps | 0.0304 | 0.0370 |
| 50..100 ps | 0.0375 | 0.0360 |
| **90..140 ps** | **0.0012** | **0.0001** |
| 150..200 ps | 0.0017 | 0.0001 |
| 250..300 ps | 0.0013 | 0.0000 |
| 350..400 ps | 0.0004 | 0.0001 |

A 30x collapse right at +90 ps. And inside +90..+400 ps every grid agrees with the
matrix CSV to rms 0.003 on Ku and 0.002 on Kd, with mean Ku spanning
0.1023–0.1046 across all five solves at 1792 ps — a 2% spread.

**The +90 ps window start was chosen before this test was run**, on the grounds
that the visible spike sat near +50 ps. Convergence independently puts the
boundary in the same place. So the scoring in
`../pu_off_scale_2026-09-07/` rests on a grid-converged reference.

## What this changes

* **Keep the claim, change the reason.** The transistor's coefficients near a
  reversal are unusable — because of the `C_comp dV/dt` finite difference, not
  because the solve is near-singular.
* **`two_fixture_conditioning.py`'s negative result stands** and now covers the
  stressed solve too.
* **Everything scored at +90..+400 ps is sound.** That includes the Ku/Kd rms and
  ratio tables that carry the "Kd is solved, Ku is not" conclusion.

## Caveats

* io_buf short-high only.
* Which grid is "right" near the reversal is not established here, and this does
  not attempt to. The point is only that no grid gives a converged answer there,
  so the region must be excluded rather than fitted.
* The matrix CSV's own values sit between the union and 1 ps solves, so the matrix
  was built on a fine grid. That is fine for +90 ps onward and unusable before it.
