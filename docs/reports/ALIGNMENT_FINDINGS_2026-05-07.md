# Alignment Findings: pybis2spice vs refspice (ngspice)

Date: 2026-05-07
Workspace: IBIS_Comparison

## Goal
Make pybis2spice and refspice ngspice benches as identical as practical, changing one item at a time, and identify which changes break the pybis run.

## Scope
Compared working new-50ohm-channel PRBS benches:
- Refspice bench: `ngspice_refspice/tb_refspice_prbs7_new50ohm_batch.sp`
- pybis bench baseline: `ngspice_pybis/tb_pybis_prbs7_new50ohm.sp`

Both use:
- PRBS7, UI=5 ns, 200 bits, 1000 ns total
- `new 50ohm channel/channel_ngspice.sp`
- `RTERM n10b 0 50`

## Why `Rin=1` exists in refspice input path
`Rin 1 ohm` between ideal source and DUT input is a common SPICE conditioning practice:
- decouples ideal source from a nonlinear/capacitive node
- improves numerical robustness
- is electrically negligible for logic drive levels

## One-change-at-a-time alignment sequence (cumulative)

| Step | Single change introduced | Bench | Outcome |
|---|---|---|---|
| 0 | Baseline pybis new50ohm | `ngspice_pybis/tb_pybis_prbs7_new50ohm.sp` | PASS, 1000.000 ns |
| 1 | Match refspice drive topology only: use refspice PRBS include + `Rin in_src in_dig 1` | `ngspice_pybis/tb_pybis_prbs7_new50ohm_step1_rin.sp` | PASS, 1000.000 ns |
| 2 | Startup only: add `.ic` and `uic` | `ngspice_pybis/tb_pybis_prbs7_new50ohm_step2_uic.sp` | FAIL/STALL at 372.127 ns |
| 3 | Solver only (from step2): `maxord=2`, `abstol=1e-9`, `vntol=1e-5`, `gmin=1e-10`, `trtol=10` | `ngspice_pybis/tb_pybis_prbs7_new50ohm_step3_solver.sp` | FAIL/STALL at 396.059 ns |
| 4 | Power/enable feed topology only (from step3): source->1ohm feed + decap | `ngspice_pybis/tb_pybis_prbs7_new50ohm_step4_pwr.sp` | FAIL/STALL at 396.069 ns |

## Additional pybis+channel combinations tested

| Combination | Bench | Outcome |
|---|---|---|
| PRBS + ideal T-line baseline | `ngspice_pybis/tb_pybis_prbs7_batch.sp` | FAIL (stalls before 1000 ns) |
| PRBS + ideal T-line + `uic+ic` | `ngspice_pybis/tb_pybis_prbs7_uic.sp` | FAIL at 0.413 ns |
| PRBS + ideal T-line + `rshunt/cshunt` | `ngspice_pybis/tb_pybis_prbs7_rshunt.sp` | FAIL at 0.260 ns |
| PRBS + ideal T-line + `Rser=1` | `ngspice_pybis/tb_pybis_prbs7_rser1.sp` | FAIL at 125.618 ns |
| PRBS + new 50ohm RLGC channel | `ngspice_pybis/tb_pybis_prbs7_new50ohm.sp` | PASS, 1000.000 ns |

## Key findings
1. The pybis run remains stable when only the refspice-style PRBS input topology is aligned (Step 1).
2. The first regression point is introducing `uic + ic` (Step 2).
3. Refspice-like solver and power-feed adjustments do not recover the pybis run once `uic` is enabled.
4. For pybis, avoid `uic` in this PRBS+new50ohm setup.
5. pybis failure is still specific to ideal-T-line PRBS benches; the RLGC channel bench can complete 1000 ns.

## Recommended "aligned and working" pybis bench style
Use:
- refspice-style PRBS injection topology (`in_src` + `Rin=1`)
- no `uic`
- current pybis-stable solver settings
- new 50ohm RLGC channel + 50 ohm termination

Reference bench:
- `ngspice_pybis/tb_pybis_prbs7_new50ohm_step1_rin.sp`

## Outputs generated for comparison
- pybis transient (channel input vs load):
  - `plots/validation/pybis_prbs7_new50ohm_chin_vs_load.png`
- pybis eye and transition:
  - `plots/validation/tb_pybis_prbs7_new50ohm_vn10b_eye.png`
  - `plots/validation/tb_pybis_prbs7_new50ohm_vn10b_trans.png`
- refspice transient (channel input vs load):
  - `plots/validation/refspice_prbs7_new50ohm_chin_vs_load.png`

## Notes
- Eye-width value from current eye script is often 0 ps for deterministic traces and should not be used alone as a quality indicator.
- UI-folding logic in `scripts/eye_diagram.py` was corrected during this session to use real multi-UI windows rather than tiled single-UI slices.
