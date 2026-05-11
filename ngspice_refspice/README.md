# Ngspice Reference-SPICE Benches

These decks use the transistor-level reference buffer from `../io_buf.sp`
with MOS models from `../hspice.mod`, driven by the same ngspice PRBS
source style used for the converted IBIS benches.

Files:

- `tb_exp2_ngspice_refspice_100n_batch.sp`
  Short 100 ns validation deck for fast smoke tests.
- `tb_exp2_ngspice_refspice_batch.sp`
  Full 2 us long-run deck for apples-to-apples comparison against the
  converted IBIS long-run bench.
- `tb_validation_compare_refspice_vs_pybis_batch.sp`
  Compact 20 ns side-by-side comparison deck, modeled after SPISim's
  short validation approach, for reference-SPICE vs converted-IBIS checks.
- `tb_validation_compare_refspice_vs_pybis_rfr_batch.sp`
  Rise-fall-rise side-by-side comparison deck using the same compact
  delayed-50-ohm validation style.

Bench alignment choices:

- Supply: `3.3 V`
- Enable/OE: held high
- Channel: `../channel.sp`
- Termination: `85 ohm`
- Stimulus: `../ngspice_pybis/prbs11_ngspice.inc`

This intentionally differs from the original `tb_exp2.sp`, which uses
HSPICE-only `PWLFILE=` syntax and a `1e6 ohm` termination.

Important note:

- The transistor-level reference side is still numerically fragile in ngspice.
- Any side-by-side plot is only valid if the raw file reaches the intended stop time.
- The compare plot scripts now refuse to generate PNGs from truncated raw files.
