# Three-Buffer True Output-Level Mid-Transition Reversal

This index collects the corrected stress study for `io_buf`, `inv_chain`, and `ex2`.
The defining event is a reversal of the loaded pad waveform itself, not merely a new
input edge or a partially changed `Ku/Kd` state.

## Qualification Rule

A case is counted as a true output-level reversal only when all of the following are
observed in the HSPICE native-IBIS waveform:

1. The input command reverses before the pending output transition is complete.
2. The pad reaches between 5% and 95% of its loaded full-swing reference.
3. The pad subsequently reaches a local turning point and moves back toward its
   original level.
4. The pending output transition never reaches the original full-swing endpoint.

The HSPICE transistor waveform is checked separately because it is a pad-level
reference and has no `Ku/Kd` observability.

## Selected Isolated Cases

All cases use the fast-edge IBIS profile, 50 ps input rise/fall, and a direct
`50 ohm || 2 pF` load.

| Buffer | Short-high pulse | Equivalent rate | Native excursion | Transistor excursion | Pad-match V2 excursion |
|---|---:|---:|---:|---:|---:|
| `io_buf` | 1750 ps | 0.571 Gb/s | 47.4% | 65.2% | 59.2% |
| `inv_chain` | 100 ps | 10.000 Gb/s | 90.9% | 26.1% | 100.1% |
| `ex2` | 750 ps | 1.333 Gb/s | 81.0% | 20.6% | 93.2% |

The `inv_chain` result is the important correction to the earlier study: the old
275 ps stimulus was an internal-state interruption, but its delayed pad response
still completed a full swing. The 100 ps stimulus is a genuine pad-level reversal.

## What The Results Say

- `io_buf`: pad-match V2 improves the partial output amplitude, but its `Kd`
  recovery is too early. This is not a coefficient-correct pass.
- `inv_chain`: pad-match V2 incorrectly produces a full output swing and is both
  temporally and coefficient-wise wrong.
- `ex2`: pad-match V2 reaches 93.2% versus the native 81.0% partial excursion and
  remains substantially wrong in pad and coefficient correlation.
- Across the stressed PRBS7 runs, pad, `Ku`, and `Kd` improve together in `0/3`
  buffers. The algorithm also produces false activations outside true output
  reversal events, especially for `inv_chain` and `ex2`.

## Evidence Packages

- Screening and selected pulse widths:
  `../three_buffer_output_level_reversal_screen_2026-08-11/`
- Isolated-event overlays and numeric metrics:
  `../three_buffer_pad_matched_replay_v2_true_output_2026-08-11/evidence/`
- Sequence-level PRBS overlays, event audit, eye plots, and waveform CSVs:
  `../three_buffer_prbs_pad_matched_v2_true_output_2026-08-11/`

Start with the isolated contact sheet:

`../three_buffer_pad_matched_replay_v2_true_output_2026-08-11/evidence/00_true_output_reversal_contact_sheet.png`

Then inspect the PRBS contact sheet:

`../three_buffer_prbs_pad_matched_v2_true_output_2026-08-11/00_three_buffer_prbs_contact_sheet.png`

## Bottom Line

The corrected dataset now tests the phenomenon of interest: the loaded output is
already moving and is forced to turn around before settling. Pad-matched replay V2
does not generalize across the three buffers under this stricter test, so it remains
an experimental diagnostic rather than a replacement for legacy pybis.
