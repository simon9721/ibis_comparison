# HSPICE native IBIS on the ex2 variants, V-T tables resampled onto 300 rows

*2026-10-18.* `scripts/native_revived_variants.py`.

**Question.** The 09-04 variant campaign recorded no valid native run on any ex2 variant at any
depth (pad peak about 23 mV, Ku never above 0.1). `native_dead_probe_2026-09-11` traced it to
HSPICE's two-waveform solver on tables sampled at 2.7 ps with 0.2-0.4 mV rms pre-edge ripple, and
showed that coarser sampling (300 rows) revives it. What does the native element score on these five
buffers once that is done?

**Method.** For each of the 25 stressed cases, the case's own `native/input.ibs` with every V-T table
resampled onto 300 rows over its own span (linear interpolation; 8.94 ps in place of
2.68 ps on ex2_base), the campaign's
own `run.sp` unchanged (same bench, 50 ohm and 2 pF, `ramp_rwf=2 ramp_fwf=2`, 2 ps time step), scored as
the cascade sweep scored native (`gate_ramp_prototype.score`: pad peak in [t_rev - 0.1, t_rev + 3.0] ns
against the campaign's transistor run). Validity rule as in `cross_device_stress_metrics` (Ku > 0.3,
Kd < 0.9, pad peak > 0.3 of the transistor's).

**Result.** 15 of 25 cases valid (hspice ran on 25 of 25). The resampled
tables stay within 3.59 mV of the originals.

| variant | depth | width (ps) | native as generated (%) | native resampled (%) | Ku max | Kd min | lag (ps) | valid |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|
| ex2_base | 50 | 812.5 | -97.1 | +63.6 | 1.26 | -0.26 | +300 | yes |
| ex2_base | 60 | 832.5 | -97.6 | +38.9 | 1.266 | -0.252 | +292 | yes |
| ex2_base | 70 | 857.5 | -97.9 | +21.9 | 1.266 | -0.256 | +239 | yes |
| ex2_base | 80 | 895.0 | -97.5 | +9.4 | 1.265 | -0.27 | +185 | yes |
| ex2_base | 90 | 975.0 | -99.9 | +0.4 | 1.273 | -0.267 | +119 | yes |
| ex2_nomiller | 50 | 808.8 | -97.2 | +64.5 | 1.279 | -0.273 | +300 | yes |
| ex2_nomiller | 60 | 830.0 | -97.7 | +37.9 | 1.281 | -0.279 | +279 | yes |
| ex2_nomiller | 70 | 855.0 | -97.2 | +21.2 | 1.282 | -0.282 | +222 | yes |
| ex2_nomiller | 80 | 895.0 | -97.6 | +8.0 | 1.282 | -0.282 | +166 | yes |
| ex2_nomiller | 90 | 975.0 | -97.9 | -0.1 | 1.282 | -0.273 | +115 | yes |
| ex2_skewp | 50 | 757.0 | -95.3 | -95.4 | 0.18 | 0.064 | -300 | no |
| ex2_skewp | 60 | 773.4 | -96.1 | -96.1 | 0.185 | 0.064 | -300 | no |
| ex2_skewp | 70 | 796.9 | -96.7 | -96.7 | 0.183 | 0.064 | -300 | no |
| ex2_skewp | 80 | 843.8 | -97.2 | -97.2 | 0.184 | 0.063 | -300 | no |
| ex2_skewp | 90 | 937.5 | -96.9 | -96.9 | 0.183 | 0.054 | -300 | no |
| ex2_slowpre | 50 | 1093.8 | -97.7 | +34.8 | 0.905 | -0.054 | +236 | yes |
| ex2_slowpre | 60 | 1137.5 | -97.5 | +34.1 | 1.009 | -0.055 | +300 | yes |
| ex2_slowpre | 70 | 1193.8 | -94.5 | +18.7 | 0.998 | -0.056 | +260 | yes |
| ex2_slowpre | 80 | 1275.0 | -93.4 | +7.5 | 1.017 | -0.06 | +182 | yes |
| ex2_slowpre | 90 | 1425.0 | -75.6 | +0.6 | 1.014 | -0.064 | +95 | yes |
| ex2_weak | 50 | 706.2 | -100.0 | -100.0 | 0.062 | 0.02 | +300 | no |
| ex2_weak | 60 | 721.9 | -100.0 | -100.0 | 0.062 | 0.021 | +300 | no |
| ex2_weak | 70 | 743.8 | -100.0 | -100.0 | 0.062 | 0.506 | +300 | no |
| ex2_weak | 80 | 787.5 | -100.0 | -100.0 | 0.061 | 0.547 | +300 | no |
| ex2_weak | 90 | 875.0 | -100.0 | -100.0 | 0.06 | 0.153 | +300 | no |

**Worst peak error over the five depths, valid cases only** (the number the paper's Table VIII reports):

| variant | worst native peak error (%) |
|---|---:|
| ex2_base | 63.6 |
| ex2_nomiller | 64.5 |
| ex2_skewp | no valid case |
| ex2_slowpre | 34.8 |
| ex2_weak | no valid case |

**Reading.** The fault was the simulator's, not the files' content: the same waveforms on 300 rows
run (where they do; see the validity column). Two finer grids, 500 rows (5.4 ps) and 8.0 ps (335 rows),
left ex2_base dead at every depth on 2026-10-18 while the probe's own 300-row file ran in the same deck,
so the sensitivity is not a plain sampling threshold; the 300-row recipe is the one verified.
run, and the native element then fails on the variants as it does on the shipped ex2 (+71 % at
810 ps), by replaying coefficients of a complete transition against a pulse that interrupts it.
Nothing else in the files was touched, so these numbers are comparable with the seven buffers on
which native ran as generated. Consumed by `scripts/build_stage_law_doc.py` (Table VIII, starred).
