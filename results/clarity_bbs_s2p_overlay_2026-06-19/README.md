# Clarity_example BBS Overlay

This folder compares the original `Clarity_example.S2P` with the BBS clean/passivity2 General SPICE conversion.

Important detail: the frequency-domain plots use `Clarity_example_Fitted.s2p`, which BroadbandSPICE writes next to `Clarity_example_GSPICE.txt`. That fitted Touchstone is BBS's exported frequency response for the generated SPICE macromodel.

## Inputs

- Original S2P: `results\clarity_bbs_s2p_overlay_2026-06-19\artifacts\Clarity_example_original.S2P`
- BBS fitted response: `results\clarity_bbs_s2p_overlay_2026-06-19\artifacts\Clarity_example_BBS_Fitted.s2p`
- BBS General SPICE model: `results\clarity_bbs_s2p_overlay_2026-06-19\artifacts\Clarity_example_GSPICE.txt`
- ngspice wrapper: `results\clarity_bbs_s2p_overlay_2026-06-19\artifacts\Clarity_example_ngspice_wrapper.sp`

## Plots

- `plots/01_sparameter_magnitude_overlay.png`
- `plots/02_sparameter_phase_overlay.png`
- `plots/03_sparameter_error.png`
- `plots/04_source_check_s21_s12_raw_points.png`: raw-point check for the nearly-straight original through paths
- `plots/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50.png`: transient HSPICE original S-element vs ngspice BBS model
- `plots/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_rx.png`: RX-only transient overlay
- `plots/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_tx.png`: TX-only transient overlay

## Fit Metrics

| Path | Complex RMS | Complex max | Mag dB RMS | Mag dB max | Phase RMS deg |
|---|---:|---:|---:|---:|---:|
| all | 0.00443238 | 0.0190856 | 0.275297 | 1.41079 |  |
| S11 | 0.00115724 | 0.00239614 | 0.400925 | 1.41079 | 2.31382 |
| S21 | 0.00617992 | 0.0190856 | 0.0533592 | 0.172192 | 0.110872 |
| S12 | 0.00615008 | 0.0189698 | 0.0530732 | 0.170997 | 0.111206 |
| S22 | 0.00110903 | 0.00220527 | 0.369795 | 1.28799 | 4.12322 |

## Reading The Result

The BBS frequency fit is quite close in complex RMS, especially on the dominant through paths. The largest visible frequency-domain discrepancies are in magnitude ripple/error on some paths rather than a gross miss.

The original S21/S12 magnitude curves look almost straight because the source Touchstone itself is very smooth and nearly monotonic in dB: S21 moves from about -0.020 dB at 50 MHz to about -0.480 dB at 2 GHz. The source-check plot uses markers to show the raw 40 Touchstone samples directly.

The existing transient audit overlay is included because it answers a different question: whether the generated General SPICE model in ngspice correlates with HSPICE's native S-element transient behavior.
