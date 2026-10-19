# HSPICE native IBIS on the ex2 variants, V-T tables resampled onto 200 rows

*2026-10-18.* `scripts/native_revived_variants.py`.

**Question.** The 09-04 variant campaign recorded no valid native run on any ex2 variant at any
depth (pad peak about 23 mV, Ku never above 0.1). `native_dead_probe_2026-09-11` traced it to
HSPICE's two-waveform solver on tables sampled at 2.7 ps with 0.2-0.4 mV rms pre-edge ripple, and
showed that coarser sampling (300 rows) revives it. What does the native element score on these five
buffers once that is done?

**Method.** For each of the 25 stressed cases, the case's own `native/input.ibs` with every V-T table
resampled onto 200 rows over its own span (linear interpolation; 13.43 ps in place of
2.68 ps on ex2_base), the campaign's
own `run.sp` unchanged (same bench, 50 ohm and 2 pF, `ramp_rwf=2 ramp_fwf=2`, 2 ps time step), scored as
the cascade sweep scored native (`gate_ramp_prototype.score`: pad peak in [t_rev - 0.1, t_rev + 3.0] ns
against the campaign's transistor run). Validity rule as in `cross_device_stress_metrics` (Ku > 0.3,
Kd < 0.9, pad peak > 0.3 of the transistor's).

**Result.** 25 of 25 cases valid (hspice ran on 25 of 25). The resampled
tables stay within 6.55 mV of the originals.

| variant | depth | width (ps) | native as generated (%) | native resampled (%) | Ku max | Kd min | lag (ps) | valid |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|
| ex2_base | 50 | 812.5 | -97.1 | +62.1 | 1.248 | -0.249 | +300 | yes |
| ex2_base | 60 | 832.5 | -97.6 | +37.8 | 1.253 | -0.25 | +275 | yes |
| ex2_base | 70 | 857.5 | -97.9 | +21.4 | 1.247 | -0.247 | +222 | yes |
| ex2_base | 80 | 895.0 | -97.5 | +9.5 | 1.253 | -0.246 | +185 | yes |
| ex2_base | 90 | 975.0 | -99.9 | +0.2 | 1.257 | -0.257 | +118 | yes |
| ex2_nomiller | 50 | 808.8 | -97.2 | +64.2 | 1.262 | -0.278 | +300 | yes |
| ex2_nomiller | 60 | 830.0 | -97.7 | +37.7 | 1.271 | -0.273 | +275 | yes |
| ex2_nomiller | 70 | 855.0 | -97.2 | +21.1 | 1.283 | -0.276 | +219 | yes |
| ex2_nomiller | 80 | 895.0 | -97.6 | +8.1 | 1.275 | -0.279 | +163 | yes |
| ex2_nomiller | 90 | 975.0 | -97.9 | +0.0 | 1.287 | -0.279 | +115 | yes |
| ex2_skewp | 50 | 757.0 | -95.3 | +51.8 | 1.528 | -0.334 | +295 | yes |
| ex2_skewp | 60 | 773.4 | -96.1 | +29.8 | 1.518 | -0.332 | +250 | yes |
| ex2_skewp | 70 | 796.9 | -96.7 | +14.9 | 1.526 | -0.331 | +202 | yes |
| ex2_skewp | 80 | 843.8 | -97.2 | +3.6 | 1.526 | -0.33 | +153 | yes |
| ex2_skewp | 90 | 937.5 | -96.9 | -2.6 | 1.526 | -0.335 | +99 | yes |
| ex2_slowpre | 50 | 1093.8 | -97.7 | +32.1 | 0.893 | -0.055 | +213 | yes |
| ex2_slowpre | 60 | 1137.5 | -97.5 | +34.1 | 0.992 | -0.054 | +300 | yes |
| ex2_slowpre | 70 | 1193.8 | -94.5 | +18.8 | 1.018 | -0.055 | +259 | yes |
| ex2_slowpre | 80 | 1275.0 | -93.4 | +7.6 | 1.02 | -0.054 | +182 | yes |
| ex2_slowpre | 90 | 1425.0 | -75.6 | +0.7 | 1.018 | -0.054 | +95 | yes |
| ex2_weak | 50 | 706.2 | -100.0 | +60.5 | 1.662 | -0.279 | +300 | yes |
| ex2_weak | 60 | 721.9 | -100.0 | +35.0 | 1.656 | -0.265 | +274 | yes |
| ex2_weak | 70 | 743.8 | -100.0 | +18.6 | 1.651 | -0.283 | +227 | yes |
| ex2_weak | 80 | 787.5 | -100.0 | +6.4 | 1.648 | -0.292 | +177 | yes |
| ex2_weak | 90 | 875.0 | -100.0 | -1.3 | 1.656 | -0.279 | +118 | yes |

**Worst peak error over the five depths, valid cases only** (the number the paper's Table VIII reports):

| variant | worst native peak error (%) |
|---|---:|
| ex2_base | 62.1 |
| ex2_nomiller | 64.2 |
| ex2_skewp | 51.8 |
| ex2_slowpre | 34.1 |
| ex2_weak | 60.5 |

**Reading.** The fault was the simulator's, not the files' content: the same waveforms on 200 rows
run on every variant, and the native element then fails on them as it does on the shipped ex2,
by replaying the coefficients of a complete transition against a pulse that interrupts it.

## How the recipe was chosen (--diagnose, 2026-10-19)

The 50 % case of ex2_skewp, ex2_weak (dead at 300 rows) and ex2_base (alive at 300), under a
matrix of table edits, plus a 10 ns full-swing pulse on three of them (`diagnose/diagnose.csv`):

| variant | recipe | pulse | pad max (V) | Ku max | Kd min | peak error (%) | valid |
|---|---|---|---:|---:|---:|---:|:--:|
| ex2_skewp | asis | 757 ps | 0.021 | 0.188 | 0.063 | -95.3 | no |
| ex2_skewp | asis | 10 ns | 0.888 | 1.576 | -0.34 |  | yes |
| ex2_skewp | flat300 | 757 ps | 0.642 | 1.571 | -0.342 | 43.3 | yes |
| ex2_skewp | flat300 | 10 ns | 0.887 | 1.576 | -0.349 |  | yes |
| ex2_skewp | flat500 | 757 ps | 0.642 | 1.567 | -0.335 | 43.5 | yes |
| ex2_skewp | smooth13 | 757 ps | 0.021 | 0.188 | 0.064 | -95.3 | no |
| ex2_skewp | rows100 | 757 ps | 0.682 | 1.538 | -0.332 | 52.3 | yes |
| ex2_skewp | rows200 | 757 ps | 0.68 | 1.528 | -0.334 | 51.8 | yes |
| ex2_skewp | rows300 | 757 ps | 0.021 | 0.18 | 0.064 | -95.4 | no |
| ex2_skewp | rows300 | 10 ns | 0.887 | 1.542 | -0.329 |  | yes |
| ex2_skewp | rows400 | 757 ps | 0.021 | 0.186 | 0.064 | -95.3 | no |
| ex2_skewp | rows300_flat300 | 757 ps | 0.68 | 1.53 | -0.323 | 51.9 | yes |
| ex2_weak | asis | 706 ps | 0.0 | 0.078 | 0.739 | -100.0 | no |
| ex2_weak | asis | 10 ns | 0.889 | 1.78 | -0.368 |  | yes |
| ex2_weak | flat300 | 706 ps | 0.663 | 1.765 | -0.368 | 49.5 | yes |
| ex2_weak | flat300 | 10 ns | 0.887 | 1.78 | -0.369 |  | yes |
| ex2_weak | flat500 | 706 ps | 0.704 | 1.764 | -0.367 | 58.7 | yes |
| ex2_weak | smooth13 | 706 ps | 0.0 | 0.075 | 0.464 | -100.0 | no |
| ex2_weak | rows100 | 706 ps | 0.716 | 1.636 | -0.295 | 61.4 | yes |
| ex2_weak | rows200 | 706 ps | 0.712 | 1.662 | -0.279 | 60.5 | yes |
| ex2_weak | rows300 | 706 ps | 0.0 | 0.062 | 0.02 | -100.0 | no |
| ex2_weak | rows300 | 10 ns | 0.888 | 1.643 | -0.314 |  | yes |
| ex2_weak | rows400 | 706 ps | 0.0 | 0.062 | 0.474 | -100.0 | no |
| ex2_weak | rows300_flat300 | 706 ps | 0.711 | 1.642 | -0.279 | 60.2 | yes |
| ex2_base | asis | 812 ps | 0.023 | 0.096 | 0.084 | -97.1 | no |
| ex2_base | asis | 10 ns | 1.554 | 1.255 | -0.278 |  | yes |
| ex2_base | flat300 | 812 ps | 1.218 | 1.242 | -0.26 | 56.4 | yes |
| ex2_base | flat300 | 10 ns | 1.552 | 1.268 | -0.273 |  | yes |
| ex2_base | flat500 | 812 ps | 1.218 | 1.241 | -0.272 | 56.3 | yes |
| ex2_base | smooth13 | 812 ps | 1.271 | 1.284 | -0.276 | 63.1 | yes |
| ex2_base | rows100 | 812 ps | 1.276 | 1.223 | -0.268 | 63.8 | yes |
| ex2_base | rows200 | 812 ps | 1.263 | 1.248 | -0.249 | 62.1 | yes |
| ex2_base | rows300 | 812 ps | 1.275 | 1.26 | -0.26 | 63.6 | yes |
| ex2_base | rows300 | 10 ns | 1.557 | 1.267 | -0.266 |  | yes |
| ex2_base | rows400 | 812 ps | 0.022 | 0.096 | 0.083 | -97.1 | no |
| ex2_base | rows300_flat300 | 812 ps | 1.276 | 1.266 | -0.26 | 63.9 | yes |

Every as-generated file runs under the 10 ns pulse, so the solver dies only when the reversal of a
short pulse lands inside the lead-in of the rising table, where the tables carry 0.2-0.4 mV rms of
ripple at 2.2-2.7 ps spacing. A flat lead-in (300 or 500 ps) revives every variant, so the ripple is
the cause on all three; 100 and 200 rows revive every variant, 300 rows only ex2_base (its tables
span 2.7 ns, the others 2.2-2.3 ns, so 300 rows is 7.4-7.7 ps there), 400 rows none, and the 13 ps
moving average only ex2_base. The revived score depends on the edit: the flat lead-in gives 43-56 %,
resampling 52-64 %, smoothing 63 % on ex2_base, because the flat lead-in also removes the real
feedthrough dip that precedes the edge. 200 rows, the least invasive edit that revives all five,
is the recipe of the table above; 100 rows gives the same numbers within two points.
run, and the native element then fails on the variants as it does on the shipped ex2 (+71 % at
810 ps), by replaying coefficients of a complete transition against a pulse that interrupts it.
Nothing else in the files was touched, so these numbers are comparable with the seven buffers on
which native ran as generated. Consumed by `scripts/build_stage_law_doc.py` (Table VIII, starred).
