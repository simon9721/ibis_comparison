# Cisco Backplane S-parameter Investigation

## Current Status

- Inventory found `180` real Cisco Touchstone files under `hspice/sparam/Cisco_Backplane_channel_data`.
- All valid Cisco files are 4-port `.s4p` channels with `3201` points from `10 MHz` to `50 GHz`.
- The current scikit-rf direct vector-fit export is not good enough for the representative channel `Ch10_35_5F3N_t.s4p`.
- This is not a case of the new metric being too strict. A forced ngspice transient on the rejected `vector_16r16c` model visibly disagrees with native HSPICE.
- A reduced ngspice model with explicit propagation delay, parallel RC residual branches, and a small zero-DC tail branch now matches native HSPICE closely on the tested through channels.

## Representative Channel

Channel: `hspice/sparam/Cisco_Backplane_channel_data/5F3N/Ch10_35_5F3N_t.s4p`

Dominant path is the 4-port through path `S31`/`S24`, not `S21`. The measured through delay is about `14 ns`.

Native HSPICE confirms the long delay:

- Native audit output: `results/sparam_cisco_native_hspice_2026-06-08/Ch10_35_5F3N_t_long/native_hspice_audit.csv`
- HSPICE `.tr0` files are in `results/sparam_cisco_native_hspice_2026-06-08/Ch10_35_5F3N_t_long/`
- HSPICE `.lis` reports `delay estimation at S[3][1]: 1.39221e-08 sec`
- HSPICE `.lis` reports `DELAYHANDLE activated` and writes/reads `ch_model.yrf`

Native HSPICE 50% output delays:

| case | rx threshold (V) | rx rise (ns) | rx fall (ns) | rise delay (ps) | fall delay (ps) |
|---|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | 0.3170 | 15.0764 | 23.1111 | 14072.9 | 14107.5 |
| `audit_amp1p5_edge50_r50` | 0.3197 | 15.1044 | 23.1332 | 14079.0 | 14108.7 |
| `audit_amp1p5_edge500_r50` | 0.3252 | 15.3758 | 23.3897 | 14114.8 | 14125.2 |

The receive threshold is based on the actual receive waveform swing, not `1.5 V / 2`, because this lossy channel only reaches about `0.67 V`.

## Direct Vector-fit Result

High-order direct scikit-rf vector fitting did not pass the HSPICE-independent gates:

| candidate | complex RMS | max mag error above -40 dB | group delay RMS (ps) | dense max singular value | passive |
|---|---:|---:|---:|---:|---:|
| `vector_8r8c` | 0.1130 | 59.70 dB | 13683.7 | 3.328 | false |
| `vector_12r12c` | 0.1075 | 76.30 dB | 13562.9 | 2.019 | false |
| `vector_16r16c` | 0.1049 | 72.69 dB | 13538.7 | 1.489 | false |

That is already a hard fail: non-passive fit, high dense singular value, large magnitude error, and group-delay error on the order of the channel delay itself.

## Forced ngspice Correlation

I forced ngspice to run the rejected `vector_16r16c` exported SPICE model anyway, then compared it against native HSPICE:

- Comparison table: `results/sparam_cisco_ngspice_forced_2026-06-08/Ch10_35_5F3N_t_vector16_compare_v2/comparison.csv`
- Comparison plots: `results/sparam_cisco_ngspice_forced_2026-06-08/Ch10_35_5F3N_t_vector16_compare_v2/`

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | FAIL | 0.1184 | 0.3417 | 468.1 | -202.0 | 0.8958 |
| `audit_amp1p5_edge50_r50` | FAIL | 0.1181 | 0.3292 | 474.7 | -213.3 | 0.8928 |
| `audit_amp1p5_edge500_r50` | FAIL | 0.1152 | 0.3014 | 462.8 | -276.9 | 0.8651 |

The ngspice model is not merely a little noisy at the edges. In the overlay plots, the ngspice converted model back-drives the input port negative while HSPICE sees the expected launched pulse. At the output, ngspice is lower amplitude, has pre-response/ringing before the main edge, and shifts the receive edge by hundreds of ps.

## Delay-parallel ngspice Result

I then built a reduced ngspice macromodel with:

- explicit 50 ohm delay line
- 4 parallel RC residual branches
- 50 ohm output resistance into the existing 50 ohm load

This is a waveform-correlation prototype, not yet a general-purpose passive multiport S-parameter replacement. For the current 50 ohm source/load audit bench, it matches HSPICE well.

- Model/report: `results/sparam_cisco_delay_parallel_2026-06-08/Ch10_35_5F3N_t/README.md`
- Corrected ngspice raw/logs: `results/sparam_cisco_delay_parallel_2026-06-08/Ch10_35_5F3N_t/ngspice_corrected/`
- Corrected comparison plots: `results/sparam_cisco_delay_parallel_2026-06-08/Ch10_35_5F3N_t/comparison_corrected/`

Fitted model parameters:

- explicit delay: `13.9203 ns`
- DC gain to loaded output: `0.89348`
- branch taus: `0.112563 ns`, `0.280437 ns`, `0.664271 ns`, `1.7238 ns`
- branch gains: `0.30177`, `0.405099`, `0.0142327`, `0.172379`

Corrected ngspice vs native HSPICE:

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | PASS | 0.003632 | 0.01020 | 5.80 | 3.65 | 0.02518 |
| `audit_amp1p5_edge50_r50` | PASS | 0.003995 | 0.02184 | 3.64 | 2.01 | 0.02473 |
| `audit_amp1p5_edge500_r50` | PASS | 0.006172 | 0.03387 | 12.02 | 16.56 | 0.02320 |

## Second-channel Check

I repeated the delay-parallel method on another true through channel:

Channel: `hspice/sparam/Cisco_Backplane_channel_data/5F3N/Ch9_33_5F3N_t.s4p`

- HSPICE receive delay: about `12.59-12.60 ns`
- Initial fitted ngspice delay: `12.4564 ns`
- Accepted trim: `-10 ps`, effective delay `12.4464 ns`
- Model/report: `results/sparam_cisco_delay_parallel_2026-06-08/Ch9_33_5F3N_t/README.md`
- Accepted comparison plots: `results/sparam_cisco_delay_parallel_2026-06-08/Ch9_33_5F3N_t/trim_sweep/trim_m10ps/comparison/`

Accepted trimmed ngspice vs native HSPICE:

| case | class | RX active RMSE (V) | RX active maxabs (V) | RX rise delta (ps) | RX fall delta (ps) | TX active RMSE (V) |
|---|---:|---:|---:|---:|---:|---:|
| `audit_amp1p5_edge5_r50` | PASS | 0.007983 | 0.04842 | -19.12 | 0.90 | 0.02944 |
| `audit_amp1p5_edge50_r50` | PASS | 0.006883 | 0.02876 | -6.74 | -5.47 | 0.02937 |
| `audit_amp1p5_edge500_r50` | PASS | 0.006463 | 0.03035 | 21.79 | 13.60 | 0.02761 |

## Optimized Batch Check

I then automated the flow across all strong `S31` Cisco through channels selected by `dominant_path=S31` and `dominant_peak_mag_db >= -3 dB`:

- batch output: `results/sparam_cisco_delay_parallel_batch_2026-06-08/`
- summary CSV: `results/sparam_cisco_delay_parallel_batch_2026-06-08/batch_summary.csv`
- per-case overlays: `results/sparam_cisco_delay_parallel_batch_2026-06-08/<channel>/trim_sweep/<accepted_trim>/comparison/`

The optimized model family uses:

- explicit 50 ohm propagation delay
- 4 parallel RC residual branches for the main through response
- 1 zero-DC tail branch, implemented as a fast-minus-slow RC pair, to match small post-edge droop/settling without changing DC gain
- automatic delay trim sweep, currently `-30 ps` to `+15 ps`

Current strong-`S31` batch result: `16/16 PASS`, with `48/48` accepted HSPICE-vs-ngspice transient comparisons passing across the three edge-rate audit cases.

The 16 rows represent 8 unique waveforms: each selected `5F3N`/`8F` Touchstone pair has identical SHA-256 content, so the paired correlation metrics are identical.

| channel | accepted trim (ps) | max RX active RMSE (V) | max RX active maxabs (V) | max rise delta (ps) | max fall delta (ps) |
|---|---:|---:|---:|---:|---:|
| `Ch1_10_5F3N_t` | -5 | 0.01281 | 0.04538 | 5.54 | 4.34 |
| `Ch3_17_5F3N_t` | 0 | 0.00652 | 0.02655 | 5.12 | 9.83 |
| `Ch4_20_5F3N_t` | 0 | 0.00948 | 0.04244 | 18.60 | 13.81 |
| `Ch5_22_5F3N_t` | -5 | 0.00802 | 0.02719 | 14.10 | 19.42 |
| `Ch7_28_5F3N_t` | -5 | 0.01253 | 0.02795 | 11.95 | 13.90 |
| `Ch8_30_5F3N_t` | -5 | 0.00744 | 0.05917 | 13.37 | 15.38 |
| `Ch9_33_5F3N_t` | -10 | 0.00770 | 0.05264 | 20.25 | 12.60 |
| `Ch10_35_5F3N_t` | -10 | 0.00802 | 0.03262 | 4.63 | 11.42 |

The matching `8F` rows pass with the same metrics because their Touchstone files are byte-identical to the listed `5F3N` rows.

The most informative case was `Ch3_17_5F3N_t`. The older RC-only model already had small 50% timing error, but failed classification because RX active RMSE was about `22.8 mV`. The overlay showed the issue was not delay: ngspice missed HSPICE's small post-fall negative tail and had the wrong settled shape. Adding one zero-DC tail branch reduced max RX active RMSE to about `6.5 mV` and made all three edge-rate cases pass.

## S11/TX Reflection Prototype

The strong `S31` model intentionally focused on receive waveform correlation, so the ngspice TX/input waveform was smoother than HSPICE. I added a prototype S11-like correction:

- starts from the accepted delay-trimmed `S31` model
- inserts a series controlled-voltage correction between external `p1` and internal matched input `pin`
- drives that correction with fixed RC reflection bases plus one zero-DC tail basis
- scales the correction strength to avoid perturbing the already-good RX fit too much

Full-strength correction improved TX but over-perturbed RX on two channels. I added an automatic strength sweep that tries `0`, `0.25`, `0.5`, `0.75`, and `1.0`, then selects the strongest S11 correction that still passes all RX/HSPICE correlation gates.

- output: `results/sparam_cisco_s11_strength_sweep_2026-06-09/`
- selected summary: `results/sparam_cisco_s11_strength_sweep_2026-06-09/s11_selected_summary.csv`
- full sweep table: `results/sparam_cisco_s11_strength_sweep_2026-06-09/s11_strength_sweep.csv`
- result: `8/8` unique strong-`S31` channels PASS
- selected strengths: `1.0` for six channels, `0.5` for `Ch1_10_5F3N_t` and `Ch8_30_5F3N_t`
- average max TX active RMSE improved from `29.5 mV` to `21.0 mV`, about `29%`
- worst S11-corrected RX active RMSE: `17.3 mV`, still below the `20 mV` pass gate
- worst S11-corrected RX timing deltas: `21.3 ps` rise and `22.1 ps` fall, still below the `25 ps` pass gate

| channel | selected strength | baseline max TX RMSE (V) | selected max TX RMSE (V) | selected max RX RMSE (V) | selected rise delta (ps) | selected fall delta (ps) |
|---|---:|---:|---:|---:|---:|---:|
| `Ch1_10_5F3N_t` | 0.5 | 0.03909 | 0.03178 | 0.01728 | 6.09 | 8.39 |
| `Ch3_17_5F3N_t` | 1.0 | 0.03840 | 0.02420 | 0.01427 | 4.05 | 11.90 |
| `Ch4_20_5F3N_t` | 1.0 | 0.02465 | 0.02193 | 0.01227 | 18.25 | 11.41 |
| `Ch5_22_5F3N_t` | 1.0 | 0.02388 | 0.01486 | 0.01296 | 12.40 | 10.13 |
| `Ch7_28_5F3N_t` | 1.0 | 0.02391 | 0.01394 | 0.01122 | 11.16 | 17.06 |
| `Ch8_30_5F3N_t` | 0.5 | 0.03141 | 0.02515 | 0.01115 | 12.94 | 22.05 |
| `Ch9_33_5F3N_t` | 1.0 | 0.02944 | 0.01918 | 0.01672 | 21.27 | 18.45 |
| `Ch10_35_5F3N_t` | 1.0 | 0.02518 | 0.01664 | 0.01490 | 6.60 | 21.39 |

This is still a bench-scoped S11 correction, not a fully passive multiport S-matrix model. But it confirms that adding an input-reflection layer can improve the TX side while preserving the RX pass results when applied conservatively.

For true `.s2p` files, the same architecture applies more directly: the current `S31` layer becomes the `S21` forward path, and the S11 correction is exactly the input reflection term. The remaining full-2-port work is to add `S12` reverse behavior and `S22` output reflection so the `.s2p` model works under arbitrary terminations, not only this 50 ohm transient bench.

## Delay-aware Prototype

I also tested delay-removal prototypes. Estimated dominant delay was `13.9841 ns`. Removing delay helps the RMS somewhat, but does not fix the model:

| residual mode | order | complex RMS | max mag error above -40 dB | group delay RMS (ps) | residual passive |
|---|---:|---:|---:|---:|---:|
| `none` | 16 | 0.1049 | 72.69 dB | 13538.7 | false |
| `through_only` | 16 | 0.0843 | 104.91 dB | 9405.2 | false |
| `per_entry` | 16 | 0.0872 | 56.90 dB | 9414.3 | true |

Delay is part of the problem, but not the whole problem. The fitted model still misses the through response shape, ripple, and notches badly enough that transient behavior is not reliable.

## Tooling Updates

- `scripts/run_sparam_conversion_quality_study.py`
  - added configurable `--smoke-stop-ns` and `--audit-stop-ns`
  - added adaptive low/active/50% waveform thresholds
  - added active-window waveform error metrics
- `scripts/run_native_hspice_sparam_audit.py`
  - added adaptive waveform thresholds
  - added `--reuse-existing` to parse existing `.tr0` files without rerunning HSPICE
  - improved `.lis` passive detection
- `scripts/compare_sparam_transient_audits.py`
  - new reusable HSPICE-vs-ngspice transient comparison script
  - writes `comparison.csv`, README summary, and one overlay per audit case
- `scripts/run_delay_aware_parallel_sparam_model.py`
  - fits and emits the explicit-delay plus parallel-RC ngspice prototype
  - default optimized model now includes one zero-DC tail branch; use `--tail-branches 0` for the older RC-only behavior
  - generates ngspice decks/raw/logs and HSPICE correlation overlays
- `scripts/run_delay_parallel_batch.py`
  - batch-runs native HSPICE, optimized ngspice model generation, delay trim sweep, and HSPICE correlation summaries
  - supports `--resume`, `--force`, selected channel IDs, and configurable tail-branch count
- `scripts/add_s11_tx_correction.py`
  - augments an accepted delay-parallel model with a bench-scoped S11-like TX correction
  - supports correction strength scaling
- `scripts/batch_add_s11_tx_correction.py`
  - sweeps S11 correction strength across accepted batch channels and selects the strongest passing correction per channel
  - writes `s11_strength_sweep.csv`, `s11_selected_summary.csv`, and a README report

## Conclusion

For Cisco-style long, measured 4-port channels, direct scikit-rf vector fitting plus SPICE export is not sufficient. HSPICE succeeds because it detects/extracts propagation delay and fits the remaining response. Matching that architecture in ngspice is the right direction.

The reduced delay-parallel ngspice prototype proves this direction works for the 50 ohm transient bench: the two earlier pilot channels and the four-channel optimized batch now pass all three HSPICE correlation edge cases. The important refinement is that a pure RC residual can miss small post-edge settling tails; the zero-DC tail branch closes that gap without disturbing the main delay fit. The next step is to scale this optimized flow to more channel groups and then generalize it from a bench-specific waveform model into a reusable, passive, multiport delay-aware channel model.
