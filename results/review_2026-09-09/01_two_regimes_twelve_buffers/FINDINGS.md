# Twelve stressed buffers, one instrument

*2026-09-08*

Every finding in the 2026-09-07 series was about io_buf short-high. This runs one
instrument (`scripts/cross_device_stress_metrics.py`) over every stressed
short-high case that exists — nine variants × five depths plus the three base
buffers — with the transistor as reference throughout: its pad into the study
load, its Ku/Kd re-solved from the two fixture runs at 5 ps with the 2/10 ps
spread recorded. 68 cases, 0 failures. Figure: `cross_device_stress.png`.

Depth is the transistor's stressed excursion as a fraction of its settled
full-swing excursion (io_buf plateau 1.5233 V from `defect_b_full_swing`, hspice.mod;
inv_chain 1.4222; ex2 1.5451). The stress matrix's io_buf cases run 37–80% depth,
the variants 50–100%.

---

## 1. Two regimes, and io_buf is alone in one of them

| | eleven buffers (inv, ex2 families) | io_buf |
|---|---|---|
| where the pad peaks | 90–830 ps **after** the input reversal | ~100 ps after |
| our gate τ_rise | 20 ps (inv), 135–337 ps (ex2) | **1127 ps** |
| stressed peak, ours vs transistor | **+34…+71 % too tall** at 50% depth | ±3 % |
| Ku over the event, ours/transistor | rises 1.0 → 1.42 with stress | **falls** 1.24 → 0.93 |
| pull-up turn-off lateness | grows with stress | shrinks |

Peak-excess slope, % per 10% of depth lost: inv 7.7–12.9, ex2 11.0–16.7,
**io_buf −1.3**. Every trend that grows with stress on the other eleven is flat
or reversed on io_buf. The correction derived on io_buf (`FRAC`, `pu_off`) was
built for the regime only io_buf is in.

## 2. The mechanism on the eleven: entering the reversal too far on

Define the **entry excess** as our Ku at the transistor's pad peak minus the
transistor's Ku there. Ours enters at 0.87–1.14 where the transistor enters at
0.2–0.7:

| | transistor Ku at its pad peak, 90%→50% depth | ours |
|---|---|---|
| inv_base8 | 0.72 → 0.31 | 0.90 → 1.01 |
| ex2_base | 0.65 → 0.25 | 0.96 → 1.14 |
| io_buf | 0.43 → 0.17 | 0.80 → 0.36 |

The transistor's pull-up is only part-way on when its output turns; ours is fully
on. The pad then rises past where the device turned. **Correlation of entry excess
with pad-peak excess: 0.889 pooled over 68 cases, and 0.86–0.98 within every one
of the twelve buffers** (io_buf 0.98 — both small there). The turn-off and
re-engage lateness that grow with stress are the same defect seen in time rather
than amplitude: normalised by event length they rise 3–7 percentage points per
10% depth on all eleven, and the ordering across buffers matches the peak-excess
ordering.

**Native fails identically wherever it is alive** — peak-excess slope 13.3 vs our
12.9 on inv_base8, 16.7 vs 15.7 on ex2, and within 1–3 % of ours case by case on
inv_skewp/inv_weak. On the matrix inv_chain it is worse (+89 % vs our +34 % at 49%
depth). So this is a limit of replaying a stored, time-indexed trajectory from
the input edge — the IBIS mechanism — not something our converter adds.

Why io_buf escapes it: its gate is slow enough (τ_rise 1.13 ns against a
0.6–1.4 ns commanded pulse) that GUP has *not* saturated when the reversal
arrives, so the entry is only moderately high and the residual dominates. Tested
as a law — commanded pulse ÷ τ_rise against entry excess — it does **not** hold
across cases (r = 0.02): within a buffer the entry excess grows with stress while
that ratio falls, because the driver is the transistor's own Ku collapsing (0.72
→ 0.31) against ours staying put. io_buf's ratio of 0.5–1.3 against 1.7–8.4 for
everyone else is a distinguishing property, not a fitted mechanism.

## 3. The io_buf residual finding generalises to 12 / 12

The transistor's Kd residual after the reversal (its minimum, in the
grid-converged window) shrinks toward zero as stress deepens on every buffer;
ours is a constant set by the full-transition calibration:

| buffer | transistor Kd min, 90% → 50% depth | ours |
|---|---|---|
| inv_base8 | −0.070 → −0.035 | −0.067 throughout |
| ex2_base | −0.097 → −0.018 | −0.100 throughout |
| ex2_slowpre | −0.052 → **+0.024** (crosses zero at 65%) | −0.053 |
| io_buf | −0.104 → −0.070 (80% → 37%) | −0.188 |

Slope toward zero is positive on all twelve (0.0007–0.0315 per 10% depth). This
is `pedestal-is-the-kd-residual` as a general statement. An earlier pass of this
instrument read a sign flip on eight buffers; that was a window artifact (it
caught Kd rising back to 1 after the event) and is withdrawn. Two buffers do
genuinely cross zero: ex2_slowpre (at 65%) and inv_stage4 (+0.08 at 50%) — the
latter with its event only ~90 ps after the reversal, so its residual minimum
sits inside the grid-noise zone and the value is indicative, not precise. Our
io_buf residual (dashed black in the figure) is jagged across widths because the
matrix CSVs sample the short negative spike coarsely; the stable value from the
2 ps ngspice runs is −0.188.

## 4. Pedestal sign, settled against the transistor

Our pad lags the transistor's on **every** stressed case: inv 6 → 67 ps, ex2 79 →
300 ps (saturating the search bound), io_buf 63 → 71 ps flat. The earlier
"opposite sign on inv_chain and ex2" (`native_waveform_count_2026-09-04`) was
measured against native, whose own sign varies by device — on io_buf native is
*early* against the transistor (−11 to −28 ps) while we are late, which is where
the ~90 ps pedestal-vs-native came from. Against truth we are late everywhere.

On the eleven, the pedestal is not a separate timing defect: at ex2_base 50% depth
our pad is 1.333 V against 0.779 and still at 1.298 V at +900 ps where the
transistor is at 0.307 — the "lag" is a 71 %-too-tall pulse draining through the
load.

## 5. No secondary event outside io_buf

The +1.8 ns pull-down turn-on bump is an io_buf feature. On inv_chain the pad
returns to zero and stays there (1–2 mV of noise); on ex2 it decays monotonically.
An earlier pass reported an ex2 bump moving the wrong way; that was an argmax on a
monotone tail and is withdrawn. `bump-is-the-timing-marker` is io_buf-only.

## 6. Native is dead on the tr1ps variant IBIS files

On every ex2 variant at every depth, and on inv_stage4 below 90%, native's pad
never rises (peak error −700…−1400 mV), its Ku never exceeds 0.1 and its Kd never
leaves 1. No warning in `run.lis`. The matrix ex2 IBIS (8 ns tables) is fine; the
variant files carry 2.2–3.9 ns tables — but span alone does not separate dead from
alive (inv_stage4 dies at 0.41 ns, inv_base8 lives at 0.62; all inv tables end
unsettled at 0.204 V). Root cause open. Consequence: on those 30 cases the only
IBIS reference is ours, and the comparisons above are ours-vs-transistor only.

## 7. Per-buffer command layer and gate, for reference

| buffer | pu_on | pu_off | pd_off | pd_on | slice | τ_rise | τ_fall | C_comp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| inv_base8 | 267 | 244 | 238 | 274 | 23 | 20 | 25 | 0.468 pF |
| inv_stage4 | 102 | 79 | 74 | 109 | 23 | 20 | 25 | 0.468 |
| inv_skewp | 262 | 251 | 235 | 284 | 11 | 20 | 26 | 0.468 |
| inv_weak | 280 | 255 | 251 | 290 | 25 | 21 | 25 | 0.468 |
| inv_chain | 268 | 247 | 242 | 278 | 21 | 20 | 26 | 0.468 |
| ex2_base | 996 | 733 | 737 | 981 | 263 | 175 | 167 | 5.0 |
| ex2_slowpre | 1233 | 724 | 788 | 1199 | 508 | 337 | 361 | 5.0 |
| ex2_skewp | 970 | 650 | 684 | 889 | 320 | 151 | 220 | 5.0 |
| ex2_weak | 880 | 641 | 582 | 934 | 239 | 135 | 190 | 5.0 |
| ex2_nomiller | 994 | 683 | 738 | 980 | 311 | 174 | 214 | 5.0 |
| ex2 | 1001 | 668 | 709 | 983 | 333 | 178 | 235 | 5.0 |
| io_buf | 993 | 68 | 850 | 1831 | 925 | 1127 | 112 | 1.2 |

(ps, except C_comp.) All twelve IBIS files carry exactly two waveform tables per
edge, so the manual's pad-voltage selection rule is dormant on every one. ex2's
5.0 pF C_comp is identical across corners and untested against the netlist;
io_buf's 1.2 pF is already known to be 2–5× the measured value.

## What this means for the model

* The io_buf corrections (`FRAC` on the residual, shortened `pu_off`) address the
  residual regime. They are the right shape for io_buf and **not for the other
  eleven**, where the residual is a minor term and the defect is the entry level.
* The entry level is set by the gate state having saturated during a commanded
  pulse the transistor's internal node never completed. Fixing it means the
  gate's *target* or *rate* must depend on how far the previous transition got —
  the same state carry-over gap, now with 68 cases behind it and shared with
  native.
* The residual shrinking toward zero with stress is the one universal amplitude
  law found (12/12). It is the natural next thing to build into the residual's
  scaling, replacing the io_buf-specific FRAC.

## Caveats

* Short-high only. All three short-low sets are unusable as instrumented
  (io_buf's model over-dips; the inv and ex2 short-low events need a mirrored
  instrument) and were skipped.
* Depth for the matrix cases is against a plateau from a different run set; the
  variants' depth is the study's own definition. Both are ±2%.
* The in-event grid spread is ≤ 0.025 on inv (fast events, 5 ps grid is coarse for
  them) and ≤ 0.013 on ex2; conclusions rest on differences of 0.1–0.9.
* `gate_state` (the superseded build) is in the CSV but not discussed; it
  misbehaves on several inv variants (Ku ratios 7–19) and is not the shipped model.
