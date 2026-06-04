# AI Agent Reference For IBIS_Comparison

Date: 2026-06-03

Current repo path:

`C:\Users\simom\Desktop\Projects\IBIS_Comparison`

Some older reports and generated links still mention:

`C:\Users\simom\Desktop\IBIS_Comparison`

Treat the `Projects\IBIS_Comparison` path as the active repo unless the user
explicitly says otherwise.

## 1. Read This First

This repository is not a simple one-off simulation folder. It is a comparison
study across several related flows:

- transistor-level reference SPICE, usually called `refspice`
- IBIS models converted to SPICE through `pybis2spice`
- ngspice
- Xyce
- historical HSPICE native-IBIS output
- newer Hibiki I3C and Wmodel channel experiments
- reusable plotting, eye, and ngspice GUI tooling

For future AI agents:

- Do not trust `codex_history.md` blindly. It can be useful context, but always
  verify with the current files, generated outputs, and reports.
- Do not treat a visually nicer eye diagram as automatically correct. The
  accepted eye flow is physical clock/UI-grid folding, not per-edge alignment.
- Do not create a new plotting script for every small plot unless the reusable
  tools cannot do the job. Prefer `scripts/transient_plot.py`,
  `scripts/eye_diagram.py`, and `scripts/ngspice_lab.py`.
- Do not assume ngspice stability means Xyce stability. The transistor-level
  paths agree well; the pybis behavioral paths have simulator-specific
  numerical limits.
- Do not assume the direct pybis model is the same thing as the current best
  Xyce pybis continuation model. The latter is a modified/conditioned model.
- Do not use ideal lossless T-line PRBS as the acceptance gate unless the user
  changes the project goal. It is a useful stress test, not the frozen main
  benchmark.

## 2. Local Tooling

Known local executables and launch commands:

```powershell
# ngspice
C:\Users\simom\Desktop\Projects\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe

# pybis2spice venv Python
C:\Users\simom\Desktop\Projects\spice\pybis2spice\.venv\Scripts\python.exe

# Xyce used in the documented Xyce work
C:\Program Files\XyceNF_7.10\bin\Xyce.exe
```

Common commands:

```powershell
# Accepted io_buf PRBS/RLGC regression
python scripts\run_accepted_prbs_rlgc_regression.py

# Xyce pybis minimum-modification ladder
python scripts\run_xyce_pybis_minmod_ladder.py

# Reusable transient plot tool
python scripts\transient_plot.py --list-signals hspice\native_ibis_exp1\tb_exp1.tr0 --fmt hspice

# ngspice Lab GUI
& 'C:\Users\simom\Desktop\Projects\spice\pybis2spice\.venv\Scripts\python.exe' scripts\ngspice_lab.py gui
```

HSPICE status:

- Historical HSPICE native-IBIS `.tr0` files exist.
- No matched HSPICE + transistor-level `io_buf.sp` accepted-benchmark result is
  currently available.
- HSPICE work should remain deferred until the license/setup is ready.

## 3. Main Source Models And Test Families

### io_buf controlled comparison

Core files:

- `models/io_buf.sp`
- `models/io_buf.ibs`
- `models/hspice_ngspice.mod`
- `ngspice_refspice/`
- `ngspice_pybis/`
- `xyce_refspice/`
- `xyce_pybis/`

Purpose:

- Compare transistor-level `io_buf.sp` against `io_buf.ibs` converted by
  `pybis2spice`.
- Compare ngspice and Xyce on the same topology.
- Separate model-fidelity problems from simulator/numerical problems.

### inv_chain correlation comparison

Core files:

- `inv_chain/`
- `docs/reports/REFSPICE_VS_PYBIS_DELAY_IOBUF_VS_INVCHAIN_2026-05-21.md`
- `docs/reports/REFSPICE_PYBIS_CORRELATION_ROOTCAUSE_2026-05-27.md`

Purpose:

- Cross-check whether the large `io_buf` refspice-vs-pybis delay is intrinsic
  to the pybis runtime method.
- It is not intrinsic: `inv_chain` aligns within roughly `0-15 ps`.

### Hibiki I3C weak-driver work

Core files:

- `pcbauto/Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs`
- model: `I3C_TX_0p125mA_tx`
- component: `A11486_IBIS-00001760`
- `scripts/run_hibiki_i3c_tx_0p125ma_ngspice.py`
- `scripts/run_hibiki_i3c_tx_0p125ma_1160ohm_ngspice.py`
- `scripts/run_hibiki_i3c_tx_0p125ma_1160ohm_ground_5pulse_ngspice.py`
- `scripts/ngspice_lab.py`

Purpose:

- Simulate a very weak I3C TX model in ngspice through pybis conversion.
- Test 50 ohm fixture cases and a matched `1160 ohm` ground termination.
- Build a reusable CLI/GUI around the ngspice workflow.

### Wmodel channel work

Core files:

- `pcbauto/Wmodel.sp`
- `scripts/run_hibiki_wmodel_baseline_ngspice.py`
- `scripts/run_hibiki_wmodel_cascade_ngspice.py`
- `results/hibiki_i3c_tx_0p125ma_wmodel_baseline_ngspice_2026-05-29/`
- `results/hibiki_i3c_tx_0p125ma_wmodel_cascade_ngspice_2026-05-29/`

Purpose:

- Check whether HSPICE W-model definitions can be used in ngspice.
- They cannot be used directly as ngspice W-elements.
- Current workaround is a baseline RLGC ladder conversion using `Ro`, `Lo`,
  `Go`, and `Co`.
- `Rs` skin-effect and `Gd` dielectric-loss terms are documented but ignored in
  the baseline conversion. In this specific Wmodel file, `Gd = 0` for all three
  traces.
- `Wmodel.sp` contains model definitions but no instance length, so the baseline
  scripts assume `100 mm` per trace.

## 4. Original Plan Status

Source plan:

- `ibis_comparison_plan.md`

Current position:

| Plan item | Current status | Important note |
|---|---|---|
| ngspice + transistor `io_buf.sp` | Done | Stable for accepted PRBS/RLGC benchmark |
| ngspice + pybis2spice | Done for accepted benchmark | Stable with the known ngspice pybis setup |
| ngspice + SPISim converted examples | Partial | SPISim examples informed validation style; no runnable SPISim conversion of our exact model |
| HSPICE native IBIS | Deferred | Historical `.tr0` exists, but not a current matched accepted run |
| Xyce + transistor `io_buf.sp` | Done | Stable and close to ngspice |
| Xyce + pybis2spice | Practical pass | Full accepted benchmark requires Xyce-specific continuation model |
| HSPICE + transistor `io_buf.sp` | Not done | Candidate deck exists, no saved result |

The frozen accepted benchmark is:

| Item | Value |
|---|---|
| Stimulus | PRBS7 voltage-source PWL |
| UI | `5 ns`, `200 Mbps` |
| Input transition | `200 ps` |
| Duration | `1000 ns` |
| Channel | new 50 ohm 10-section RLGC ladder |
| Termination | 50 ohm to ground at `n10b` |
| Supply | `3.3 V` |
| Eye plot | physical clock/UI-grid folding only |

Primary accepted result folder:

- `results/final_prbs_rlgc_comparison_2026-05-11/`

Primary accepted commands:

```powershell
python scripts\run_accepted_prbs_rlgc_regression.py
python scripts\run_xyce_pybis_minmod_ladder.py
```

## 5. Stable And Unstable Flow Summary

| Flow | Status | Why |
|---|---|---|
| ngspice + `io_buf.sp` + PRBS/RLGC | Stable | Direct transistor model, damped RLGC channel, V-source PWL breakpoints, known ngspice model adjustments |
| Xyce + `io_buf.sp` + PRBS/RLGC | Stable | Xyce handles the transistor-level BSIM3 deck well; agrees closely with ngspice |
| ngspice + direct pybis + PRBS/RLGC | Stable for accepted benchmark | Requires known setup; avoid `uic`; use V-source PWL and RLGC channel |
| Xyce + direct pybis + PRBS/RLGC | Not stable | DCOP/stalls and repeated-edge behavioral stiffness |
| Xyce + `edge15_flat4p2` pybis + PRBS/RLGC | Practical pass | Modified continuation model plus Xyce transient controls |
| pybis + ideal T-line PRBS | Stress only | ngspice can stall long-run; Xyce has no solved long-window profile |
| HSPICE + `io_buf.sp` | Missing | No matched saved transient result |
| HSPICE native IBIS historical `.tr0` | Useful but not accepted baseline | Bench does not match current frozen PRBS/RLGC setup |

## 6. Root Causes And Lessons Learned

### 6.1 Weird eye diagrams were not only an eye-tool bug

The user noticed that generated eye diagrams looked strange: large rise/fall
phase separation, missing expected intersections, and repeated step-response
looking overlays.

What we learned:

- Early eye-tool logic could make plots misleading if it aligned edges in a
  non-physical way.
- The final accepted eye approach is physical clock/UI-grid folding only.
- The strong rise/fall phase distortion is visible in the transient data.
- It also appears in transistor-level `io_buf.sp`, not just pybis.

Important reports:

- `docs/reports/IBIS_COMPARISON_PROGRESS_REPORT_2026-05-11.md`
- `docs/reports/TRANSIENT_EYE_REVIEW_2026-05-13.md`

Practical rule:

- If a physical eye looks unusual, do not "fix" the eye tool to hide it.
  Investigate the transient waveform and model behavior.

### 6.2 ngspice pybis RSF collapse was a real model bug

In a rise-steady-fall case, one generated pybis `.sub` briefly rose and then
collapsed low while the input was still high.

Root cause:

- The emitted model did not use the original state-aware selector logic from
  `pybis2spice/subcircuit.py`.
- A smoothed selector block selected the falling-family `Ku/Kd` hold path
  during steady high.
- `KUR0/KUF0` tables were sane; final `Ku/Kd` selection was wrong.

Fix:

- Regenerate from the current `pybis2spice` source.
- Promote regenerated `ngspice_pybis/driver_OutputInput_Typical.sub`.

Report:

- `docs/reports/RSF_ROOTCAUSE_AND_FIX_2026-05-18.md`

Practical rule:

- If pybis output collapses during a steady high input, inspect final `Ku/Kd`
  selector logic before blaming the bench.

### 6.3 Fast-UI pybis behavior is a model-fidelity boundary

For stressed short-UI patterns, the pybis coefficient model can diverge from
the transistor reference.

Important mechanism:

- IBIS VT waveform tables are single-edge tables.
- They implicitly assume the new edge starts from a fully settled opposite
  state.
- At normal UI, that assumption is often close enough.
- At stressed UI, especially patterns like short high/low/high sequences, the
  previous transition may not be settled when the next edge begins.
- The pybis `Ku/Kd` table handoff can therefore jump to a canonical initial
  condition that does not match the actual partial state.

This is not primarily an ngspice-vs-Xyce mismatch:

- Corrected ngspice pybis and Xyce pybis agree well in the stressed pybis
  behavior sweeps.
- The larger difference is pybis-vs-refspice.

Important reports and plots:

- `docs/reports/PYBIS_TWO_BEHAVIORS_2026-05-13.md`
- `docs/reports/TRANSIENT_EYE_REVIEW_2026-05-13.md`
- `results/transient_review_plots_2026-05-13/stressed_edge50_prbs80_channel/`

Two documented stressed behaviors:

| Behavior | Trigger | Symptom |
|---|---|---|
| Positive rise precursor spike | previous high, exactly 1 UI low gap, then new rising edge | pybis receiver jumps high while source-side pybis node is still near low |
| Negative 2 UI high-run fall-window mismatch | exactly 2 UI high run before falling input edge | pybis receiver is much lower than refspice in the tied fall window, then catches up |

Practical rule:

- Normal PRBS/RLGC is an acceptance benchmark.
- Stressed short-UI/long-channel cases are diagnostic for model limitations and
  history sensitivity.

### 6.4 Xyce direct pybis is a numerical stiffness problem, not just syntax

Xyce pybis required syntax porting:

| ngspice/pybis form | Xyce form |
|---|---|
| `Bxx n1 n2 V = expr` | `Bxx n1 n2 V={expr}` |
| `Bxx n1 n2 I = expr` | `Bxx n1 n2 I={expr}` |
| `pwl(x, ...)` expression | `table(x, ...)` |
| `.save V(...)` | `.print tran format=csv ...` |
| internal node `v(xdrv.ku)` | `V(XDRV:Ku)` |

But syntax conversion alone was not enough.

Root-cause pieces found:

- sharp `tanh(200*...)` gates
- edge detector/latch timing logic
- behavioral source/table stiffness
- internal elapsed-time/tail node `NX`
- late rising `KUR/KDR` coefficient tails around `NX = 4.2-4.8 ns`
- reactive loads, especially ideal T-line stress cases

Known practical Xyce pybis full-run setup:

- model: `driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub`
- internal `.ic`: `Ku=0`, `Kd=1`, `NX=0`, `N6=0`, `N8=0`
- Xyce time controls:

```spice
.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
.options output initial_interval=10p
.tran 10p 1000n uic
```

Important distinction:

- `edge15_flat4p2` is the current practical full PRBS/RLGC pass.
- It is not direct pybis and should not be presented as a proof that direct
  pybis is robust in Xyce.

Reports:

- `docs/reports/XYCE_RESULTS_2026-05-09.md`
- `docs/reports/IBIS_COMPARISON_PROGRESS_REPORT_2026-05-11.md`

### 6.5 `io_buf` refspice-vs-pybis delay was a source-correlation issue

The `io_buf` comparison originally showed pybis delayed by roughly `0.6-0.7 ns`
relative to transistor refspice. The `inv_chain` comparison did not.

Root cause:

- pybis follows `io_buf.ibs` VT waveform timing closely.
- The transistor refspice bench used a very fast `5 ps` input edge.
- `io_buf.ibs` appears to have been characterized with a much slower input
  transition, roughly around `1 ns`, with a time origin closer to input edge
  start than input threshold crossing.
- Therefore the mismatch is mostly between `io_buf.ibs` waveform timing and the
  fast-edge transistor reference bench, not a pybis runtime delay.

Evidence:

- pybis-vs-IBIS is only about `5-10 ps`.
- `io_buf` refspice-vs-IBIS is hundreds of ps early with 5 ps input.
- Slowing the `io_buf.sp` refspice input edge to about `1 ns` gives a much
  better RSF overlay.
- `inv_chain` aligns within about `0-15 ps`, proving the converter architecture
  is not inherently adding a large fixed lag.

Reports:

- `docs/reports/REFSPICE_VS_PYBIS_DELAY_IOBUF_VS_INVCHAIN_2026-05-21.md`
- `docs/reports/REFSPICE_PYBIS_CORRELATION_ROOTCAUSE_2026-05-27.md`

Practical rule:

- For transistor-vs-IBIS validation, match the transistor input stimulus to the
  IBIS characterization stimulus. If the characterization deck is missing,
  avoid over-interpreting delay as a simulator or converter bug.

### 6.6 Hibiki I3C weak-driver observations

The model:

- IBIS: `pcbauto/Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs`
- component: `A11486_IBIS-00001760`
- model: `I3C_TX_0p125mA_tx`

Matched `1160 ohm` ground-terminated 5-pulse run:

- result folder:
  `results/hibiki_i3c_tx_0p125ma_1160ohm_ground_5pulse_ngspice_2026-05-28/`
- average high: about `0.6034 V`
- average low: about `0.0005 V`
- average 10-90 rise: about `3.561 ns`
- average 90-10 fall: about `3.677 ns`
- input edge setting: `5 ps`

The colleague concern was that system-simulation rise time looked very large
and I3C expectations were around `8-10 ns`. Based on the current runs:

- The bare `1160 ohm` matched-load run is not extremely slow; it is about
  `3.5-3.7 ns` 10-90 at the pad.
- Adding Wmodel-derived channel capacitance/loss changes the picture
  significantly.
- A `100 mm` baseline Wmodel RLGC ladder gives first-rise 10-90 times around
  `8.86 ns` for Trace01/Trace02 and `12.27 ns` for Trace03.
- Cascading Trace01 + Trace02 + Trace03, assuming `100 mm` each, gives about
  `14.51 ns` first-rise 10-90 at the far end.

Practical rule:

- Before calling the weak-driver result unrealistic, check the load, channel
  length, channel capacitance, and whether Wmodel skin/dielectric loss is being
  approximated or ignored.

### 6.7 Wmodel conversion is a baseline, not a full W-element replacement

`pcbauto/Wmodel.sp` contains HSPICE W model definitions:

- `Wmodel_Trace01::Sig`
- `Wmodel_Trace02::Sig`
- `Wmodel_Trace03::Sig`

Current baseline conversion:

- parse `Ro`, `Lo`, `Go`, `Co`
- convert each trace to a lumped RLGC ladder
- assume `100 mm` length per trace
- use `80` ladder sections per trace
- ignore `Rs`
- ignore `Gd` because it is zero in this file

Approximate trace summary for `100 mm`:

| Trace | Z0 approx | Delay | First-rise 10-90 in individual baseline |
|---|---:|---:|---:|
| Trace01 | `122.49 ohm` | `0.535 ns` | `8.855 ns` |
| Trace02 | `122.49 ohm` | `0.535 ns` | `8.855 ns` |
| Trace03 | `65.95 ohm` | `0.548 ns` | `12.271 ns` |

Cascade summary:

- order: Trace01 -> Trace02 -> Trace03
- assumed total length: `300 mm`
- ideal LC delay estimate: `1.618 ns`
- far-end first-rise 10-90: `14.510 ns`

Important limitation:

- This is not frequency-dependent W-element behavior. It is a first-pass
  ngspice-compatible baseline using constant RLGC.

## 7. ngspice Setup Lessons

Working accepted pybis PRBS/RLGC style:

```spice
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7
.tran 10p 1000n
```

Working transistor refspice PRBS/RLGC style:

```spice
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran 10p 1000n uic
```

Important ngspice findings:

- Use V-source PWL stimulus. It exposes breakpoints.
- Avoid behavioral-source PRBS PWL for acceptance runs.
- `Rin=1 ohm` between ideal source and DUT input is safe and useful.
- For ngspice pybis PRBS/RLGC, do not add `uic` by default.
- In the alignment study, adding `.ic + uic` was the first regression point.
- Refspice-like solver settings and power-feed cleanup did not rescue the
  pybis run after `uic` was added.
- Ideal T-line PRBS can stall even in ngspice; use it as stress only.
- Source damping around `1.75-2 ohm` helped ngspice ideal-T-line PRBS in some
  windows, but the effect is non-monotonic.

## 8. Xyce Setup Lessons

Working transistor refspice style:

```spice
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran 10p 1000n uic
.print tran format=csv time V(in_dig) V(in_buf) V(pad_ref) V(tx_out) V(n10b) V(in_sense_ref)
```

Working practical Xyce pybis style:

```spice
.ic V(pad)=0 V(tx_out)=0 V(n10b)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
.options output initial_interval=10p
.tran 10p 1000n uic
.print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
```

Important Xyce findings:

- Direct pybis syntax conversion is necessary but not sufficient.
- `method=trap maxord=1` is effectively the Backward-Euler-like profile used.
- `.options output initial_interval=10p` helps output size/runtime but is not a
  convergence fix.
- Explicit internal `.ic` values are important for pybis startup.
- Direct pybis can pass simple edges with good controls but is not robust for
  repeated switching.
- The Xyce pybis direct/minimal-modification question remains open.

## 9. Eye And Transient Plot Tooling

### `scripts/transient_plot.py`

Use this for future transient review plots.

Supports:

- HSPICE ASCII `.tr0`
- ngspice binary `.raw`
- Xyce `.csv` / `.prn`
- overlays
- zoom windows
- metrics CSV
- signal listing

Doc:

- `docs/TRANSIENT_PLOT_TOOL.md`

### `scripts/eye_diagram.py`

Use this for physical eye review.

Important:

- Clock/UI-grid folding is the accepted physical mode.
- Do not use edge-aligned diagnostic plots as final evidence.
- Brighter overlay eyes and exact output filenames were added during the review
  work.

### `scripts/ngspice_lab.py`

This is now the preferred reusable ngspice CLI/GUI for IBIS/SPICE buffer tests.

Capabilities:

- choose IBIS or SPICE DUT
- convert selected IBIS model through pybis
- scan IBIS components/models/corners into dropdowns
- add multiple DUTs in one run
- choose termination and optional channel
- choose pulse train, bit pattern, or PRBS7 stimulus
- generate schematic preview before running
- run ngspice
- view plots in embedded matplotlib
- live log tab streams ngspice output and heartbeat status
- disables duplicate Run Sim while one run is active
- waveform viewer supports toolbar pan/zoom, mouse wheel zoom, right/middle drag
  pan, and draggable H/V markers
- vertical markers show time plus interpolated voltage for visible traces

Doc:

- `docs/ngspice_lab.md`

## 10. Important Artifact Map

Plans and summary docs:

- `ibis_comparison_plan.md`
- `README.md`
- `docs/AI_AGENT_REFERENCE.md`
- `docs/reports/IBIS_COMPARISON_PROGRESS_REPORT_2026-05-11.md`
- `docs/reports/XYCE_RESULTS_2026-05-09.md`
- `docs/reports/TRANSIENT_EYE_REVIEW_2026-05-13.md`
- `docs/reports/PYBIS_TWO_BEHAVIORS_2026-05-13.md`
- `docs/reports/RSF_ROOTCAUSE_AND_FIX_2026-05-18.md`
- `docs/reports/REFSPICE_VS_PYBIS_DELAY_IOBUF_VS_INVCHAIN_2026-05-21.md`
- `docs/reports/REFSPICE_PYBIS_CORRELATION_ROOTCAUSE_2026-05-27.md`

Accepted io_buf benchmark:

- `results/final_prbs_rlgc_comparison_2026-05-11/`
- `results/final_prbs_rlgc_comparison_2026-05-11/final_metrics_summary.csv`
- `results/final_prbs_rlgc_comparison_2026-05-11/pairwise_error_summary.csv`

Normal/stressed review plots:

- `results/transient_review_plots_2026-05-13/normal_prbs_channel/`
- `results/transient_review_plots_2026-05-13/stressed_edge50_prbs80_channel/`

Pybis behavior sweeps:

- `results/pybis_spike_trend_sweep_2026-05-12/`

Refspice/pybis correlation:

- `results/refspice_pybis_correlation_study_2026-05-27/`
- `clean_ibis_vs_pybis_matched_pkg/`
- `inv_chain/`

Hibiki weak-driver:

- `results/hibiki_i3c_tx_0p125ma_ngspice_2026-05-28/`
- `results/hibiki_i3c_tx_0p125ma_1160ohm_ngspice_2026-05-28/`
- `results/hibiki_i3c_tx_0p125ma_1160ohm_ground_5pulse_ngspice_2026-05-28/`

Hibiki Wmodel:

- `pcbauto/Wmodel.sp`
- `results/hibiki_i3c_tx_0p125ma_wmodel_baseline_ngspice_2026-05-29/`
- `results/hibiki_i3c_tx_0p125ma_wmodel_cascade_ngspice_2026-05-29/`

Reusable tools:

- `scripts/transient_plot.py`
- `scripts/eye_diagram.py`
- `scripts/ngspice_lab.py`
- `scripts/run_accepted_prbs_rlgc_regression.py`
- `scripts/run_xyce_pybis_minmod_ladder.py`
- `scripts/run_hibiki_wmodel_baseline_ngspice.py`
- `scripts/run_hibiki_wmodel_cascade_ngspice.py`

## 11. Recommended Next Steps

For io_buf comparison:

1. Keep `results/final_prbs_rlgc_comparison_2026-05-11/` as the accepted
   benchmark baseline unless the user explicitly changes the benchmark.
2. If continuing Xyce pybis research, focus on reducing modification level from
   `edge15_flat4p2` toward less-relaxed variants without losing the 1000 ns
   PRBS/RLGC pass.
3. Keep ideal T-line PRBS as a named stress test, not the acceptance gate.
4. If HSPICE becomes available, run a matched HSPICE + `io_buf.sp` accepted
   benchmark before making further HSPICE conclusions.
5. If source-correlation quality matters, regenerate `io_buf.ibs` with a known
   characterization deck and known input slew.

For Hibiki/I3C:

1. Use `scripts/ngspice_lab.py` for interactive cases and repeatable CLI
   configs.
2. Compare bare `1160 ohm` matched load against channel-loaded cases before
   judging driver strength.
3. Treat the current Wmodel RLGC conversion as a baseline only.
4. If frequency-dependent loss matters, implement a better approximation for
   `Rs` and nonzero `Gd`, or run in a simulator that supports the W-element
   model directly.
5. If real board length is known, replace the current `100 mm` per-trace
   assumption in the Wmodel scripts.

## 12. Common Mistakes To Avoid

| Mistake | Why it is wrong |
|---|---|
| Using `uic` in ngspice pybis PRBS/RLGC by default | It caused the first known regression in the alignment study |
| Treating Xyce `edge15_flat4p2` as direct pybis | It is a continuation model, not the direct converted model |
| Comparing fast-edge `io_buf.sp` directly to `io_buf.ibs` and blaming pybis for the delay | The IBIS VT table timing appears characterized with slower input timing |
| Hiding eye distortion with edge alignment | The distortion is in the transient waveform and should remain visible |
| Using ideal T-line PRBS as the main acceptance gate | It is a severe numerical stress topology |
| Assuming Wmodel files directly run in ngspice | The current file is HSPICE W model definitions; ngspice needs a conversion or different channel representation |
| Starting from `codex_history.md` alone | It is a chat reference, not verified state |

## 13. Short Bottom Line

The open-source io_buf pipeline is usable for the accepted PRBS/RLGC benchmark:

- ngspice and Xyce transistor-level `io_buf.sp` agree closely.
- ngspice direct pybis works for the accepted benchmark.
- Xyce pybis works only through a documented continuation model.
- HSPICE transistor-level comparison remains missing.
- Eye diagrams should be physically folded, even when the result looks strange.

The newer Hibiki/I3C work shows:

- the `I3C_TX_0p125mA_tx` pybis ngspice setup is runnable;
- matched `1160 ohm` load alone gives about `3.6 ns` 10-90 pad edges;
- Wmodel-derived channel loading can push far-end rise times into the
  `8-15 ns` range depending on trace/cascade assumptions;
- the Wmodel ngspice path is currently an RLGC baseline conversion, not a full
  HSPICE W-element equivalent.
