# The open-drain ex2 under stress

*2026-09-08*

Every stressed buffer in the study is push-pull. The open-drain ex2
(`ex2_variants_2026-09-03/opendrain`, pullup PMOS removed, `Model_type Open_drain`,
one waveform per edge, declared C_comp 5.0 pF) can only pull the pad low and
releases it to a 50 Ω termination to VCC (+2 pF). The stressed event is a short
LOW input pulse. Depth is the low excursion reached as a fraction of the settled
10 ns control (3.30 → 1.327 V).

Transistor (HSPICE, `n4` probed), native (HSPICE, six-node `buffer=2`), ours
(ngspice). Because the OD has one fixture, the transistor's Kd is solved directly
from the bench run: `Kd = (I_gc + I_pc + I_fixture − C_comp dV/dt) / I_pd(V)`.

Figure: `opendrain_stress.png`. Data: `cases.csv`.

---

## 1. Both IBIS models pull all the way down at every width — the regime, in its purest form

| W | depth | transistor low | ours low err | native low err | Kd at min: transistor / ours / native |
|---:|---:|---:|---:|---:|---|
| 10 ns | 100 % | 1.327 V | +4 mV | +2 | 1.01 / 1.00 / 1.00 |
| 0.75 | 90 % | 1.529 | −195 | −115 | 0.77 / 1.01 / 1.02 |
| 0.72 | 79 % | 1.749 | −415 | −321 | 0.68 / 1.02 / 1.02 |
| 0.70 | 65 % | 2.019 | −685 | −579 | 0.50 / 1.02 / 1.02 |
| 0.68 | 47 % | 2.383 | −1049 | −933 | 0.32 / 1.02 / 1.01 |
| 0.66 | 28 % | 2.753 | −1419 | −1180 | 0.21 / 1.01 / 1.16 |
| 0.64 | 13 % | 3.051 | −1717 | −1445 | 0.08 / 1.00 / 1.37 |
| 0.62 | 4 % | 3.225 | −1891 | −1587 | 0.02 / 1.00 / 1.31 |

The transistor's excursion runs smoothly from 4 % to 90 % across 130 ps of input
width. **Ours reaches ~1.4 V — essentially full low — at every width**; native
reaches 1.45–1.62 V. Both have Kd = 1.0 at the pad minimum regardless of depth,
where the transistor's Kd runs 0.77 → 0.02.

This is `two-stress-regimes` with nothing else in the way: the model's pull-down
gate is fully on because the stored trajectory is replayed from the input edge,
and the device's is not. The OD follows the eleven push-pull buffers, not io_buf,
and does so more severely than any of them (their worst was +71 % at 50 % depth;
here the excursion error is 100 % of the swing below ~30 % depth).

## 2. The transistor's own Kd and gate scale with depth

| depth | Kd at min | Kd/depth | n4 at min |
|---:|---:|---:|---:|
| 90 % | 0.765 | 0.85 | 2.45 V |
| 79 % | 0.681 | 0.86 | 2.29 |
| 65 % | 0.504 | 0.77 | 2.02 |
| 47 % | 0.318 | 0.68 | 1.65 |
| 28 % | 0.205 | 0.73 | 1.31 |
| 13 % | 0.076 | 0.60 | 0.90 |
| 4 % | 0.024 | 0.63 | 0.54 |

Kd at the minimum is roughly 0.6–0.85 × depth. And unlike the push-pull ex2
stress cases (where `n4` reached ~70 % of its swing at every width), here the real
gate **is truncated** — 2.45 → 0.54 V — because these widths (0.62–0.75 ns) fall
inside the predriver's ~0.7 ns swing time, while the push-pull stress widths
(0.81–0.98 ns) did not. The same predriver shows both behaviours; the pulse width
relative to its swing time decides which.

## 3. Our OD model is the legacy build, and it rests in the wrong state

`subcircuit.py` line 2893: *"InputDrivenTwoStateGate v1 is push-pull only; using
legacy Kd control for open-drain."* Every "ours" above is the legacy table-replay
Kd, not the gate-state architecture. Two consequences visible in the figure:

* **Wrong rest state.** With the input resting high (pad released) ours sits at
  1.334 V — pulled low — and releases over the first 0.7 ns after the stimulus
  begins. The legacy control needs an edge before it knows its state. This is a
  converter defect independent of stress.
* **~120 ps late on both edges at full swing**, measured with the glitch excluded:
  pull-down 50 % at +1.210 ns against the transistor's +1.094 (+116 ps), release
  +1.137 against +1.008 (+129 ps). Native is 46–62 ps *early* on both. Under
  stress ours grows to the +500 ps search bound; native stays +80…+140.

Native's Kd exceeds 1 (1.16–1.37) at the deepest stress — the single-waveform
`rwf_tune` path, not a physical value.

## 4. The C_comp loop, on a single-fixture solve

Sweeping the C_comp used in the Kd solve and minimising the Kd-vs-`n4` loop:

| W | argmin | min loop | loop at declared 5.0 |
|---:|---:|---:|---:|
| 10 ns | 3.00 pF | 0.030 | 0.290 |
| 0.75 | 3.00 | 0.025 | 0.265 |
| 0.72 | 3.00 | 0.020 | 0.234 |
| 0.70 | 3.00 | 0.017 | 0.195 |
| 0.68 | 3.25 | 0.018 | 0.128 |

Sharp, width-independent minimum at **3.0 pF** — against 5.0 declared, but
**above** the 1.5–1.75 pF the push-pull ex2 gave (`gate_physics_2026-09-08`). The
prediction that removing the pullup PMOS would lower it failed. The explicit
Miller caps (`cx3/cx5/cx8`, n4→out) total 20 fF and cannot account for a 1.3 pF
gap. What differs: a single-fixture solve on a pad swinging 1.3–3.3 V versus a
two-fixture solve on 0–1.5 V; device Cgd and drain-junction capacitance are
voltage-dependent and the two solves absorb them differently. **Both numbers are
effective capacitances for their own solve; the gap is open.** Both say the
declared 5.0 pF is wrong.

## What this means

* Open-drain confirms the regime result with no push-pull machinery in the loop:
  the defect is the gate being fully on when the device's is not, and it is shared
  with native.
* Our converter has no gate-state model for `Open_drain` at all; the legacy
  fallback has a wrong rest state and a ~120 ps baseline lag. That is the first
  thing to fix for OD, before any stress work.
* Two OD variants (`od_weak`: pull-down at half width; `od_slowpre`: predriver at
  half width) are composed under `ex2_variants_2026-09-03/od_*` and characterising;
  their stressed runs will say whether the depth law in §2 is buffer-specific.

## Caveats

* One OD buffer, eight widths, one bench. Depth below ~30 % puts the transistor's
  Kd solve inside its own noise floor (Kd_min 0.02–0.08).
* `n4` here is the same node as on push-pull ex2 but drives NMOS only; its
  excursion at full swing is 3.40 V (Miller overshoot above supply).
* The "lag" column in `cases.csv` includes the rest-state glitch for ours; the
  honest full-swing numbers are the crossing times in §3.

---

## 5. Variant od_weak: pull-down at half width (added later the same day)

IBIS from the selector's probe (`s2ibispy_parameter_selection_ex2_od_weak_2026-09-02/probe`,
tr = 200 ps; the selector's own gates timed out at the finish line but the file is
ibischk-clean). Settled low 2.066 V — a half-width pull-down into 50 ohm cannot
pull below that. Sweep in `../opendrain_stress_od_weak_2026-09-08/`.

| depth | transistor low | ours low err | native low err | Kd at min: transistor / ours / native |
|---:|---:|---:|---:|---|
| 101 % | 2.066 V | +1 mV | +2 | 1.00 / 1.03 / 1.03 |
| 86 % | 2.255 | −185 | **+423** | 0.84 / 1.02 / 0.67 |
| 79 % | 2.340 | −271 | **+801** | 0.70 / 1.02 / **−0.82** |
| 72 % | 2.421 | −352 | +778 | 0.66 / 1.02 / −0.82 |
| 61 % | 2.554 | −484 | +746 | 0.52 / 1.02 / 0.00 |
| 43 % | 2.779 | −709 | +521 | 0.40 / 1.02 / −0.30 |
| 22 % | 3.037 | −967 | +263 | 0.16 / 1.01 / −0.50 |
| 7 % | 3.216 | −1146 | +84 | 0.06 / 1.01 / −0.71 |

**Ours behaves exactly as on the base OD**: Kd = 1.02 at the minimum at every
depth, pad bottoming at 2.19 V regardless of width. The regime does not depend on
drive strength.

**Native malfunctions on this variant.** From 86 % depth down its Kd goes
negative (to −0.82) and its pad is driven *above* VCC to 3.6 V on every stressed
pulse — the pull-down sourcing current. Single-waveform mode with this table is
not a usable reference below ~85 % depth (lag pinned at −500 ps).

**The transistor's law is the same law.** Kd at the pad minimum against depth:

| | fit | R² |
|---|---|---:|
| base OD | Kd_min = 0.87 · depth − 0.04 | 0.990 |
| od_weak | Kd_min = 0.95 · depth − 0.03 | 0.988 |

and the real gate `n4` at the pad minimum tracks depth with corr 0.993 (base) and
0.997 (od_weak). A weaker output device changes the settled level and the slope
slightly, not the form: **how far the pull-down coefficient gets is proportional
to how far the output got**, on both open-drains — the same statement the twelve
push-pull buffers made for Ku.

`od_slowpre` (predriver at half width) is characterising with a longer conversion
limit; the first attempt exceeded the selector's 1200 s while HSPICE was shared.

## 6. Variant od_slowpre: predriver at half width

IBIS from the selector's probe (retried with a 3600 s conversion limit; the first
attempt exceeded 1200 s while HSPICE was shared). Sweep in
`../opendrain_stress_od_slowpre_2026-09-08/`. The slower predriver moves the
onset cliff later: the base grid (0.62–0.75 ns) reached only 0.5–46 % depth, so
this variant was swept at 0.75–1.00 ns.

| W | depth | transistor low | ours low err | native low err | Kd at min: transistor / ours / native |
|---:|---:|---:|---:|---:|---|
| 10 ns | 100 % | 1.330 V | +3 mV | +2 | 1.01 / 1.01 / 1.01 |
| 1.00 | 97 % | 1.391 | −57 | +4 | 0.94 / 1.01 / 1.01 |
| 0.94 | 95 % | 1.433 | −99 | −22 | 0.90 / 1.01 / 1.01 |
| 0.88 | 90 % | 1.529 | −195 | −99 | 0.81 / 1.01 / 1.02 |
| 0.84 | 83 % | 1.676 | −342 | −224 | 0.72 / 1.01 / 1.00 |
| 0.80 | 70 % | 1.924 | −590 | −417 | 0.57 / 1.01 / 1.09 |
| 0.77 | 57 % | 2.190 | −856 | −681 | 0.43 / 1.00 / 1.10 |
| 0.75 | 46 % | 2.398 | −1064 | −874 | 0.34 / 1.00 / 1.02 |

Same picture: **ours and native both pull essentially all the way down at every
width** (Kd 1.0 at the minimum), the transistor's Kd tracks depth. Native behaves
on this variant — the od_weak malfunction is specific to the weak pull-down's
table. Our full-swing lag on this build is +304 ps (rest-state glitch included).

### The law across the three open-drains

| buffer | depths covered | fit | R² | corr(n4 at min, depth) |
|---|---|---|---:|---:|
| base OD | 13–90 % | Kd_min = 0.90 · depth − 0.06 | 0.989 | 0.997 |
| od_weak | 7–86 % | Kd_min = 0.95 · depth − 0.03 | 0.988 | 0.997 |
| od_slowpre | 46–97 % | Kd_min = 1.15 · depth − 0.21 | 0.990 | 0.992 |

Linear in depth at R² ≥ 0.99 on every one. The slopes differ and the ranges
differ, so the slope is not a single constant across buffers — the slow predriver
gives a steeper line with a lower intercept over its (higher) range — but the
**form** is the same everywhere: the pull-down coefficient at the pad minimum is
set by how far the output actually got, and the real gate at that instant tracks
depth at corr ≥ 0.99. That is what every IBIS model here lacks.
