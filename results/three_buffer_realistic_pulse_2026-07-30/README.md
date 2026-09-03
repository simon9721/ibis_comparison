# Three-Buffer Realistic-Pulse Campaign

This campaign replaces the earlier 1 ps stimulus with transistor-library-aware 100 ps and 250 ps input slews. Pulse widths are selected from HSPICE transistor response rather than named `short` in advance.

## Headline Findings

- The transistor sweep found `15` pad-partial cases among `28` selected controls/stress cases. All pad-partial cases are short-high; pad-partial short-low cases: `0`.
- The internal-control panel shows that pad-partial does not always mean the final output-stage gate was already mid-transition at the external reverse edge. This distinction is especially important for the multistage `inv_chain` and `ex2` buffers.
- The minimum full-swing short-low command already produces a complete output excursion in all three transistor circuits. The pipeline preserves that as regeneration evidence instead of inventing a shorter reduced-amplitude pulse.
- `inv_chain` has a narrow partial short-high region at 100 ps input slew (102-125 ps pulse width), but its minimum 250 ps full-swing pulse already produces a complete transition.
- The hybrid reversal detector stayed inactive in `12/12` long-pulse controls. The normal-operation branch therefore remained on legacy replay as designed.
- The hybrid is not a universal winner. It reduces median errors in several partial-pulse groups, but coefficient-step warnings expose the switching handoff; the full gate-state path is usually more continuous.
- Fast `io_buf` remains the clearest structural failure: both candidate paths frequently leave the native coefficient envelope, and the full gate-state model has numeric failures.
- Native-reference coefficients themselves exceed the old nominal `[-0.2, 1.2]` interval for: `ex2/fast_5ps, ex2/slow_1ns, io_buf/fast_5ps`. Candidate validity is therefore checked against each case's native envelope with a `0.10` margin; the absolute interval is retained only as context.

## Experiment Design

- All three transistor libraries are 0.18 um-class models.
- `100 ps` is the aggressive realistic stress slew; `250 ps` is the moderate slew.
- The libraries do not specify a board-interface slew limit, so these are engineering stress points validated against measured transistor timing, not claimed datasheet limits.
- Load remains `50 ohm || 2 pF`, matching the earlier studies.
- A transistor-only sweep chooses widths nearest 20%, 55%, and 85% output excursion for each device, direction, and slew.
- The selected widths are then compared across HSPICE transistor, HSPICE native IBIS, ngspice full gate-state, and ngspice legacy-normal/gate-on-reversal hybrid.
- Slow 1 ns and fast 5 ps characterized IBIS files are both retained. Their characterization slew is a model property; the runtime input slew in this study is 100 ps or 250 ps.

## What Counts As Mid-Transition

The report does not infer mid-transition from pulse width alone. It records the transistor pad excursion and, where available, the final output-stage control-node extrema. A selected case is partial when the transistor output excursion lies between 5% and 95% of its loaded full swing.

- Selected cases with partial transistor output: `15/28`.
- ngspice candidate failures preserved: `55`.

## Transistor Pad-Partial Short-High Results

This table excludes long controls and regenerated/full-swing cases. `Completed` means no envelope, discontinuity, or numeric warning under the recorded checks.

| Device | IBIS profile | Flow | Cases | Completed | Step warnings | Outside native envelope | Numeric failures | Median pad RMSE mV | Median Ku RMSE | Median Kd RMSE |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| io_buf | slow_1ns | gate_state | 6 | 3 | 0 | 1 | 2 | 27.940 | 0.02190 | 0.20015 |
| io_buf | slow_1ns | hybrid | 6 | 3 | 1 | 2 | 0 | 31.480 | 0.02672 | 0.17761 |
| io_buf | fast_5ps | gate_state | 6 | 0 | 0 | 5 | 1 | 501.445 | 0.23827 | 0.33322 |
| io_buf | fast_5ps | hybrid | 6 | 0 | 0 | 6 | 0 | 348.806 | 0.15819 | 0.19968 |
| inv_chain | slow_1ns | gate_state | 3 | 3 | 0 | 0 | 0 | 148.590 | 0.11403 | 0.10045 |
| inv_chain | slow_1ns | hybrid | 3 | 3 | 0 | 0 | 0 | 146.038 | 0.10553 | 0.09989 |
| inv_chain | fast_5ps | gate_state | 3 | 3 | 0 | 0 | 0 | 148.387 | 0.10793 | 0.10001 |
| inv_chain | fast_5ps | hybrid | 3 | 3 | 0 | 0 | 0 | 147.906 | 0.10680 | 0.09994 |
| ex2 | slow_1ns | gate_state | 6 | 6 | 0 | 0 | 0 | 74.824 | 0.10021 | 0.06674 |
| ex2 | slow_1ns | hybrid | 6 | 1 | 5 | 0 | 0 | 59.221 | 0.06859 | 0.05338 |
| ex2 | fast_5ps | gate_state | 6 | 6 | 0 | 0 | 0 | 72.788 | 0.08756 | 0.05968 |
| ex2 | fast_5ps | hybrid | 6 | 0 | 6 | 0 | 0 | 61.761 | 0.07141 | 0.05571 |

## Normal Transition Characterization

| Device | Edge ps | Rise delay ps | Rise 10-90 ps | Fall delay ps | Fall 90-10 ps | Loaded swing V |
|---|---:|---:|---:|---:|---:|---:|
| io_buf | 50 | 1648.1 | 1477.9 | 302.5 | 372.0 | 1.6036 |
| io_buf | 100 | 1635.2 | 1469.6 | 311.2 | 372.0 | 1.6035 |
| io_buf | 250 | 1616.9 | 1447.9 | 337.9 | 376.1 | 1.6035 |
| inv_chain | 50 | 327.8 | 93.0 | 313.9 | 58.4 | 1.4222 |
| inv_chain | 100 | 337.6 | 93.2 | 323.6 | 58.4 | 1.4222 |
| inv_chain | 250 | 360.4 | 93.3 | 346.9 | 58.5 | 1.4222 |
| ex2 | 50 | 1374.8 | 442.0 | 1116.5 | 364.8 | 1.5451 |
| ex2 | 100 | 1379.3 | 442.7 | 1122.7 | 365.0 | 1.5451 |
| ex2 | 250 | 1396.6 | 444.4 | 1147.2 | 364.7 | 1.5451 |

## Selected Widths

| Device | Edge ps | Direction | Target | Width ps | Measured transistor excursion | Partial |
|---|---:|---|---|---:|---:|---|
| io_buf | 100 | rise_fall | long_control | 10000 | 100.0% | False |
| io_buf | 100 | short_high | visible | 1194 | 19.9% | True |
| io_buf | 100 | short_high | mid_transition | 1560 | 55.0% | True |
| io_buf | 100 | short_high | near_settled | 2191 | 85.0% | True |
| io_buf | 100 | short_low | visible | 100 | 100.8% | False |
| io_buf | 250 | rise_fall | long_control | 10000 | 100.0% | False |
| io_buf | 250 | short_high | visible | 1198 | 20.4% | True |
| io_buf | 250 | short_high | mid_transition | 1569 | 55.1% | True |
| io_buf | 250 | short_high | near_settled | 2239 | 85.1% | True |
| io_buf | 250 | short_low | visible | 250 | 100.8% | False |
| inv_chain | 100 | rise_fall | long_control | 10000 | 100.0% | False |
| inv_chain | 100 | short_high | visible | 102 | 19.5% | True |
| inv_chain | 100 | short_high | mid_transition | 108 | 60.5% | True |
| inv_chain | 100 | short_high | near_settled | 125 | 84.9% | True |
| inv_chain | 100 | short_low | visible | 100 | 101.5% | False |
| inv_chain | 250 | rise_fall | long_control | 10000 | 100.0% | False |
| inv_chain | 250 | short_high | visible | 250 | 100.3% | False |
| inv_chain | 250 | short_low | visible | 250 | 101.5% | False |
| ex2 | 100 | rise_fall | long_control | 10000 | 100.0% | False |
| ex2 | 100 | short_high | visible | 721 | 14.5% | True |
| ex2 | 100 | short_high | mid_transition | 820 | 56.6% | True |
| ex2 | 100 | short_high | near_settled | 921 | 85.3% | True |
| ex2 | 100 | short_low | visible | 100 | 103.6% | False |
| ex2 | 250 | rise_fall | long_control | 10000 | 100.0% | False |
| ex2 | 250 | short_high | visible | 717 | 15.1% | True |
| ex2 | 250 | short_high | mid_transition | 808 | 54.3% | True |
| ex2 | 250 | short_high | near_settled | 913 | 85.4% | True |
| ex2 | 250 | short_low | visible | 250 | 103.6% | False |

## Candidate Summary

| Device | IBIS profile | Edge ps | Flow | Cases | Native-envelope valid | Native reference outside nominal range | Median pad RMSE mV | Median Ku RMSE | Median Kd RMSE |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| ex2 | fast_5ps | 100 | gate_state | 5 | 5 | 5 | 49.804 | 0.06770 | 0.04237 |
| ex2 | fast_5ps | 100 | hybrid | 5 | 4 | 5 | 38.224 | 0.05771 | 0.03791 |
| ex2 | fast_5ps | 250 | gate_state | 5 | 4 | 5 | 89.800 | 0.10233 | 0.07386 |
| ex2 | fast_5ps | 250 | hybrid | 5 | 4 | 5 | 86.528 | 0.10338 | 0.07169 |
| ex2 | slow_1ns | 100 | gate_state | 5 | 5 | 5 | 40.877 | 0.06146 | 0.03413 |
| ex2 | slow_1ns | 100 | hybrid | 5 | 5 | 5 | 37.111 | 0.05285 | 0.03633 |
| ex2 | slow_1ns | 250 | gate_state | 5 | 4 | 5 | 84.716 | 0.10213 | 0.06579 |
| ex2 | slow_1ns | 250 | hybrid | 5 | 4 | 5 | 84.034 | 0.09826 | 0.06837 |
| inv_chain | fast_5ps | 100 | gate_state | 5 | 5 | 0 | 140.868 | 0.10458 | 0.09793 |
| inv_chain | fast_5ps | 100 | hybrid | 5 | 5 | 0 | 139.732 | 0.10392 | 0.09961 |
| inv_chain | fast_5ps | 250 | gate_state | 3 | 3 | 0 | 208.159 | 0.16278 | 0.15813 |
| inv_chain | fast_5ps | 250 | hybrid | 3 | 3 | 0 | 206.020 | 0.16151 | 0.15666 |
| inv_chain | slow_1ns | 100 | gate_state | 5 | 5 | 0 | 142.517 | 0.10824 | 0.09839 |
| inv_chain | slow_1ns | 100 | hybrid | 5 | 5 | 0 | 142.042 | 0.10498 | 0.09811 |
| inv_chain | slow_1ns | 250 | gate_state | 3 | 3 | 0 | 207.840 | 0.16259 | 0.15787 |
| inv_chain | slow_1ns | 250 | hybrid | 3 | 3 | 0 | 204.296 | 0.15925 | 0.15359 |
| io_buf | fast_5ps | 100 | gate_state | 4 | 2 | 4 | 364.115 | 0.17865 | 0.19274 |
| io_buf | fast_5ps | 100 | hybrid | 5 | 2 | 5 | 141.309 | 0.11918 | 0.13041 |
| io_buf | fast_5ps | 250 | gate_state | 4 | 0 | 4 | 580.400 | 0.26191 | 0.32007 |
| io_buf | fast_5ps | 250 | hybrid | 5 | 2 | 5 | 574.081 | 0.19799 | 0.27613 |
| io_buf | slow_1ns | 100 | gate_state | 4 | 3 | 0 | 32.866 | 0.02826 | 0.11005 |
| io_buf | slow_1ns | 100 | hybrid | 5 | 3 | 0 | 40.556 | 0.03597 | 0.12719 |
| io_buf | slow_1ns | 250 | gate_state | 4 | 4 | 0 | 117.652 | 0.05957 | 0.11247 |
| io_buf | slow_1ns | 250 | hybrid | 5 | 5 | 0 | 40.801 | 0.02920 | 0.10471 |

## Files

- `normal_transition_characterization.csv`: measured transistor timing at 50, 100, and 250 ps input slew.
- `transistor_pulse_sweep.csv`: every transistor-only pulse candidate.
- `selected_realistic_cases.csv`: adaptive width choices and internal control extrema.
- `metrics.csv`: candidate errors versus HSPICE native IBIS.
- `partial_short_high_summary.csv`: model statistics restricted to transistor-confirmed partial short-high cases.
- `selected_runs/<device>/<edge>/<profile>/waveform_data/`: exact plotted data.
- `selected_runs/<device>/<edge>/<profile>/plots/`: four-panel evidence figures.
- `selected_runs/<device>/<edge>/<profile>/editable_figures/`: editable one-panel pad, Ku, and Kd JSON recipes.
- `plots/00_transistor_pulse_selection.png`: selection evidence.
- `reference_cache_manifest.csv`: cache/run provenance for every HSPICE result.

## Fast-Edge Figure View

The current presentation view uses only `fast_5ps` IBIS results. Fast-only contact sheets are:

- `selected_runs/io_buf/fast_5ps/contact_sheet.png`
- `selected_runs/inv_chain/fast_5ps/contact_sheet.png`
- `selected_runs/ex2/fast_5ps/contact_sheet.png`

In the fourth panel, measured transistor gate controls are displayed as `1 - V(gate)/VDD`. This is a plotting-only polarity normalization: the raw CSV still contains the actual HSPICE gate voltage. It makes an external rising command and its delayed final-stage control both appear as rising signals.

`plots/00_transistor_pulse_selection.png` is not an IBIS-model comparison. It is the transistor-only experiment-design figure used to choose pulse widths that produce visible, partial, and near-settled loaded-pad motion. Therefore it is shared by both IBIS characterization profiles and remains relevant when the comparison view is restricted to `fast_5ps`.

Open any editable recipe with:

```powershell
& .\scripts\launch_figure_editor.cmd .\path\to\figure_recipe.json
```

## Interpretation Limits

HSPICE transistor pad is the circuit-level output reference. Native-IBIS Ku/Kd are native-IBIS diagnostics, not transistor-internal truth. A small pad error does not by itself validate coefficient behavior, and a partial pad response does not guarantee both pullup and pulldown internal controls are partial.
