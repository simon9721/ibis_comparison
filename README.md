# IBIS_Comparison

This project compares three related flows for the same `io_buf.ibs` driver:

- native HSPICE IBIS simulation
- SPISim's free-spice reference flow
- `pybis2spice` conversion plus ngspice

The current focus is waveform-based ngspice simulation that is as close as practical to SPISim's architecture while still using the converted `pybis2spice` model.

## Layout

- `io_buf.ibs`
  The working IBIS model under test.
- `channel.sp`
  The shared 10-section RLGC ladder channel used by the HSPICE and ngspice channel benches.
- `prbs11.pwl`
  The shared PRBS11 stimulus file.
- `tb_exp1.sp`
  Original HSPICE native-IBIS channel bench with `power=on`.
- `tb_exp1_hspice_poweroff.sp`
  HSPICE native-IBIS channel bench with explicit rails and `power=off`.
- `SimIbis_FreeSpice_From_SPISim/`
  SPISim's example files used as external reference and verification.
- `ngspice_pybis/`
  Generated pybis2spice/ngspice models, benches, and ngspice outputs.

## Where To Start

- Read [STATUS_2026-05-06.md](C:/Users/simom/Desktop/IBIS_Comparison/STATUS_2026-05-06.md) for the most detailed status snapshot.
- Read [ngspice_pybis/README.md](C:/Users/simom/Desktop/IBIS_Comparison/ngspice_pybis/README.md) for the ngspice-side deck map.

## Current Summary

- SPISim's `Ibs2Spc_Coef.spc` and `Ibs2Spc_Ramp.spc` both run successfully in ngspice.
- The converted `pybis2spice` input-driven model now follows the SPISim-style elapsed-time and `Ku/Kd` approach closely enough to validate in ngspice.
- Compact validation decks and short PRBS/channel decks run well in ngspice.
- The full `2 us` PRBS/channel ngspice deck is still a long-run job.

## Recommended Workflow

1. Use the SPISim compact decks as reference:
   `SimIbis_FreeSpice_From_SPISim/Ibs2Spc_Coef.spc`
   `SimIbis_FreeSpice_From_SPISim/Ibs2Spc_Ramp.spc`
2. Use the compact pybis2spice/ngspice validation deck for model checks:
   `ngspice_pybis/tb_validation_pulse_ngspice_pybis_batch.sp`
3. Use the short PRBS/channel deck for quick channel sanity:
   `ngspice_pybis/tb_exp1_ngspice_pybis_inputdriven_100n_batch.sp`
4. Use the full `2 us` deck only for long correlation runs:
   `ngspice_pybis/tb_exp1_ngspice_pybis_inputdriven_batch.sp`

## Notes

- The `ngspice_pybis` folder contains both the current preferred SPISim-style input-driven model and an older direct-wrapper model kept for reference.
- No file moves were done during this documentation pass because many decks rely on simple relative `.include` paths.
