# Transient And Eye Review Plots

Date: 2026-05-13

This folder contains the clean review plots for two comparison cases:

- `normal_prbs_channel/`: accepted PRBS7 + 50 ohm RLGC channel benchmark
- `stressed_edge50_prbs80_channel/`: corrected stressed edge50 PRBS80/channel case

Each subfolder contains the same plot set:

| File | Meaning |
|---|---|
| `01_ngspice_refspice_individual.png` | ngspice transistor-level `io_buf.sp` receiver transient |
| `02_ngspice_pybis_individual.png` | ngspice pybis receiver transient |
| `03_xyce_refspice_individual.png` | Xyce transistor-level `io_buf.sp` receiver transient |
| `04_xyce_pybis_individual.png` | Xyce pybis receiver transient |
| `05_ngspice_refspice_vs_pybis.png` | ngspice refspice vs pybis transient overlay |
| `06_xyce_refspice_vs_pybis.png` | Xyce refspice vs pybis transient overlay |
| `07_all_refspice_pybis_overlay.png` | all four transient traces together |
| `08_eye_ngspice_refspice.png` | ngspice refspice physical eye |
| `09_eye_ngspice_pybis.png` | ngspice pybis physical eye |
| `10_eye_xyce_refspice.png` | Xyce refspice physical eye |
| `11_eye_xyce_pybis.png` | Xyce pybis physical eye |

The eye diagrams use clock/UI-grid folding.  They do not use per-edge alignment
or rise/fall phase compensation.

## Normal PRBS + Channel Case

Configuration:

- Stimulus: PRBS7
- Bit count: 200 bits
- UI: 5 ns
- Stop time: 1000 ns
- Input transition: 200 ps
- Channel: accepted 50 ohm 10-section RLGC channel
- Source files:
  - `ngspice_refspice/tb_refspice_prbs7_new50ohm_batch.raw`
  - `results/prbs_rlgc_clean_2026-05-10/ngspice/tb_clean_prbs_rlgc_ngspice.raw`
  - `xyce_refspice/tb_refspice_prbs7_new50ohm_xyce.cir.csv`
  - `results/prbs_rlgc_clean_2026-05-10/xyce/tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir.csv`

Observation:

The normal-case eyes have highly aligned rising and falling edge families.  The
case is deterministic, relatively gentle, and already covers more than one full
PRBS7 sequence period.  Increasing the bit count alone should mostly increase
plot density rather than fundamentally changing the eye shape.

## Stressed Edge50 PRBS80/Channel Case

Configuration:

- Stimulus: PRBS7-80
- Bit count: 80 bits
- UI: 2 ns
- Stop time: 160 ns
- Input transition: 200 ps
- Channel: 30 cm coarse10 RLGC, loss scale x5
- Source bundle:
  - `results/stressed_edge50_corrected_crossflow_2026-05-12_clean/`

Source files:

- `runs/ui2_len30cm_loss5_coarse10/ngspice_refspice/ui2_len30cm_loss5_coarse10_ngspice_refspice.raw`
- `runs/ui2_len30cm_loss5_coarse10/ngspice_pybis_edge50_corrected/ui2_len30cm_loss5_coarse10_ngspice_pybis_edge50_corrected.raw`
- `runs/ui2_len30cm_loss5_coarse10/xyce_refspice/ui2_len30cm_loss5_coarse10_xyce_refspice.cir.csv`
- `runs/ui2_len30cm_loss5_coarse10/xyce_pybis_edge50/ui2_len30cm_loss5_coarse10_xyce_pybis_edge50.cir.csv`

Observation:

The stressed-case eyes show much more edge spread and history-dependent
structure.  This is mainly caused by the shorter UI, harsher channel, and pybis
edge50 behavior.  It is not simply a consequence of having more bits; this case
actually uses fewer bits than the normal benchmark.

## Tooling

Transient plots were generated with:

- `scripts/transient_plot.py`

Eye diagrams were generated with:

- `scripts/eye_diagram.py`

The eye tool was updated during this work to support:

- exact eye PNG output path via `--eye-out`
- clean eye-only review output via `--no-transitions --no-metrics`
- brighter overlay traces with adaptive opacity
