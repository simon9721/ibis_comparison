# Transient And Eye Review Summary

Date: 2026-05-13

Workspace: `C:\Users\simom\Desktop\IBIS_Comparison`

Review plot bundle:

- `results/transient_review_plots_2026-05-13/`

## Purpose

This work created a consistent review set for comparing refspice and pybis
results across ngspice and Xyce.  The goal was to avoid one-off plot scripts
and make the normal and stressed cases easy to inspect side by side.

## Generated Plot Sets

Two folders were created:

- `results/transient_review_plots_2026-05-13/normal_prbs_channel/`
- `results/transient_review_plots_2026-05-13/stressed_edge50_prbs80_channel/`

Each folder contains 11 PNGs:

- 4 individual transient plots
- 1 ngspice refspice-vs-pybis transient overlay
- 1 Xyce refspice-vs-pybis transient overlay
- 1 all-four transient overlay
- 4 individual physical eye diagrams

The transient plot filenames are numbered `01` through `07`; the eye diagrams
are numbered `08` through `11`.

## Normal Case

Configuration:

| Item | Value |
|---|---:|
| Stimulus | PRBS7 |
| Bit count | 200 bits |
| UI | 5 ns |
| Stop time | 1000 ns |
| Input transition | 200 ps |
| Channel | accepted 50 ohm 10-section RLGC |

The normal case already covers more than one full PRBS7 period, because PRBS7
repeats every 127 bits.  After skipping the first 10 UI for eye construction,
about 190 UI remain.

Observation:

The normal-case eyes have very aligned rising-edge and falling-edge families.
This is expected.  The case is deterministic, relatively gentle, and not
injecting random jitter or noise.  Increasing only the bit count should mostly
make the overlay denser, not fundamentally change the eye shape.

## Stressed Case

Configuration:

| Item | Value |
|---|---:|
| Stimulus | PRBS7-80 |
| Bit count | 80 bits |
| UI | 2 ns |
| Stop time | 160 ns |
| Input transition | 200 ps |
| Channel | 30 cm coarse10 RLGC, loss scale x5 |
| Pybis model | corrected edge50/tailflat4p2 flow |

Observation:

The stressed case has fewer bits than the normal case, but it produces a much
more spread-out eye.  The spread is caused by deterministic ISI and
history-dependent channel/model behavior, not by a larger PRBS population.

This is consistent with the pybis behavior study documented in:

- `docs/reports/PYBIS_TWO_BEHAVIORS_2026-05-13.md`

## Tooling Changes

Reusable transient utility:

- `scripts/transient_plot.py`
- documented in `docs/TRANSIENT_PLOT_TOOL.md`

Eye tool updates:

- `scripts/eye_diagram.py`
- added `--eye-out` for exact output filenames
- added `--no-transitions` and `--no-metrics` for clean review folders
- made overlay eye diagrams brighter and clearer using adaptive opacity,
  thicker cyan traces, brighter threshold markers, and higher DPI

The eye diagrams remain physically clock/UI-grid folded.  No per-edge alignment
or rise/fall phase compensation was added.

## Interpretation

The normal benchmark is useful as a stable accepted comparison and as a
sanity-check case for ngspice/Xyce agreement.  The stressed edge50 case is more
useful for exposing deterministic history sensitivity in pybis and for seeing
edge-family spread in eye diagrams.

These two cases answer different questions:

- Normal case: "Do the accepted open-source flows run and agree in the standard
  PRBS/RLGC setup?"
- Stressed case: "What model/channel-history behavior appears when the setup is
  pushed harder?"
