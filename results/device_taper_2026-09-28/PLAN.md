# Can the device's own taper replace `x_lin = 0.45`?

*Written before the numbers, 2026-09-28. Findings in `FINDINGS.md`.*

## Why

`x_lin` is the least defensible thing in the stage law. `docs/stage_law_walkthrough.md` §4.4
tier 4 lists it twice over: the **straight line** has no source, and the **constant boundary**
has no source. On top of that it is not even fitted — 360 of ~390 fit rows hold it at 0.45
exactly, and where it is free it lands anywhere from 0.02 to 1.50.

SPICE Level 1 (Leventhal & Green §3.8 p.89, eq. 3-24/3-25) gives a drain factor that is both a
different curve and a different boundary:

```
I/I_sat = q(2 − q),   q = min(r, 1),   r = headroom / overdrive
```

The boundary is the **overdrive**, which moves with the gate. Substituting it **removes a
parameter**, because `x_lin` collapses into `vt`.

## The closed form that motivates it

At full gate drive the overdrive is `1 − vt`, so the device taper begins at `v = vt`; the
constant taper begins at `v = 1 − x_lin`. Equating:

```
x_lin_equivalent  =  1 − vt
```

So the device form does not invent a new number — it **ties the boundary to the threshold**.
ex2's file-only `vt = 0.528` implies `x_lin = 0.472`, which is nearly the pinned 0.45. That is
either a pleasing coincidence or the reason 0.45 works, and this study should say which.

## The experiment

Four drain factors, **one integrator** (Heun, 1 ps substeps — verified identical to
`cl.simulate` to 1.1e-16), **one optimiser budget** (Nelder–Mead, 3 restarts, maxiter 800),
fitted to **full swing only** and then asked to predict the stressed gate. This is the §8 bench.

| kind | drain factor | boundary | params |
|---|---|---|---:|
| `linear_const` | `min(1, d/x_lin)` | constant | 4 |
| `parab_const` | `q(2−q), q = d/x_lin` | constant | 4 |
| `linear_ov` | `min(1, d/ov)` | **moving** | 3 |
| `parab_ov` | `q(2−q), q = d/ov` | **moving** | **3** |

The 2×2 is deliberate: it separates **curve shape** from **boundary**, so a loss can be
attributed to one or the other rather than to "the device form" as a lump.

Buffers: ex2 (K=3) and inv_chain (K=7), the counts §8 established. `p = 1` throughout, so the
gate exponent is held constant and does not confound.

## Hypothesis, recorded in advance

**At full drive the two boundaries nearly coincide** (0.528 vs 0.550 on ex2), so the full-swing
fit should barely distinguish them. They diverge under **partial** drive, where the device form
keeps the stage current-source-like for longer:

| gate drive | device taper starts at `v` | constant taper starts at `v` |
|---|---|---|
| 1.0 | 0.528 | 0.550 |
| 0.8 | 0.728 | 0.550 |
| 0.6 | 0.928 | 0.550 |

§8 shows today's model runs **consistently low** on ex2 — 0.755/0.782/0.813/0.847/0.898 against
measured 0.758/0.797/0.838/0.880/0.936. More current under partial drive should push predictions
**up, toward the measurement**.

**So: `parab_ov` should fit full swing about as well with one parameter fewer, and predict the
stressed gate better.** If it does neither, the hypothesis is wrong and 0.45 is doing real work
that the device form cannot.

## The risk to watch

In the `_ov` kinds `vt` takes **two jobs**: the gate threshold and the saturation boundary. They
pull in **opposite directions** — a larger `vt` turns the stage on later (slower) but shrinks the
overdrive, which keeps it saturated longer (faster). That is the shape of the `pu_off` trap, where
one parameter serving two purposes proved underivable.

If `parab_ov` fits worse, the fifth variant to try is a parabola with a moving boundary carrying
its **own** threshold `vt_d` — back to 4 parameters, but a threshold has a physical referent where
`x_lin` has none, so it would still be a gain in defensibility.

## Decision rule

| outcome | conclusion |
|---|---|
| `parab_ov` full-swing rms within ~25 % of `linear_const`, stressed error no worse | **adopt it** — one parameter fewer and a sourced form; then test the same swap in the Ku domain, which is what track 1 actually fits |
| full swing fine, stress worse | the constant boundary is doing real work; say so and keep it, with the reason |
| full swing much worse | `vt`'s two jobs conflict; try the 5th variant before concluding |

A win here is **not** sufficient. This bench fits against the **probed** gate. Track 1 fits in the
**Ku domain** through an assumed map (§6.3), and that test has to pass too before anything ships.
