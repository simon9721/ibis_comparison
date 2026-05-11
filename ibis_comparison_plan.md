# IBIS Buffer Simulation Comparison Plan

Date updated: 2026-05-11

Workspace: `C:\Users\simom\Desktop\IBIS_Comparison`

## 1. Objective

This project compares IBIS-derived buffer simulation behavior across ngspice,
Xyce, and eventually HSPICE. The current source model is controlled:

- `io_buf.sp`: transistor-level CMOS tristate I/O buffer
- `io_buf.ibs`: IBIS file generated from `io_buf.sp`
- `driver_OutputInput_Typical.sub`: pybis2spice conversion of the IBIS model

The purpose is to separate three questions:

1. Model fidelity: how close is converted IBIS-SPICE to transistor-level
   `io_buf.sp`?
2. Simulator portability: how close are ngspice and Xyce on the same model and
   testbench?
3. Numerical robustness: which simulator/setup/model combinations converge
   reliably, and which are stress cases?

HSPICE is intentionally excluded from the current accepted result set because a
matched HSPICE + `io_buf.sp` transient result is not available yet.

## 2. Frozen Accepted Benchmark

The current accepted benchmark is now frozen as:

| Item | Value |
|---|---|
| Stimulus | PRBS7 voltage-source PWL |
| UI | 5 ns, 200 Mbps |
| Input transition | 200 ps rise/fall |
| Duration | 1000 ns |
| Channel | new 50 ohm, 10-section lumped RLGC ladder |
| Termination | 50 ohm to ground at `n10b` |
| Supply | 3.3 V |
| Temperature | 27 C |
| Eye plot | physical clock/UI-grid folding only |

The ideal T-line PRBS cases are now explicitly classified as stress tests, not
the acceptance gate.

Final accepted benchmark artifacts are in:

`results/final_prbs_rlgc_comparison_2026-05-11/`

## 3. Experiment Matrix

| # | Simulator | Buffer model | Current status | Stability status |
|---|---|---|---|---|
| 1 | ngspice | `io_buf.sp` transistor-level | Done | Stable for accepted PRBS/RLGC benchmark |
| 2 | ngspice | pybis2spice direct | Done | Stable for accepted PRBS/RLGC benchmark with known setup |
| 3 | ngspice | SPISim converted examples | Partial | Static reference examples only; no runnable SPISim conversion of our model |
| 4 | HSPICE | native IBIS | Deferred | Historical `.tr0` files exist, but no matched accepted benchmark run |
| 5 | Xyce | `io_buf.sp` transistor-level | Done | Stable and close to ngspice |
| 6 | Xyce | pybis2spice | Practical pass | Full PRBS/RLGC works with `edge15_flat4p2` continuation model; direct pybis still not robust |
| 7 | HSPICE | `io_buf.sp` transistor-level | Not done | Candidate deck exists, but no `.tr0/.lis/.st0` result found |

## 4. Current Final Results

From `results/final_prbs_rlgc_comparison_2026-05-11/final_metrics_summary.csv`:

| Case | Completed | V(n10b) min | V(n10b) max | Rise 20-80 | Fall 20-80 | Eye height | Eye width | Rise/fall 50 split |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ngspice + `io_buf.sp` | yes | -0.021 V | 1.517 V | 932 ps | 168 ps | 296 mV | 2618 ps | 0.265 UI |
| Xyce + `io_buf.sp` | yes | -0.025 V | 1.518 V | 928 ps | 168 ps | 305 mV | 2623 ps | 0.265 UI |
| ngspice + pybis | yes | -0.008 V | 1.540 V | 1034 ps | 323 ps | 1064 mV | 5000 ps | 0.274 UI |
| Xyce + pybis `edge15_flat4p2` | yes | -0.007 V | 1.541 V | 1034 ps | 352 ps | 998 mV | 1370 ps | 0.277 UI |

Pairwise simulator agreement:

| Comparison | RMSE | Max abs error | Mean error |
|---|---:|---:|---:|
| Xyce `io_buf.sp` minus ngspice `io_buf.sp` | 3.14 mV | 23.97 mV | 0.16 mV |
| Xyce pybis minus ngspice pybis | 26.64 mV | 50.38 mV | -13.30 mV |

Interpretation:

- Xyce and ngspice agree very closely for transistor-level `io_buf.sp`.
- Xyce pybis is close enough to be useful for the accepted benchmark, but it is
  still a modified continuation setup, not a direct pybis pass.
- The strong rise/fall timing asymmetry appears in transistor-level and pybis
  results; the physical eye tool should preserve it rather than compensate it.

## 5. Accepted Testbench Setup

### 5.1 PRBS Stimulus

Use voltage-source inline PWL includes:

```spice
Vstim  in_dig  0  PWL(0.000000000e+00 0.0000
+ 5.000000000e-09  0.0000
+ ...
)
```

Do not use a behavioral-source PRBS:

```spice
* Avoid this for PRBS
Bstim in_dig 0 V = pwl(time, ...)
```

Reason: V-source PWL exposes breakpoints to the timestep controller. Behavioral
PWL hides transition times inside an expression and caused excessive tiny-step
work.

### 5.2 Channel

Use the new 50 ohm RLGC channel:

- R = 0.05 ohm per section
- L = 3.46 nH per section
- C = 1.384 pF per section
- G = 1e-6 S per section
- 10 sections
- approximate total delay = 692 ps

ngspice channel file:

`new 50ohm channel/channel_ngspice.sp`

Xyce channel files replace behavioral shunt conductances with equivalent
`1meg` shunt resistors:

- `xyce_refspice/channel_xyce.sp`
- `xyce_pybis/channel_xyce.sp`

## 6. Simulator Setup Profiles

### 6.1 ngspice + `io_buf.sp`

Representative deck:

`ngspice_refspice/tb_refspice_prbs7_new50ohm_batch.sp`

Current setup:

```spice
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran 10p 1000n uic
```

Status: pass.

Reasoning: `uic + .ic` avoids a bad operating point for the transistor-level
reactive-channel startup.

### 6.2 ngspice + pybis

Representative deck:

`results/prbs_rlgc_clean_2026-05-10/ngspice/tb_clean_prbs_rlgc_ngspice.sp`

Current setup:

```spice
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7
.tran 10p 1000n
```

Status: pass.

Important: do not add `uic` to this accepted pybis PRBS/RLGC deck. The
alignment study found that adding `.ic + uic` was the first regression point:

- baseline pybis RLGC: pass to 1000 ns
- add `Rin=1`: pass to 1000 ns
- add `.ic + uic`: stall around 372 ns
- stricter/refspice-like solver settings after `uic`: still stalls
- power/enable feed cleanup after `uic`: still stalls

### 6.3 Xyce + `io_buf.sp`

Representative deck:

`xyce_refspice/tb_refspice_prbs7_new50ohm_xyce.cir`

Current setup:

```spice
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran 10p 1000n uic
.print tran format=csv time V(in_dig) V(in_buf) V(pad_ref) V(tx_out) V(n10b) V(in_sense_ref)
```

Status: pass.

### 6.4 Xyce + pybis

Representative deck:

`results/prbs_rlgc_clean_2026-05-10/xyce/tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir`

Current setup:

```spice
.ic V(pad)=0 V(tx_out)=0 V(n10b)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
.options output initial_interval=10p
.tran 10p 1000n uic
.print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
```

Model:

`driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub`

Status: practical pass.

Meaning:

- edge/latch block relaxed to `tanh15`
- final selector mostly remains near `tanh92`
- rising KUR/KDR table tail flattened after 4.2 ns
- direct unmodified pybis remains not robust for full repeated switching

## 7. Syntax Porting Notes

Xyce pybis required syntax conversion:

| ngspice/pybis form | Xyce form |
|---|---|
| `Bxx n1 n2 V = expr` | `Bxx n1 n2 V={expr}` |
| `Bxx n1 n2 I = expr` | `Bxx n1 n2 I={expr}` |
| `pwl(x, ...)` expression | `table(x, ...)` |
| `.save V(...)` | `.print tran format=csv ...` |
| internal node `v(xdrv.ku)` | `V(XDRV:Ku)` |
| behavioral shunt `G value={1e-6*v(n,0)}` | `R_G n 0 1meg` |

These syntax conversions make the model parse, but they do not by themselves
make the direct pybis model robust in Xyce.

## 8. Stress Tests and Non-Accepted Cases

The following are useful stress cases but not the current acceptance gate:

| Case | Current finding |
|---|---|
| ngspice pybis + ideal T-line PRBS, no source damping | stalls near 125.6 ns on long windows |
| ngspice pybis + ideal T-line PRBS with `RISO=1.75-2 ohm` | can pass 130-200 ns windows |
| ngspice pybis + ideal T-line PRBS with too much damping (`RISO=5 ohm`) | fails again around 110 ns |
| Xyce pybis + ideal T-line PRBS, no damping | no tested profile completes long windows |
| Xyce `edge50_flat4p2 + RISO=2` ideal T-line PRBS | passes 100 ns, fails 200 ns |
| Xyce pybis with 5 ps edges | severe stress test; not accepted benchmark |
| Xyce direct pybis full PRBS | not robust; DCOP/transition stalls remain |

## 9. Xyce pybis Next-Step Potentials

HSPICE is not ready, so the next optional research direction is Xyce pybis
minimization. Keep two questions separate:

### Question A: Can Xyce run the accepted benchmark?

Current answer: yes, with `edge15_flat4p2`.

### Question B: Can Xyce run direct or minimally modified pybis robustly?

Current answer: not yet.

Potential focused experiments:

1. Start from `edge50_flat4p2`, because it is the best short-PRBS compromise.
2. Try to extend `edge50_flat4p2` from 200 ns to 1000 ns without dropping all
   the way to edge/latch `tanh15`.
3. Keep the KUR/KDR flat tail at 4.2 ns, since it fixes the RFR/T-line tail
   root cause.
4. Vary only edge/latch smoothing first; avoid changing selector smoothing
   unless needed.
5. Track three gates separately:
   - SPISim-style pulse200p T-line
   - SPISim-style RFR200p T-line
   - accepted PRBS/RLGC 1000 ns

Do not treat ideal T-line PRBS as the acceptance gate unless the project goal
changes to "lossless T-line robustness."

## 10. HSPICE Next Step, Deferred

No HSPICE work should be started until the HSPICE setup/license is ready.

When ready, build a matched HSPICE + `io_buf.sp` accepted-benchmark deck:

- PRBS7
- 5 ns UI
- 200 ps edges
- new 50 ohm RLGC channel
- 50 ohm termination
- `.TRAN 10p 1000n`
- `.OPTION POST=2`

Candidate starting file:

`experiments/tb_exp2.sp`

Known issue:

- no `tb_exp2.tr0/.lis/.st0` result exists
- include paths likely need cleanup before running from `experiments/`

## 11. Current Deliverables

Primary status/report files:

- `docs/reports/IBIS_COMPARISON_PROGRESS_REPORT_2026-05-11.md`
- `docs/reports/XYCE_RESULTS_2026-05-09.md`
- `docs/reports/ALIGNMENT_FINDINGS_2026-05-07.md`
- `docs/reports/STATUS_2026-05-06.md`
- `results/final_prbs_rlgc_comparison_2026-05-11/README.md`
- `results/final_prbs_rlgc_comparison_2026-05-11/final_metrics_summary.csv`
- `results/final_prbs_rlgc_comparison_2026-05-11/pairwise_error_summary.csv`
- `results/final_prbs_rlgc_comparison_2026-05-11/REGRESSION_SUMMARY.md`
- `results/xyce_pybis_minmod_ladder_2026-05-11/README.md`
- `results/xyce_pybis_minmod_ladder_2026-05-11/xyce_pybis_minmod_ladder_summary.csv`

Primary plots:

- `results/final_prbs_rlgc_comparison_2026-05-11/plots/rx_transient_overlay_0_120ns.png`
- `results/final_prbs_rlgc_comparison_2026-05-11/plots/rx_transient_overlay_30_80ns.png`
- `results/final_prbs_rlgc_comparison_2026-05-11/plots/rx_transient_overlay_full.png`
- `results/final_prbs_rlgc_comparison_2026-05-11/eyes/*/*_overlay.png`
- `results/xyce_pybis_minmod_ladder_2026-05-11/xyce_pybis_minmod_ladder_matrix.png`

Primary commands:

```powershell
python scripts\run_accepted_prbs_rlgc_regression.py
python scripts\run_xyce_pybis_minmod_ladder.py
```

## 12. Immediate Plan

1. Treat `results/final_prbs_rlgc_comparison_2026-05-11/` as the current
   accepted benchmark baseline.
2. Use `scripts/run_accepted_prbs_rlgc_regression.py` for the one-command
   accepted-benchmark rerun.
3. Use `scripts/run_xyce_pybis_minmod_ladder.py` to maintain the Xyce pybis
   minimum-modification matrix.
4. Keep HSPICE deferred until the matched setup is ready.
5. If continuing Xyce pybis research, focus on minimal-modification variants
   around `edge50_flat4p2` and `edge15_flat4p2`, with the accepted PRBS/RLGC
   benchmark as the final gate.
6. Keep the eye tool physically clock-folded; no visual edge compensation for
   final evidence.
