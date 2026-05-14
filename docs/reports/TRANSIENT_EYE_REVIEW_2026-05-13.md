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

The common review set contains 14 PNGs in each folder:

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

Additional source-side diagnostics were added after the common set:

- normal case: `15_normal_source_edge_response_map.png`
- stressed case: `15_stressed_spike_leadin_kukd_history.png` through
  `19_stressed_source_edge_response_map.png`

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
`scripts/plot_review_kukd.py` regenerated a short `0-80 ns` ngspice pybis
diagnostic run with `V(xdrv.ku)`, `V(xdrv.kd)`, and `V(xdrv.nx)` saved.  The
plotted review window is `0-75 ns` and the zoom window is `50-70 ns`.  Xyce
already had `V(XDRV:Ku)` and `V(XDRV:Kd)` in the existing CSV, so it was
plotted over the same review window.

One important setup detail: the accepted normal ngspice RAW was generated before
the later `ngspice_pybis/driver_OutputInput_Typical.sub` edits.  To make the
normal diagnostic match the accepted normal transient, the diagnostic rerun uses
the preserved pre-edit snapshot:
`results/ngspice_kukd_ab_context38_2026-05-11/driver_OutputInput_Typical_pre_kukd_3e0bf44.sub`.

The normal source-edge map is:

- `results/transient_review_plots_2026-05-13/normal_prbs_channel/15_normal_source_edge_response_map.png`
- `results/transient_review_plots_2026-05-13/normal_prbs_channel/normal_source_edge_response_map_metrics.csv`

It shows the expected calm behavior:

- E1 input rise: `35.10 ns`; sustained `Ku` at `38.764 ns` in Xyce and
  `38.781 ns` in ngspice
- E2 input fall: `65.10 ns`; sustained `Kd` at `68.020 ns` in Xyce and
  `68.030 ns` in ngspice
- E3 input rise: `70.10 ns`; sustained `Ku` at `73.779 ns` in Xyce and
  `73.781 ns` in ngspice

The Xyce normal trace has a one-sample `Ku` blip at the first input threshold
crossing.  The metric intentionally uses a sustained crossing so this blip is
not mistaken for the real source response.

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
- writes `15_stressed_spike_leadin_kukd_history.png` and
  `spike_leadin_metrics.csv` for the stressed-case spike lead-in
- writes `16_stressed_spike_chain_kukd_top_transient_bottom.png` as a simpler
  cause/effect view with `Ku/Kd` above the transient waveforms
- writes `17_stressed_pybis_tx_vs_kukd_no_channel.png` as the minimal
  source-side view, using `tx_out` before the RLGC channel so the channel delay
  is removed from the causal view
- writes `18_stressed_pybis_tx_kukd_source_context.png` to show the neighboring
  source-side events before and after the problematic falling-edge pulse
- writes `19_stressed_source_edge_response_map.png` and
  `source_edge_response_map_metrics.csv` to explicitly map input edges to
  pybis coefficient transitions and pybis/refspice source responses
- writes `15_normal_source_edge_response_map.png` and
  `normal_source_edge_response_map_metrics.csv` for the normal-case source-side
  input/`Ku/Kd`/`tx_out` comparison

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

The focused `Ku/Kd` lead-in plot shows that the pybis receiver spike around
`56.69 ns` is not a same-time `Ku` turn-on.  At the spike peak, `Ku` is still
near zero and `Kd` is near one in both ngspice and Xyce.  The spike is instead
the delayed channel response to a large pybis transmitter-side pad launch near
`54.24 ns`, immediately after the prior falling input edge.  The pybis pad peak
is about `2.18-2.19 V`, while the matching refspice pad peak is only about
`1.52-1.53 V`; the receiver spike arrives roughly `2.45 ns` later.

These two cases answer different questions:

- Normal case: "Do the accepted open-source flows run and agree in the standard
  PRBS/RLGC setup?"
- Stressed case: "What model/channel-history behavior appears when the setup is
  pushed harder?"
