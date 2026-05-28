## Refspice vs pybis Correlation Root Cause

Date: 2026-05-27

### Question

We have two clean refspice-vs-pybis comparison cases:

- `io_buf`
- `inv_chain`

`inv_chain` lines up tightly, but `io_buf` shows a large pybis-vs-refspice delay. The goal was to understand why this inconsistency exists.

### Main Finding

The large `io_buf` mismatch is not caused by the pybis runtime circuit, ngspice, Xyce, or the T-line edge detector. The converted pybis model is replaying the `io_buf.ibs` waveform table very closely.

The inconsistency is between:

- the `io_buf.ibs` VT waveform timing, and
- the `io_buf.sp` transistor reference bench we are using.

The best current explanation is that `io_buf.ibs` was characterized with a much slower input stimulus, or with a waveform time origin closer to the start of the characterization input edge. Our clean transistor reference bench uses a nearly ideal `5 ps` input edge. That makes the transistor reference respond much earlier than the IBIS VT waveform table.

### Evidence 1: pybis Follows IBIS in Both Cases

New analysis script:

- `scripts/analyze_refspice_pybis_correlation.py`

New output folder:

- `results/refspice_pybis_correlation_study_2026-05-27/`

Important generated files:

- `ibis_refspice_pybis_crossing_timing.csv`
- `ibis_refspice_pybis_shape_rmse.csv`
- `io_buf_ibis_pybis_refspice_edge_overlay.png`
- `inv_chain_ibis_pybis_refspice_edge_overlay.png`

At the clean RSF pad, crossing timing relative to the IBIS VT table is:

| Case | Edge | pybis - IBIS | refspice - IBIS | pybis - refspice |
|---|---:|---:|---:|---:|
| `io_buf` | rising | `+6.6` to `+9.8 ps` | `-572.9` to `-610.9 ps` | `+581.1` to `+617.5 ps` |
| `io_buf` | falling | `+5.8` to `+7.1 ps` | `-637.5` to `-732.7 ps` | `+643.9` to `+738.5 ps` |
| `inv_chain` | rising | `+8.2` to `+9.3 ps` | `-1.9` to `-0.6 ps` | `+9.5` to `+11.1 ps` |
| `inv_chain` | falling | `+6.7` to `+7.2 ps` | `+3.4` to `+4.5 ps` | `+2.7` to `+3.3 ps` |

Interpretation:

- pybis is within about `5-10 ps` of the IBIS waveform tables in both cases.
- `inv_chain` refspice is also within only a few ps of the IBIS waveform tables.
- `io_buf` refspice is hundreds of ps earlier than the IBIS waveform tables.

So the `io_buf` problem is not a pybis replay problem. pybis is faithfully reproducing the timing in `io_buf.ibs`.

### Evidence 2: Fresh Reruns Match Existing Raw Data

The four clean ngspice benches were rerun into:

- `results/refspice_pybis_correlation_study_2026-05-27/rerun_raw/`

The newly rerun waveforms match the existing package raw files numerically with maximum signal difference `0.0`.

This means the result is reproducible and not an old/raw-file artifact.

### Evidence 3: io_buf Input Slew Sweep

New experiment script:

- `scripts/run_io_buf_input_slew_correlation.py`

New output folder:

- `results/refspice_pybis_correlation_study_2026-05-27/io_buf_input_slew_sweep/`

Important generated files:

- `io_buf_input_slew_refspice_vs_ibis.csv`
- `io_buf_input_slew_refspice_vs_ibis.png`

In the original clean refspice bench, the input edge is `5 ps`. At the 50% output threshold:

| io_buf edge | 5 ps input, refspice - IBIS |
|---|---:|
| rising | about `-570 ps` |
| falling | about `-634 ps` |

Then the transistor-level `io_buf.sp` bench was swept with slower input rise/fall times. When timing is measured from the start of the input transition, a roughly `1 ns` input edge brings the refspice result close to the IBIS VT table:

| io_buf edge | 1 ns input, refspice - IBIS from input start |
|---|---:|
| rising, 50% | about `-53 ps` |
| falling, 50% | about `+9 ps` |

But when timing is measured from the input threshold crossing, the mismatch remains large:

| io_buf edge | 1 ns input, refspice - IBIS from threshold |
|---|---:|
| rising, 50% | about `-478 ps` |
| falling, 50% | about `-567 ps` |

Interpretation:

- The `io_buf.ibs` waveform timing behaves as if it includes delay from a slow characterization input edge.
- The IBIS table time origin appears closer to the start of that edge than to the later input threshold crossing used by the pybis `InputDriven` detector.
- The original `5 ps` refspice bench is therefore not stimulus-matched to the `io_buf.ibs` waveform characterization.

### Evidence 4: Corrected Continuous RSF Overlay

After the input-slew finding, a corrected RSF-style overlay was generated using:

- `io_buf.sp` refspice with `1 ns` input rise/fall slew
- pybis converted from `io_buf.ibs`
- `io_buf.ibs` VT waveform tables

Corrected RSF plot folder:

- `results/refspice_pybis_correlation_study_2026-05-27/corrected_io_buf_rsf_plot/`

Most important review plot:

- `refspice_vs_pybis_rsf_load.png`

This plot intentionally keeps the same visual structure as the original clean package plot:

- rise
- steady high
- fall

The corrected refspice raw file has its fall at `10 ns`, because with SPICE `PULSE(0 3.3 1n 1n 1n 8n 20n)` the falling transition starts after the `1 ns` rise plus the `8 ns` high time. For review, the falling segment was remapped to `9 ns` so the plot has the same RSF layout as:

- `clean_ibis_vs_pybis_matched_pkg/plots/refspice_vs_pybis_rsf_load.png`

This is a plotting/remapping step only; the source raw data was not changed.

The corrected continuous RSF overlay shows good transient alignment:

| Comparison | RMSE |
|---|---:|
| Pad refspice vs pybis | about `24.1 mV` over the full RSF plot |
| Load refspice vs pybis | about `24.1 mV` over the full RSF plot |
| pybis pad vs IBIS VT table | about `6.3 mV` over the full RSF plot |

This confirms the practical point: when the `io_buf.sp` reference is driven with a stimulus consistent with the apparent `io_buf.ibs` characterization timing, the refspice-vs-pybis transient comparison becomes well aligned. The earlier `0.6-0.7 ns` apparent pybis delay was mainly a bench/characterization-stimulus mismatch.

### Why inv_chain Does Not Show the Same Problem

The two source packages are not equivalent.

`inv_chain` is a tight source pair:

- `t2b_0615_v5.ibs` says it was created by Cadence T2B with HSPICE.
- It contains `Vmeas = 0.900V`.
- The refspice source is a simple 8-stage inverter chain.
- The clean bench stimulus is consistent with a fast, direct digital switching test.

`io_buf` is looser:

- `io_buf.ibs` says it was created by `PYS2IBIS3`.
- The `[Source]` says `Netlist generated by Grok`.
- The transistor source is a more complex I/O buffer with OE logic, predriver logic, output stack, feedback input sensing, and parasitic caps.
- The exact IBIS waveform characterization deck is not present in this package.

So `inv_chain` is a direct, known T2B correlation case. `io_buf` is an IBIS file and a transistor deck that are related, but their exact characterization stimulus/time origin is not currently proven to match.

### Practical Meaning

For `io_buf`:

- pybis is doing what the IBIS file tells it to do.
- The big `0.6-0.7 ns` delay is mostly inherited from the IBIS waveform timing.
- Comparing that pybis output against a `5 ps`-input transistor reference is not a clean source-correlation test.

For `inv_chain`:

- IBIS, pybis, and refspice are all aligned closely.
- This proves that the converted pybis architecture does not inherently add a large fixed delay.

### Remaining Uncertainty

We still do not have the original `PYS2IBIS3` characterization deck for `io_buf.ibs`. Therefore the exact stimulus used to build the VT tables is not proven directly.

However, the input slew sweep is strong evidence that the `io_buf.ibs` waveform tables correspond to a much slower input transition, approximately around `1 ns`, when measured from input transition start.

### Recommended Next Steps

1. Locate or regenerate the `io_buf.ibs` characterization deck.
2. Recreate `io_buf.ibs` with a documented input stimulus and timing reference.
3. For transistor-vs-IBIS validation, run the transistor reference with the same input slew used during IBIS waveform extraction.
4. For high-speed channel studies, avoid interpreting the current `io_buf.ibs` pybis delay as a simulator error. It is a model/source-correlation issue.
5. If we need a high-speed behavioral model for `io_buf`, regenerate the IBIS file from `io_buf.sp` under the intended fast input stimulus, or use the transistor-level reference directly.
