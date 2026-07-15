# Master Work Report: IBIS, pybis, HSPICE/ngspice, and S-parameter Conversion

Date: 2026-06-25

Workspace root:

```text
C:\Users\sh3qm\code\ibis_comparison
```

This document is the consolidated technical record for the recent work. Many result folders already contain local `README.md` files, CSVs, figures, and decks. This master report ties them together so the work can be presented, resumed, or audited without digging through the chat history.

## 1. Executive Summary

The work has two main branches:

1. `io_buf` IBIS / pybis / SPICE correlation.
2. S-parameter channel conversion to ngspice-ready SPICE models.

The `io_buf` branch now has a clear story:

- Normal complete fast edges are well matched between HSPICE native IBIS and ngspice pybis.
- Slow edges and interrupted short pulses expose a real state-machine difference in `Ku/Kd`.
- Simple replay fixes are not enough; the best direction so far is a hidden charge/gate-state model, especially `InputDrivenChargeLimitedGateHybrid`.

The S-parameter branch also has a clear story:

- A general `sNp -> ngspice SPICE` workflow is not solved yet.
- Reduced RX-through models can be useful for matched 50 ohm RX waveform shape, but must not be advertised as full multiport replacements.
- scikit-rf vector fitting is promising for some 2-port cases and slower edges, but fast-edge trust requires independent edge-bandwidth and transient smoke gates.
- BBS/BroadbandSPICE integration runs and produces models, but current BBS results are not ready as clean PASS models.

Current best engineering conclusions:

- For `io_buf` interrupted switching, coefficient agreement must be a hard gate. Pad RMSE alone can hide physically wrong `Ku/Kd`.
- For S-parameter conversion, HSPICE should stay audit-only. Normal selection must use independent metrics, ngspice smoke, passivity/singularity checks, and edge-bandwidth suitability.
- For presentation, the strongest visible progress is:
  - old/new `io_buf.ibs` overlays showing the s2ibispy transition-time issue,
  - S-parameter RX-trust report with grouped overlays,
  - vector-fit campaign showing edge-rate-dependent pass/fail behavior,
  - switching coefficient short-pulse demos showing why hidden state is needed.

## 2. Result Folder Index

All paths below are absolute.

### Core `io_buf` IBIS and pybis correlation

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_old_new_four_overlays_2026-06-05
C:\Users\sh3qm\code\ibis_comparison\results\hspice_rsf_io_buf_inv_chain_2026-06-04
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_fast_edge_retest_2026-06-05
```

### Switching coefficients and interrupted transition studies

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_switching_coeff_overlay_2026-06-18
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_switching_coeff_sweep_2026-06-19
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_state_continuous_retrigger_2026-06-20
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_coeff_state_retrigger_2026-06-20
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_shortpulse_hybrid_retrigger_2026-06-21
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_gate_state_retrigger_2026-06-22
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_directional_gate_state_retrigger_2026-06-22
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_charge_limited_gate_retrigger_2026-06-22
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_value_matched_replay_2026-06-23
```

### S-parameter trust workflow and reports

```text
C:\Users\sh3qm\code\ibis_comparison\results\sparam_conversion_quality_2026-06-08
C:\Users\sh3qm\code\ibis_comparison\results\sparam_trust_workflow_calibration_v1_2026-06-09
C:\Users\sh3qm\code\ibis_comparison\results\sparam_rx_trust_v2_2026-06-11
C:\Users\sh3qm\code\ibis_comparison\results\visual_support_pack_2026-06-12
C:\Users\sh3qm\code\ibis_comparison\results\status_bucket_overlays_2026-06-12
C:\Users\sh3qm\code\ibis_comparison\results\simple_good_bad_overlays_2026-06-12
```

### Converted SPICE model comparison and Clarity demo

```text
C:\Users\sh3qm\code\ibis_comparison\results\converted_sp_comparison_2026-06-12
```

Important document:

```text
C:\Users\sh3qm\code\ibis_comparison\results\converted_sp_comparison_2026-06-12\share_pack\case_01_Clarity_example_s2p\CLARITY_SP_MODEL_WALKTHROUGH.md
```

### scikit-rf vector fitting campaign

```text
C:\Users\sh3qm\code\ibis_comparison\results\sparam_vector_fit_campaign_v1_2026-06-12
C:\Users\sh3qm\code\ibis_comparison\results\sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight
C:\Users\sh3qm\code\ibis_comparison\results\sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2
C:\Users\sh3qm\code\ibis_comparison\results\sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18
```

Important documents:

```text
C:\Users\sh3qm\code\ibis_comparison\results\sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18\README.md
C:\Users\sh3qm\code\ibis_comparison\results\sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18\OVERNIGHT_ANALYSIS.md
```

### BroadbandSPICE / BBS integration

```text
C:\Users\sh3qm\code\ibis_comparison\results\sparam_bbs_integration_v1_2026-06-16
C:\Users\sh3qm\code\ibis_comparison\results\sparam_bbs_quality_tuning_v1_2026-06-17
C:\Users\sh3qm\code\ibis_comparison\results\clarity_bbs_s2p_overlay_2026-06-19
C:\Users\sh3qm\code\ibis_comparison\results\agilent_e5071b_bbs_s4p_overlay_2026-06-19
C:\Users\sh3qm\code\ibis_comparison\results\agilent_io_buf_ibis_bbs_transient_2026-06-19
C:\Users\sh3qm\code\ibis_comparison\results\agilent_io_buf_ibis_bbs_pulsetrain_2026-06-19
C:\Users\sh3qm\code\ibis_comparison\results\agilent_io_buf_ibis_bbs_pulsetrain_settled_2026-06-19
```

### `my_top` / TopXP HSPICE side-project

```text
C:\Users\sh3qm\code\ibis_comparison\results\my_top_hspice_simulation_input_2026-06-18
C:\Users\sh3qm\code\ibis_comparison\results\my_top_hspice_channel_2026-06-18
```

Important document:

```text
C:\Users\sh3qm\code\ibis_comparison\results\my_top_hspice_channel_2026-06-18\MY_TOP_SIMULATION_FLOW.md
```

## 3. Environment And Tooling Status

### HSPICE

HSPICE is available and used successfully for:

- native IBIS simulations,
- transistor/reference SPICE comparisons,
- S-parameter native `S`-element audits,
- `my_top` channel deck reproduction.

HSPICE output files of interest:

```text
*.tr0  transient waveform data
*.lis  listing/log output
*.st0  status
*.ic0  initial condition output
```

### ngspice

The downloaded ngspice executable used during the work is:

```text
\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin\ngspice.exe
```

ngspice is used for:

- pybis-generated behavioral SPICE,
- reference SPICE subcircuits,
- converted S-parameter SPICE macromodels,
- BBS General SPICE outputs.

### pybis / pybis2spice

pybis/ngspice was configured to be ready-to-use locally. The key mode remains `InputDriven`, with several opt-in experimental modes added for interrupted switching research.

Documentation:

```text
C:\Users\sh3qm\code\ibis_comparison\docs\NGSPICE_PYBIS_READY.md
```

Main generator code:

```text
C:\Users\sh3qm\code\ibis_comparison\tools\pybis2spice\pybis2spice\subcircuit.py
```

## 4. `io_buf.ibs` Transition-Time Finding

### Question

The original `io_buf.ibs` was generated through `../s2ibispy`. We suspected the delay between pybis/refspice and native IBIS/refspice was caused by too-slow IBIS transition settings.

### Finding

The generated old `io_buf.ibs` used slow transition timing. The relevant setting is the stimulus edge rate used by s2ibispy, with defaults around `1 ns` rise/fall if not overridden.

That slow transition was too slow for the `io_buf` reference transistor model. Regenerating with a fast edge greatly reduced delay and RMSE.

### Evidence

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_old_new_four_overlays_2026-06-05
```

Key numbers from that folder:

| Figure | Comparison | Rise Delta | Fall Delta | RMSE |
|---|---|---:|---:|---:|
| `01_ngspice_old_slow_io_buf_pybis_vs_refspice.png` | old pybis vs refspice | +580.8 ps | +639.0 ps | 350.6 mV |
| `02_hspice_old_slow_io_buf_ibis_vs_spice.png` | old HSPICE IBIS vs SPICE | +720.2 ps | +645.2 ps | 389.1 mV |
| `03_ngspice_new_fast_io_buf_pybis_vs_refspice.png` | new pybis vs refspice | +81.4 ps | +5.7 ps | 32.2 mV |
| `04_hspice_new_fast_io_buf_ibis_vs_spice.png` | new HSPICE IBIS vs SPICE | +220.3 ps | +13.6 ps | 93.5 mV |

### Interpretation

For `io_buf`, the s2ibispy default transition settings can be too slow. A faster `tr/tf`, such as the tested fast regenerated model, improves both ngspice pybis and HSPICE native IBIS correlation.

`inv_chain` did not show the same delay because its model/bench behavior was less sensitive to that generated IBIS stimulus edge setting.

## 5. Core IBIS/pybis/HSPICE Test Bench Setup

### Native IBIS HSPICE flow

The HSPICE native IBIS flow uses HSPICE's built-in IBIS support. For switching coefficient extraction, it exposes the internal pullup/pulldown switching functions with `xv_pu=ku` and `xv_pd=kd`.

Conceptual flow:

```text
io_buf.ibs
  -> HSPICE native IBIS B-element
  -> PWL input stimulus
  -> pad load
  -> pad waveform + Ku/Kd diagnostic nodes
```

### ngspice pybis flow

The ngspice pybis flow converts the same IBIS model into a free-SPICE subcircuit.

Conceptual flow:

```text
io_buf.ibs
  -> pybis2spice
  -> driver_OutputInput_Typical.sub
  -> ngspice transient deck
  -> pad waveform + V(xdrv.ku)/V(xdrv.kd)
```

### Standard switching coefficient bench

The switching coefficient studies use:

- 0 V / 3.3 V PWL input.
- 3.3 V supply.
- output pad load such as 50 ohm + 2 pF.
- matched HSPICE and ngspice stimulus/load conditions.

The important comparison signals are:

```text
pad voltage
Ku pullup coefficient
Kd pulldown coefficient
```

## 6. Switching Coefficient Findings

### Baseline coefficient overlay

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_switching_coeff_overlay_2026-06-18
```

Finding:

- A normal rise/fall transition matches very well.
- Pad active-window RMSE is about 5.26 mV.
- `Ku` and `Kd` active-window RMSE are about 0.004 to 0.005.

### Sweep across edge/load/pattern cases

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_switching_coeff_sweep_2026-06-19
```

Key findings:

- Sharp complete toggles match very well.
- Load variation alone is not the weak point.
- Slow input ramps create visible switching-state differences.
- Interrupted output transitions create the largest mismatch.

The key demo folder is:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_switching_coeff_sweep_2026-06-19\interrupted_switching_demo
```

For `short_pulse_2ns_high`:

- HSPICE pad was only about 0.266 V at the reverse command, so the first transition was not settled.
- HSPICE `Ku` peak during the interrupted pulse: about 0.543.
- legacy pybis `Ku` peak: about 1.013.
- HSPICE pad peak: about 0.825 V.
- pybis pad peak: about 1.521 V.

Interpretation:

```text
The risk condition is a new switching event before the previous output transition settles.
At that point, coefficient history matters.
```

## 7. pybis Interrupted-Switching Algorithms Tried

All experimental modes are opt-in. Legacy `InputDriven` remains the default unless explicitly requested.

### 7.1 `InputDrivenStateContinuous`

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_state_continuous_retrigger_2026-06-20
```

Idea:

- Use one continuous normalized `PSTATE`.
- `PSTATE=0` means settled low, `PSTATE=1` means settled high.
- Reverse edges move `PSTATE` toward the new target instead of restarting elapsed time.

Finding:

- Invalid abstraction.
- It can reduce pad RMSE by suppressing drive, but coefficient behavior is wrong.
- It produced pad-only false passes and a large `double_toggle_1ps` regression.

### 7.2 `InputDrivenCoeffState`

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_coeff_state_retrigger_2026-06-20
```

Idea:

- Treat `Ku` and `Kd` as separate continuous coefficient states.
- Drive those states with delayed branch approximations derived from IBIS coefficient tables.
- Do not use one shared `PSTATE`.

Finding:

- Short-pulse coefficient behavior improved.
- Normal complete edges regressed badly: 9 complete-edge regressions.
- Useful as a short-pulse demo, not default-ready.

### 7.3 `InputDrivenShortPulseHybrid`

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_shortpulse_hybrid_retrigger_2026-06-21
```

Idea:

- Preserve legacy `InputDriven` for normal long pulses.
- Activate a correction path only for interrupted short-high pulses.
- Evaluate candidate delay estimators.

Finding:

- Long-pulse control was preserved well.
- Short-high pulses improved versus legacy.
- For `short_pulse_1ns_high`, `Ku` peak was still about 0.3606 while HSPICE was about 0.0746, so the method was still too strong.

### 7.4 `InputDrivenGateStateHybrid`

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_gate_state_retrigger_2026-06-22
```

Idea:

- Introduce transistor-like hidden gate-drive states.
- Use `GUP` and `GDN` internally.
- Map hidden gate states into `Ku/Kd`.

Finding:

- Strong improvement for `Ku` in short-high pulses.
- For `short_pulse_1ns_high`, `Ku` peak moved to about 0.0586, close to HSPICE 0.0746.
- `Kd` timing/recovery remained weak.

### 7.5 `InputDrivenDirectionalGateStateHybrid`

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_directional_gate_state_retrigger_2026-06-22
```

Idea:

- Split interrupted behavior into four directional processes:
  - `Ku` turn-on,
  - `Ku` turn-off,
  - `Kd` turn-off,
  - `Kd` turn-on.
- Handle fall-after-rise and rise-after-fall separately.

Finding:

- Directional thinking was correct.
- The additive event-tap implementation could over-cancel or over-compose state.
- It did not improve enough versus the previous gate-state method.

### 7.6 `InputDrivenChargeLimitedGateHybrid`

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_charge_limited_gate_retrigger_2026-06-22
```

Idea:

- Replace additive event taps with bounded hidden charge states:

```text
QPU = pullup gate-charge state
QPD = pulldown gate-charge state
```

- `QPU/QPD` are SPICE capacitor-backed internal nodes.
- A reverse edge can only discharge or recharge the state that actually exists.

How the gate state is determined:

- From IBIS-derived `Ku/Kd` complete-edge tables, estimate:

```text
pu_on_delay / pu_on_tau
pu_off_delay / pu_off_tau
pd_on_delay / pd_on_tau
pd_off_delay / pd_off_tau
```

- Use delayed edge commands to set `QPUTARGET` and `QPDTARGET`.
- Let the capacitor-backed states follow those targets continuously.
- Build PWL maps:

```text
KUCHG = f_pu(QPU)
KDCHG = f_pd(QPD)
```

- Hybrid mode uses charge-state coefficients only during detected interrupted short-high behavior; otherwise it uses legacy `KULEG/KDLEG`.

Why the capacitor matters:

```text
If QPU only charged to 0.06 before the falling edge,
the falling edge can only discharge from 0.06.
It cannot act as if QPU had reached 1.0.
```

Finding:

- This is the best direction so far.
- It fixes the over-cancellation problem.
- It gives strong short-high `Ku` behavior.
- It still is not default-ready because mirrored short-low behavior and `double_toggle_1ps` remain problematic.

### 7.7 `InputDrivenValueMatchedReplayHybrid`

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_value_matched_replay_2026-06-23
```

Idea:

- On reverse edge, sample current `Ku/Kd`.
- Invert the opposite transition table to find a matching replay time.
- Continue replay from that matched table time.

Finding:

- Important negative baseline.
- It still lets `Ku` go almost full in the key short-high case.
- For `short_pulse_1ns_high`:

```text
HSPICE Ku peak:                  0.0746
legacy pybis Ku peak:            1.0125
ChargeLimitedHybrid Ku peak:     0.0586
ValueMatchedReplay Ku peak:      1.0122
```

Interpretation:

```text
Matching a visible Ku/Kd table value does not uniquely recover the hidden physical state.
Hidden charge/gate state is needed.
```

## 8. S-parameter Conversion Workflow

### Goal

Convert Touchstone `sNp` files into ngspice-ready SPICE models and produce a confidence report that can eventually be trusted without HSPICE.

Normal intended flow:

```text
Touchstone .sNp
  -> inventory
  -> candidate model generation
  -> independent metrics
  -> ngspice smoke tests
  -> PASS/WARN/FAIL report
  -> selected ngspice model
```

Development audit flow:

```text
selected ngspice model
  -> HSPICE native S-element comparison
  -> correlation metrics
  -> calibration summary
```

Important rule:

```text
HSPICE audit must not affect normal model selection.
```

### Canonical workflow script

```text
C:\Users\sh3qm\code\ibis_comparison\scripts\run_sparam_conversion_quality_study.py
```

### Main v2 result

```text
C:\Users\sh3qm\code\ibis_comparison\results\sparam_rx_trust_v2_2026-06-11
```

Important files:

```text
README.md
REPORT_PRESENTATION.md
manifest.csv
metrics.csv
ranking.csv
ngspice_smoke.csv
hspice_correlation.csv
view_trust_summary.csv
view_calibration_summary.csv
audit_overlay_groups\
selected_models\
```

### S-parameter bench topology

For `.s2p`:

```text
source PWL -> 50 ohm source resistor -> p1
channel p1/p2
p2 -> 50 ohm load
RX = V(p2)
TX = V(p1)
dominant path = S21
```

For `.s4p`:

```text
source PWL -> 50 ohm source resistor -> p1
p2 terminated to 50 ohm
p3 observed RX and terminated
p4 terminated to 50 ohm
RX = V(p3)
TX = V(p1)
dominant path in current convention = S31
```

The v2 study was a linear 50 ohm pulse bench, not a nonlinear IBIS driver bench.

### v2 result summary

From `results/sparam_rx_trust_v2_2026-06-11/README.md`:

- Candidate metric rows: 682.
- Selected channels: 149.
- Independent PASS/WARN/FAIL: 0 / 147 / 2.
- RX voltage-shape PASS/WARN/FAIL: 7 / 142 / 56.
- RX timing PASS/WARN/FAIL: 4 / 145 / 56.
- Reflection PASS/WARN/FAIL: 0 / 2 / 203.
- HSPICE correlation rows: 93.
- Successful HSPICE correlations: 80.

Important calibration finding:

- RX voltage-shape independent PASS correlated well with HSPICE in the audited rows.
- RX timing was not clean enough; 50% threshold crossings can be ambiguous when RX swing is small or ringing creates early/false crossings.
- Full-model readiness was not achieved.
- Reduced `.s4p` models are scoped RX-through approximations, not full four-port replacements.

## 9. Reduced S-parameter Models

### Idea

Reduced models are custom ngspice-friendly approximations focused on matched 50 ohm transient behavior, not full S-matrix replacement.

Examples:

```text
reduced_4p_rx_dominant_delay_rc
reduced_4p_rx_delayeq_rc_ring
reduced_s2p_rx_delayeq_rc_ring
reduced_s2p_reflection_s11_rc
```

### Why they exist

Full vector fitting was often too brittle or too slow to become a full-model solution immediately. Reduced models let us ask a scoped question:

```text
Can ngspice reproduce RX through-path waveform shape for this matched 50 ohm bench?
```

### Scope limitations

Reduced `.s4p` RX-through models:

- can be useful for RX voltage shape,
- should be labeled `matched_50ohm_rx_through`,
- should not be used as full multiport replacements,
- do not guarantee reflection/TX/S11/crosstalk behavior.

## 10. scikit-rf Vector Fitting Campaign

### Goal

Determine whether scikit-rf `VectorFitting` can become a trustworthy full-model `sNp -> ngspice .sp` path.

Main script:

```text
C:\Users\sh3qm\code\ibis_comparison\scripts\run_sparam_vector_fit_campaign.py
```

Main result:

```text
C:\Users\sh3qm\code\ibis_comparison\results\sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18
```

Important files:

```text
README.md
OVERNIGHT_ANALYSIS.md
vf_candidates.csv
vf_metrics.csv
vf_ranking.csv
vf_ngspice_smoke.csv
vf_hspice_correlation.csv
plots\
share_pack\
selected_vector_models\
```

### Candidate space tried

The campaign tested:

- fixed vector-fit orders such as `3r3c`, `5r5c`, `8r8c`, `12r12c`,
- complex-dominant settings,
- auto-fit settings,
- raw preprocessing,
- DC hold,
- frequency trim,
- high-frequency hold/rolloff diagnostics,
- passivity-enforced variants,
- ngspice smoke,
- HSPICE audit for selected and top candidates.

### Key numbers

From the phase-1 overnight report:

- Candidate rows: 5970.
- Ranked channels: 9.
- ngspice smoke rows: 72.
- HSPICE audit rows: 54.
- Selected vector models: 6.
- Full/RX/reflection classes: 5 FAIL, 4 WARN; no production-ready PASS.

### Main finding

Vector fitting is promising for some 2-port cases and slower edges, especially `ntwk2` / `ntwk3`. It is not production-ready as a general full-model workflow.

Important edge-rate finding:

```text
required bandwidth ~= 0.35 / edge_time
```

Observed pattern:

- 5 ps edges require about 70 GHz. Current audited cases failed or warned.
- 50 ps edges require about 7 GHz. 10 GHz `ntwk2` / `ntwk3` worked well.
- 500 ps edges require about 0.7 GHz. Audited cases passed.

This independent edge-bandwidth gate explained the HSPICE audit results better than raw frequency-fit/passivity alone.

## 11. Clarity `.s2p` SPICE Model Walkthrough

Result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\converted_sp_comparison_2026-06-12
```

Detailed walkthrough:

```text
C:\Users\sh3qm\code\ibis_comparison\results\converted_sp_comparison_2026-06-12\share_pack\case_01_Clarity_example_s2p\CLARITY_SP_MODEL_WALKTHROUGH.md
```

This document compares:

```text
vector_fit/vector_3r3c.sp
reduced_model/reduced_s2p_rx_delayeq_rc_ring.sp
```

Main teaching point:

- Vector-fit model tries to preserve the full two-port S-matrix `S11/S12/S21/S22`.
- Reduced model focuses on matched 50 ohm RX-through transient response.
- Both can have the same external `.SUBCKT s_equivalent p1 p2` interface while having completely different internal model meaning.

## 12. BroadbandSPICE / BBS Work

### Goal

Test whether BroadbandSPICE/BBS can convert `sNp` to SPICE models that ngspice can use, and compare the converted model to HSPICE native S-parameter behavior.

Main BBS integration result:

```text
C:\Users\sh3qm\code\ibis_comparison\results\sparam_bbs_integration_v1_2026-06-16
```

Key result:

- BBS extraction ran successfully for tested rows.
- BBS produced HSPICE-compatible and General SPICE outputs.
- Current BBS candidates did not reach clean independent PASS.

### Clarity BBS overlay

```text
C:\Users\sh3qm\code\ibis_comparison\results\clarity_bbs_s2p_overlay_2026-06-19
```

We investigated a suspicious plot where converted `S21/S12` looked like straight blue lines. The source issue was in how the converted model response was being evaluated/overlaid, not a simple conclusion that the channel itself was flat.

### Agilent BBS channel transient

Important folders:

```text
C:\Users\sh3qm\code\ibis_comparison\results\agilent_e5071b_bbs_s4p_overlay_2026-06-19
C:\Users\sh3qm\code\ibis_comparison\results\agilent_io_buf_ibis_bbs_transient_2026-06-19
C:\Users\sh3qm\code\ibis_comparison\results\agilent_io_buf_ibis_bbs_pulsetrain_settled_2026-06-19
```

Bench:

- HSPICE: `io_buf.ibs` native IBIS + original S-parameter channel + matched termination.
- ngspice: pybis `io_buf` + BBS converted Agilent channel + same nominal termination.
- Agilent channel used 75 ohm reference impedance, so p2/p3/p4 were terminated to 75 ohm.

Repeated-pulse finding:

- Multiple pulses made overlays easier to interpret than a single isolated pulse, but the channel still behaves like a band-pass/coupled response rather than a DC-settling digital through path.
- RX p3 error was much smaller than TX p1 error in the settled pulse train report.

## 13. `my_top` / TopXP Side Project

Source folder:

```text
\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\my_top-20260618T181135Z-3-001\my_top
```

Result folders:

```text
C:\Users\sh3qm\code\ibis_comparison\results\my_top_hspice_simulation_input_2026-06-18
C:\Users\sh3qm\code\ibis_comparison\results\my_top_hspice_channel_2026-06-18
```

Flow document:

```text
C:\Users\sh3qm\code\ibis_comparison\results\my_top_hspice_channel_2026-06-18\MY_TOP_SIMULATION_FLOW.md
```

### Main conclusion

`simulation_input.sp` is a buffer-only characterization deck. It drives the Tx buffer into loads and supports buffer delay metadata.

The real channel transient deck is:

```text
channel_Tx_out1p_out1n_Rx.sp
```

That deck includes:

```text
standard_step.sp
channel_Tx_out1p_out1n_Rx_ibis.sp
S1.sp
sparams_4port.bnp
scd_example.ibs
```

Conceptual flow:

```text
standard_step
  -> Tx IBIS buffer
  -> 4-port S-parameter channel
  -> Rx IBIS input buffer
  -> rxnode / V(n3,n4)
```

HSPICE reproduction artifacts include:

```text
channel_hspice.tr0
channel_hspice.lis
channel_hspice_waveforms.csv
channel_hspice_waveforms.png
channel_hspice_waveforms_zoom.png
```

## 14. Important Scripts Added Or Used

### S-parameter conversion and trust

```text
scripts\run_sparam_conversion_quality_study.py
scripts\run_sparam_vector_fit_campaign.py
scripts\package_vector_fit_audit_share.py
scripts\make_bbs_touchstone_overlay.py
scripts\make_clarity_bbs_overlay.py
scripts\bbs_extract.py
```

### Agilent/BBS transient studies

```text
scripts\run_agilent_ibis_bbs_transient.py
scripts\run_agilent_ibis_bbs_pulsetrain.py
```

### Switching coefficient and retrigger studies

```text
scripts\run_io_buf_switching_coeff_overlay.py
scripts\run_io_buf_switching_coeff_sweep.py
scripts\make_io_buf_interrupted_switching_demo.py
scripts\analyze_io_buf_switching_coeff_mismatch.py
scripts\run_io_buf_state_continuous_retrigger.py
scripts\run_io_buf_coeff_state_retrigger.py
scripts\run_io_buf_shortpulse_hybrid_retrigger.py
scripts\run_io_buf_gate_state_retrigger.py
scripts\run_io_buf_directional_gate_state_retrigger.py
scripts\run_io_buf_charge_limited_gate_retrigger.py
scripts\run_io_buf_value_matched_replay.py
```

### pybis2spice implementation

```text
tools\pybis2spice\pybis2spice\subcircuit.py
tools\pybis2spice\test\test_pybis2spice.py
```

## 15. Reproduction Commands

These are the most important commands for reproducing the main studies.

### S-parameter RX trust v2

```powershell
py -3.14 scripts/run_sparam_conversion_quality_study.py qualify `
  --study-dir results/sparam_rx_trust_v2_2026-06-11 `
  --skrf-target "$env:TEMP\ibis_skrf_target" `
  --skrf-tests-dir results/sparam_conversion_quality_2026-06-08/inputs/skrf_tests `
  --extra-touchstone-dir hspice/sparam `
  --fast-calibration-profile `
  --dense-samples 501 `
  --sim-timeout 180

py -3.14 scripts/run_sparam_conversion_quality_study.py audit-hspice `
  --study-dir results/sparam_rx_trust_v2_2026-06-11 `
  --skrf-target "$env:TEMP\ibis_skrf_target" `
  --sim-timeout 240 `
  --audit-stop-ns 35 `
  --max-channels 20 `
  --resume

py -3.14 scripts/run_sparam_conversion_quality_study.py report `
  --study-dir results/sparam_rx_trust_v2_2026-06-11
```

### Vector fitting campaign

```powershell
py -3.14 scripts/run_sparam_vector_fit_campaign.py fit `
  --study-dir results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18 `
  --skrf-target "$env:TEMP\ibis_skrf_target" `
  --skrf-tests-dir results/sparam_conversion_quality_2026-06-08/inputs/skrf_tests `
  --extra-touchstone-dir hspice/sparam `
  --phase-profile phase1 `
  --candidate-timeout-s 900 `
  --passivity-strategy near-pass `
  --dense-samples 501 `
  --resume
```

Then run the associated `smoke-ngspice`, `audit-hspice`, and `report` subcommands as needed for that study folder.

### Switching coefficient sweep

```powershell
py -3.14 scripts\run_io_buf_switching_coeff_sweep.py
```

### Charge-limited gate-state retrigger

```powershell
py -3.14 scripts\run_io_buf_charge_limited_gate_retrigger.py
```

### Value-matched replay baseline

```powershell
py -3.14 scripts\run_io_buf_value_matched_replay.py --timeout-s 240
```

## 16. Older May Baseline Work

The June work above builds on earlier May baseline studies. Those are already documented in `docs/reports/`, and this section records how they fit into the full project story.

### Main progress report

```text
C:\Users\sh3qm\code\ibis_comparison\docs\reports\IBIS_COMPARISON_PROGRESS_REPORT_2026-05-11.md
```

Purpose:

- Documents the accepted PRBS7/RLGC comparison benchmark.
- Establishes that ngspice and Xyce can run the transistor-level `io_buf.sp` reference.
- Establishes that ngspice pybis is stable for the accepted benchmark.
- Explains why Xyce pybis needed specific model/timestep conditioning.
- Corrects eye plotting back to physical clock/UI-grid folding rather than edge-aligned cosmetic folding.

Important result folders referenced by that report:

```text
C:\Users\sh3qm\code\ibis_comparison\results\prbs_rlgc_clean_2026-05-10
C:\Users\sh3qm\code\ibis_comparison\results\final_prbs_rlgc_comparison_2026-05-11
C:\Users\sh3qm\code\ibis_comparison\results\io_buf_sp_physical_eye_2026-05-11
C:\Users\sh3qm\code\ibis_comparison\results\xyce_pybis_minmod_ladder_2026-05-11
```

### Pybis stressed-channel behavior

```text
C:\Users\sh3qm\code\ibis_comparison\docs\reports\PYBIS_TWO_BEHAVIORS_2026-05-13.md
```

Purpose:

- Separates two different pybis stressed-channel behaviors:
  - positive rise precursor spike,
  - negative 2 UI high-run fall-window mismatch.
- Shows these are transient waveform behaviors, not eye-plot artifacts.
- Establishes that channel memory/reflection and pybis edge-state behavior can interact.

Important result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\pybis_spike_trend_sweep_2026-05-12
```

### Transient and eye review plots

```text
C:\Users\sh3qm\code\ibis_comparison\docs\reports\TRANSIENT_EYE_REVIEW_2026-05-13.md
```

Purpose:

- Defines a consistent plot review set for normal and stressed channels.
- Documents transient overlays, physical eye diagrams, and `Ku/Kd` diagnostics.
- Makes clear that the review plots are for direct waveform inspection, not just single-number metrics.

Important result folder:

```text
C:\Users\sh3qm\code\ibis_comparison\results\transient_review_plots_2026-05-13
```

### Other historical reports

```text
C:\Users\sh3qm\code\ibis_comparison\docs\reports\ALIGNMENT_FINDINGS_2026-05-07.md
C:\Users\sh3qm\code\ibis_comparison\docs\reports\RSF_ROOTCAUSE_AND_FIX_2026-05-18.md
C:\Users\sh3qm\code\ibis_comparison\docs\reports\REFSPICE_VS_PYBIS_DELAY_IOBUF_VS_INVCHAIN_2026-05-21.md
C:\Users\sh3qm\code\ibis_comparison\docs\reports\REFSPICE_PYBIS_CORRELATION_ROOTCAUSE_2026-05-27.md
C:\Users\sh3qm\code\ibis_comparison\docs\reports\XYCE_RESULTS_2026-05-09.md
```

Purpose:

- Preserve earlier alignment/root-cause findings.
- Explain the historical refspice-vs-pybis delay investigations.
- Document Xyce-specific results and limitations.

## 17. What Is Well Documented Now

This master report plus the linked result-folder READMEs now document:

- the older May accepted PRBS/RLGC baseline and stressed-channel investigations,
- the old/new `io_buf.ibs` transition-time diagnosis,
- the matched HSPICE/ngspice switching-coefficient setup,
- the interrupted-pulse mismatch mechanism,
- every retrigger algorithm tried and why it passed/failed,
- the S-parameter trust workflow and v2 calibration,
- reduced versus vector-fit model philosophy,
- Clarity `.s2p` converted SPICE walkthrough,
- vector fitting campaign settings and conclusions,
- BBS integration and Agilent transient comparison,
- `my_top` HSPICE flow and actual channel deck.

## 18. Remaining Documentation Gaps

The main remaining gap is not missing technical narrative; it is long-term curation:

- Some generated result folders are exploratory smoke runs and should eventually be tagged as `archive`, `superseded`, or `canonical`.
- Several scripts are research scripts with overlapping responsibilities; once the preferred direction is chosen, they should be grouped or renamed by study family.
- For production documentation, `README.md` should eventually be modernized because it still references older absolute paths from a previous machine/user.

## 19. Current Recommended Next Steps

### For pybis interrupted switching

1. Continue from `InputDrivenChargeLimitedGateHybrid`, not value-matched replay.
2. Focus on mirrored short-low behavior and `double_toggle_1ps`.
3. Keep coefficient metrics (`Ku/Kd`) as hard gates.
4. Do not promote any experimental mode as default until normal complete edges and interrupted cases both pass.

### For S-parameter conversion

1. Keep HSPICE as audit-only.
2. Use edge-bandwidth gates before claiming fast-edge readiness.
3. Continue vector fitting on 2-port cases with known sufficient bandwidth.
4. Treat reduced `.s4p` RX models as scoped matched-50-ohm tools only.
5. Do not claim full multiport readiness until reflection/TX and full-matrix behavior pass independently.

### For presentation

Recommended story:

1. `io_buf.ibs` old/new overlay proves transition-time setup matters.
2. Switching coefficient sweep proves normal cases match, short pulses reveal state mismatch.
3. Re-trigger algorithm series shows why simple fixes fail and why charge-state modeling is the right direction.
4. S-parameter trust workflow shows careful separation of RX shape, timing, reflection, and full-model readiness.
5. Vector-fit and BBS campaigns show we tested general conversion methods seriously, but production trust still needs tighter gates.
