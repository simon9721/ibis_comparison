# Three-Buffer Direct-Load PRBS7 Phase 1

This study replaces isolated pulses with a repeated PRBS7 stream while keeping the electrical bench deliberately simple.

## Fixed Setup

- Fast-edge IBIS files only.
- Deterministic PRBS7: `x^7 + x^6 + 1`, 127 bits.
- HSPICE: two complete periods.
- ngspice: first 31 PRBS7 bits plus recovery; all eight three-bit histories are present.
- Longer ngspice failures are retained in `solver_attempts.csv`.
- Runtime rise/fall: 50 ps.
- UI sweep: 2 ns, 1 ns, 500 ps, 250 ps.
- Direct load: `50 ohm || 2 pF`.
- Flows: HSPICE transistor, HSPICE native IBIS, ngspice gate-state, ngspice hybrid.
- No transmission line in Phase 1.

## Start Here

- `plots/00_testbench_and_stimulus.png`: exact Phase 1 concept and PRBS stimulus.
- `plots/01_eye_height_vs_ui.png`: eye opening across buffers and UI.
- `plots/02_pad_rmse_vs_ui.png`: absolute-time pad correlation.
- `plots/03_coefficient_rmse_vs_ui.png`: Ku/Kd agreement with native IBIS.
- `plots/04_history_spread_vs_ui.png`: pattern-history sensitivity.
- `plots/05_hybrid_activation_vs_ui.png`: when and how often the hybrid actually used gate state.
- `plots/10_<device>_sequence_overview.png`: 32-UI excerpts for each UI.
- `plots/cases/<device>/<case>/02_pad_eyes.png`: readable two-UI pad eyes on common axes.
- `plots/cases/<device>/<case>/03_coefficient_eyes.png`: two-UI Ku/Kd eyes.
- `plots/cases/<device>/<case>/06_hybrid_activation_events.png`: event-by-event hybrid mode trace.

## Reproduce Or Resume

```powershell
py -3.14 scripts/run_three_buffer_prbs_phase1.py `
  --study-dir results/three_buffer_prbs_phase1_2026-07-31 `
  --solver-profile gear_relaxed `
  --timeout-s 900
```

The runner reuses completed artifacts. Add `--retry-failures` only when intentionally retrying numeric failures. Rebuild plots without simulation using:

```powershell
py -3.14 scripts/run_three_buffer_prbs_phase1.py `
  --study-dir results/three_buffer_prbs_phase1_2026-07-31 `
  --report-only
```

## Numeric Data

- `waveforms/<device>/<case>.csv`: full aligned numeric waveform data.
- `metrics.csv`: pad and coefficient correlation.
- `eye_metrics.csv`: eye height, width, delay, and sample BER.
- `pattern_metrics.csv`: all three-bit history-class samples.
- `history_metrics.csv`: compact history-spread metrics.
- `worst_bit_metrics.csv`: worst candidate bit per case.
- `hybrid_event_summary.csv`: activation count and active time for every hybrid run.
- `hybrid_events.csv`: start/stop, direction, state, and error values for each activation event.
- `run_manifest.csv`: raw/log paths and resume/cache provenance.
- `prbs7_bits.csv`: exact 127-bit sequence.

## Run Status

- Completed simulator flows: `45`.
- Completed device/UI combinations represented: `12`.
- Failed or incomplete flows: `3`.

## Measured Findings

### Reference behavior

- `inv_chain` is the clean reference case. At 250 ps UI, the transistor/native-IBIS eye heights are `1.419 / 1.421 V`; both references remain open at every UI.
- `ex2` has a clear physical bandwidth boundary. The transistor/native-IBIS eyes are `1.416 / 1.421 V` at 1 ns, but `-0.034 / -0.026 V` at 500 ps.
- `io_buf` is already marginal at 1 ns. Its transistor/native-IBIS eyes are `1.172 / 0.890 V` at 2 ns and `0.085 / -0.018 V` at 1 ns.

### Candidate behavior

- For `inv_chain`, the hybrid preserves a `1.422 V` eye at 500 ps, but its gate-state active fraction is `0.000`. That is legacy-path preservation, not proof that the reversal correction improved the stream.
- For `ex2` at 500 ps, both HSPICE references are closed while the hybrid reports a `0.494 V` eye. This is a false-open result; the hybrid cannot be trusted at that stress point.
- For `io_buf` at 1 ns, the hybrid reports a `0.284 V` eye while both references are marginal or closed. Its Ku/Kd also leave the accepted coefficient range.
- Gate state was actually triggered in completed runs for `io_buf` at 1 ns, 500 ps, and 250 ps; for `ex2` at 500 ps and 250 ps; and for `inv_chain` only at 250 ps.
- It was not triggered for completed `inv_chain` runs at 1 ns or 500 ps, or `ex2` runs at 2 ns or 1 ns. Any hybrid advantage there is legacy-path preservation, not gate-state improvement.
- Across the completed cases, neither the full gate-state nor hybrid candidate is generally trustworthy. The result depends strongly on buffer structure and UI.

### How to read the plots

- Eye height is optimized independently for each flow at that flow's best sampling phase. It measures usable opening, not absolute timing agreement.
- Each eye panel now spans two UIs around the best sample. Colored dots at time zero are the actual bit samples; the dotted horizontal line is that flow's decision threshold.
- Pad RMSE uses the common absolute time axis. A candidate can have an open eye and still have poor waveform or timing correlation.
- A candidate eye that stays open after both HSPICE references close is a false-open warning, not an improvement.
- These are direct-load results. The observed closure and history dependence cannot be blamed on transmission-line reflection or channel ISI.

## Numerical Scope

- Selected ngspice solver profile(s): `gear_relaxed`.
- The final matrix uses a bounded 31-bit window because longer gate-state PRBS runs reproducibly stopped making progress.
- The bounded window still contains all eight three-bit histories, so it is sufficient for this Phase 1 history comparison.
- The long-stream stalls and three final numeric failures mean the experimental state models are not yet production-scalable.
- `solver_attempts.csv` retains the strict-Gear, relaxed-Gear, and relaxed-Trap attempts; failed work was not discarded.

## Phase 1 Conclusion

The direct-load PRBS study is complete enough to answer the first question: repeated-data behavior is not universally fixed by the current gate-state or hybrid model. `inv_chain` remains the strongest case, while `io_buf` exposes coefficient-range, waveform, and solver-sensitivity problems, and `ex2` exposes a clear false-open hybrid eye at 500 ps.

The next experiment should not add a transmission line yet. First, make the ngspice state implementation numerically bounded for a full 127-bit period and add an automatic false-open gate that rejects any candidate whose eye remains open after both HSPICE references close. Once that passes, Phase 2 can add a matched line to separate driver-history error from channel ISI.

## Failed/Incomplete Flows

- `io_buf / prbs7_ui_2ns_edge_50ps / ngspice_hybrid`: `NUMERIC_FAIL`
- `inv_chain / prbs7_ui_2ns_edge_50ps / ngspice_hybrid`: `NUMERIC_FAIL`
- `ex2 / prbs7_ui_2ns_edge_50ps / ngspice_gate_state`: `NUMERIC_FAIL`
