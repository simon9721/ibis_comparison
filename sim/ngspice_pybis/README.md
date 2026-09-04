# ngspice_pybis

This folder holds the ngspice-side artifacts for the `io_buf.ibs` comparison work.

The important idea is that there are two generations of ngspice work here:

- older direct-wrapper experiments
- current preferred SPISim-style input-driven experiments

## Important Files

### Model files

- `driver_OutputInput_Typical.sub`
  Current preferred converted output model.
  Uses explicit `OUT IN EN VCC VSS`.
  Implements SPISim-style elapsed-time and `Ku/Kd` behavior.

- `driver_Output_Typical_ext.sub`
  Older direct-wrapper model.
  Kept for reference, not the preferred path.

### Shared support files

- `channel.sp`
  Copy of the project channel file used by the ngspice channel benches.

- `prbs11.pwl`
  Copy of the PRBS source data.

- `prbs11_ngspice.inc`
  ngspice behavioral-source include generated from `prbs11.pwl`.

## Compact Validation Decks

- `tb_validation_pulse_ngspice_pybis.sp`
  Compact validation deck with a `.control` section and linearized ASCII raw output.

- `tb_validation_pulse_ngspice_pybis_batch.sp`
  Preferred plain batch/raw compact validation deck.
  Use this when comparing directly against SPISim's `.spc` workflow.

- `tb_validation_rfr_ngspice_pybis_batch.sp`
  Rise-fall-rise compact validation deck.
  Useful for inspecting coefficient behavior across two reversals.

Outputs:

- `tb_validation_pulse_ngspice_pybis.raw`
- `tb_validation_pulse_ngspice_pybis_batch.raw`
- `tb_validation_rfr_ngspice_pybis_batch.raw`

## Channel Decks

- `tb_exp1_ngspice_pybis.sp`
  Older direct-wrapper channel bench.

- `tb_exp1_ngspice_pybis_inputdriven.sp`
  Full `2 us` SPISim-style input-driven bench with `.control`/linearize flow.

- `tb_exp1_ngspice_pybis_inputdriven_batch.sp`
  Full `2 us` SPISim-style input-driven bench in plain batch/raw form.
  This is the preferred long-run correlation deck.

- `tb_exp1_ngspice_pybis_inputdriven_100n.sp`
  Short `100 ns` interactive/raw bench.

- `tb_exp1_ngspice_pybis_inputdriven_100n_batch.sp`
  Preferred short `100 ns` plain batch/raw bench.

- `tb_exp1_ngspice_pybis_inputdriven_500n.sp`
  Medium-duration diagnostic bench.

Outputs currently kept:

- `tb_exp1_ngspice_pybis.raw`
- `tb_exp1_ngspice_pybis_inputdriven_100n.raw`
- `tb_exp1_ngspice_pybis_inputdriven_100n_batch.raw`

Note:
- A full `2 us` batch/raw output is not currently kept because the interactive test run was interrupted before completion.

## Recommended Usage

Use these in order:

1. `tb_validation_pulse_ngspice_pybis_batch.sp`
   Best for compact model validation.

2. `tb_validation_rfr_ngspice_pybis_batch.sp`
   Best for checking rise/fall/re-rise handoff behavior directly.

3. `tb_exp1_ngspice_pybis_inputdriven_100n_batch.sp`
   Best for quick PRBS/channel validation.

4. `tb_exp1_ngspice_pybis_inputdriven_batch.sp`
   Best for long correlation runs if you are prepared for a longer ngspice runtime.

## Runtime Expectations

- Compact validation decks are fast.
- The short `100 ns` channel deck is still practical.
- The full `2 us` waveform-based PRBS/channel deck is slow and should be treated as a long-run job.
