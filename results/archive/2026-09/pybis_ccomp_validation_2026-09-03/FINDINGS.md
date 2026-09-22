> **SUPERSEDED (2026-09-03).** The conclusion below -- that pybis over-applies
> C_comp -- is wrong. The golden-waveform test in
> `../golden_waveform_test_2026-09-03/` shows nominal C_comp reproduces the
> model's own V-T tables better than any reduced value, on all four tables.
> pybis's C_comp handling is correct; the residual ~5-6 ps lag and the
> falling-edge error are separate defects. Kept for the measurements.

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

---

## Correct-fix investigation: the extraction is clean; the replay method is the cause

Following the correct fix rather than the pragmatic C_comp reduction, two
hypotheses were tested directly.

### Ruled out: the extraction differentiation

`differentiate()` used a forward difference (`(y[i+1]-y[i])/(x[i+1]-x[i])`
stored at index i), a half-step phase lead that would shift the `C_comp * dV/dt`
term the K-parameter solve subtracts. Replaced it with a centered difference and
regenerated the base8 model: **the pad lag stayed at 9.9 ps, unchanged.** The
extraction grid is ~0.6 ps, so its half-step is sub-picosecond and not the
cause. Reverted -- it perturbs the validated silicon extraction for no benefit.

### Ruled out: a wrong or over-applied C_comp value

native IBIS uses the same `.ibs` C_comp = 0.468 pF and tracks the transistor at
every load (RMSE 1-5 mV, shift within 3.4 ps). If the value were wrong, native
would be off too. It is not, so the value is right.

Nor is pybis applying a fixed wrong *fraction* of it. If the only error were
die-cap magnitude, native would always sit between pybis-noCcomp and pybis-Ccomp.
It does not: at 50 Ω + 2 pF native (0.0 ps) is **earlier** than pybis with zero
C_comp (+3.3 ps), and adding capacitance can only slow an edge. So pybis's zero-
C_comp reconstruction is already load-dependently late in a way that has nothing
to do with C_comp.

### The cause: the InputDriven replay approximation

pybis replays `Ku(t)` as a fixed function of elapsed time and injects
`Ku(t) * I_pu(V_die)` -- evaluating the pullup current at the *simulated* pad,
which under a new load does not follow the recorded trajectory `Ku(t)` was
extracted against. That approximation, closed around the C_comp + load node,
produces a load-dependent edge that differs from native's. Native does not make
it: HSPICE's B-element reconstructs from the V-T waveform tables directly, so the
recorded edge (die cap included) is reproduced consistently at any load.

This is structural to the InputDriven method, not a parameter or a bug in one
line. No C_comp value matches native across loads because the discrepancy is not
about C_comp -- it is about how the drive itself is reconstructed.

### Where that leaves the fix

The exact fix -- match native -- means giving pybis a V-T-waveform-based output
stage in place of the `Ku(t) x I_pu(V_die) + lumped C_comp` reconstruction. That
is a redesign of the model's core, with its own validation, not a safe edit to
make speculatively on shipped pybis. The verification here has done its job: it
rules out the cheap fixes and scopes the real one.

Interim, unchanged from above: reducing the explicit C_comp is a net improvement
on realistic (capacitively loaded) nets and is the best available without the
redesign.
