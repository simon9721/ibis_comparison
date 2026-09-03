# Validating the C_comp fix: net-positive, but not the whole story

The lag localization traced pybis's ~10 ps output-stage delay to its explicit
C_comp, and matched native by removing it -- on one load. This validates that
across the load space C_comp actually governs, all against the transistor.

## The result

Pad RMSE vs transistor (mV), rising edge + settle:

| load | native IBIS | pybis (C_comp) | pybis (C_comp=0) |
|---|---:|---:|---:|
| 50 Ω, 0 pF | 4.77 | 31.91 | **26.58** |
| 50 Ω, 2 pF | 1.11 | 17.70 | **9.66** |
| 50 Ω, 10 pF | 2.78 | 8.11 | **5.15** |
| 500 Ω, 2 pF | 2.95 | 21.01 | **12.44** |
| 1 kΩ, 5 pF | 3.32 | 13.34 | **9.86** |

Rising-edge 50% shift vs transistor (ps):

| load | native | pybis (C_comp) | pybis (C_comp=0) |
|---|---:|---:|---:|
| 50 Ω, 0 pF | +1.4 | +9.7 | **−6.3** |
| 50 Ω, 2 pF | −0.0 | +9.3 | +3.3 |
| 50 Ω, 10 pF | −3.4 | +7.3 | +1.0 |
| 500 Ω, 2 pF | +0.3 | +9.3 | +2.2 |
| 1 kΩ, 5 pF | −1.2 | +7.8 | +0.8 |

## Two conclusions, both firm

**1. Removing the explicit C_comp is a strict improvement.** Lower RMSE at all
five loads (18.4 -> 12.7 mV mean, ~31% better) and the +7-10 ps lag collapses to
near zero at four of five. The explicit C_comp over-delays pybis at every load,
so it is a real over-application, not a one-load artifact. That settles the
question theory left open: `solve_k_params_output` does subtract C_comp when
extracting Ku, yet adding it back explicitly still over-delays -- empirically,
across loads, the addition is wrong.

**2. Zeroing it is not the complete fix.** Two things say so:

- **It over-corrects at the cap-lean load.** At 50 Ω + 0 pF, C_comp=0 lands at
  −6.3 ps (now too early), where native is +1.4 ps. With no external capacitance,
  the die cap is the only thing shaping the edge, and removing it entirely takes
  away a real effect. So some C_comp belongs; the shipped full value is too much.
- **native still beats C_comp=0 at every load, and by a lot at 50 Ω + 0 pF**
  (4.77 vs 26.58 mV). When there is no capacitance to filter it, the *other*
  pybis artifact -- the Ku ringing through the transition seen in the lag
  localization -- dominates, and no C_comp setting touches it.

## What this means for the fix

The pybis output stage has two separable errors:

1. **C_comp over-application** -- dominant on any capacitively loaded net, fixed
   in the right direction by reducing/removing the explicit C_comp.
2. **Ku synthesis ringing** -- dominant only on a cap-lean load, untouched by
   C_comp, and a separate problem in the coefficient replay.

So "delete C_comp" is a genuine net improvement and safe to prefer over the
status quo on realistic (capacitively loaded) nets, but it is not the exact fix:
it over-corrects where the die cap is the only capacitance, and it leaves the
ringing untouched. The exact fix reproduces native's C_comp handling -- native
holds near-zero shift and low RMSE at every load, so it applies the die cap
correctly rather than either doubling or dropping it.

## Recommendation

Two options, for a decision, not made here because both change shipped pybis
output for every model:

- **Pragmatic:** reduce the explicit output C_comp (e.g. to zero, or to a
  fraction) as a net-positive on loaded nets, accepting the light-load
  over-correction. Strictly better than today on 5/5 loads.
- **Correct:** rework the output stage so C_comp is applied the way native does
  -- once, in the drive reconstruction rather than as an extra lumped cap on top
  of a Ku that already partly embeds it -- and separately damp the Ku replay
  ringing. Larger change; needs its own validation.

## Files

- `ccomp_validation.csv`, `ccomp_validation.png`
- `<load>/{transistor,native,pybis_ccomp,pybis_noccomp}/` -- the runs
- `scripts/validate_pybis_ccomp.py`
