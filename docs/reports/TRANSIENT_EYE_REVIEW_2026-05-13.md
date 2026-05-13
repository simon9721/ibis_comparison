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

Each folder now contains 14 PNGs:

- 4 individual transient plots
- 1 ngspice refspice-vs-pybis transient overlay
- 1 Xyce refspice-vs-pybis transient overlay
- 1 all-four transient overlay
- 4 individual physical eye diagrams
- 2 individual pybis `Ku/Kd` diagnostic plots, one for ngspice and one for Xyce
- 1 ngspice-vs-Xyce pybis `Ku/Kd` overlay

The transient plot filenames are numbered `01` through `07`; the eye diagrams
are numbered `08` through `11`; the `Ku/Kd` diagnostics are numbered `12`
through `14`.

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

`Ku/Kd` diagnostic:

The accepted normal ngspice RAW did not contain internal pybis nodes, so
`scripts/plot_review_kukd.py` regenerated a short `0-75 ns` ngspice pybis
diagnostic run with `V(xdrv.ku)`, `V(xdrv.kd)`, and `V(xdrv.nx)` saved.  The
zoom window is `50-70 ns`.  Xyce already had `V(XDRV:Ku)` and `V(XDRV:Kd)` in
the existing CSV, so it was plotted over the same review window.

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

`Ku/Kd` diagnostic:

The stressed pybis receiver spike is marked at about `56.69 ns`.  The new
diagnostic plots zoom over `55.5-58.8 ns` so the `Ku/Kd` coefficient behavior
can be inspected directly at the spike timing.  The ngspice pybis diagnostic was
rerun with the same corrected edge50/tailflat4p2 model and circuit setup, only
adding internal `Ku/Kd/NX` saved nodes.

This is consistent with the pybis behavior study documented in:

- `docs/reports/PYBIS_TWO_BEHAVIORS_2026-05-13.md`

## Tooling Changes

Reusable transient utility:

- `scripts/transient_plot.py`
- documented in `docs/TRANSIENT_PLOT_TOOL.md`

Pybis coefficient diagnostic utility:

- `scripts/plot_review_kukd.py`
- regenerates missing ngspice internal-node RAWs for review
- writes `12_ngspice_pybis_kukd.png`, `13_xyce_pybis_kukd.png`,
  `14_ngspice_xyce_pybis_kukd_overlay.png`, and `kukd_metrics.csv` into each
  review folder

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
