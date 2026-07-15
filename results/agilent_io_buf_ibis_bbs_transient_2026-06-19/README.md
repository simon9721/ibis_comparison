# Agilent Channel io_buf Transient: HSPICE IBIS vs ngspice pybis/BBS

This run compares the requested nonlinear-driver transient setup:

- HSPICE: native `io_buf.ibs` IBIS instance driving native S-parameter `Agilent_E5071B.s4p`.
- ngspice: pybis-converted `io_buf.ibs` driver driving the BBS General SPICE conversion of the same Agilent channel.

## Bench Setup

- IBIS source: `C:\Users\sh3qm\code\ibis_comparison\hspice\sparam\io_buf.ibs`
- Original channel: `C:\Users\sh3qm\code\ibis_comparison\results\agilent_e5071b_bbs_s4p_overlay_2026-06-19\artifacts\Agilent_E5071B_original.s4p`
- BBS model: `C:\Users\sh3qm\code\ibis_comparison\results\agilent_e5071b_bbs_s4p_overlay_2026-06-19\artifacts\Agilent_E5071B_GSPICE.txt`
- Port convention: `p1` driven Tx, `p3` observed RX, `p2` and `p4` unused/terminated.
- Terminations: `p2`, `p3`, and `p4` each to `75 ohms`, matching the Agilent Touchstone `R 75` reference.
- Stimulus: `0 -> 3.3 V` at `1 ns`, `3.3 -> 0 V` at `9 ns`, `5 ps` edge.
- Transient: `.tran 2p 12n`.

## Run Status

- HSPICE return code: `0`
- ngspice return code: `0`

## Plots

- `plots/01_all_overlay.png`
- `plots/02_tx_p1_overlay.png`
- `plots/03_rx_p3_overlay.png`
- `plots/04_far_terminated_p4_overlay.png`

## Metrics

| Node | RMSE V | Max Abs V | Active RMSE V | Active Max Abs V | HSPICE range V | ngspice range V |
|---|---:|---:|---:|---:|---:|---:|
| p1 | 0.752418 | 2.05777 | 0.699638 | 2.05777 | -0.0142085..3.72611 | -0.0132625..2.90308 |
| p2 | 0.00404923 | 0.0130262 | 0.00337744 | 0.00917546 | -0.045953..0.0583643 | -0.0444242..0.0525237 |
| p3 | 0.00267468 | 0.00714751 | 0.00252487 | 0.00629127 | -0.0166847..0.017039 | -0.0181117..0.0134618 |
| p4 | 0.011571 | 0.0173533 | 0.0114016 | 0.0173533 | -2.78086e-05..0.0185322 | -0.00439323..0.00399043 |
| in_dig | 3.07108e-05 | 0.00032 | 3.20307e-05 | 0.00032 | 0..3.3 | 0..3.3 |

## Artifacts

- `hspice_native_ibis_sparam/agilent_io_buf_hspice.sp`
- `hspice_native_ibis_sparam/agilent_io_buf_hspice.tr0`
- `ngspice_pybis_bbs/agilent_io_buf_ngspice.sp`
- `ngspice_pybis_bbs/agilent_io_buf_ngspice.raw`
- `ngspice_pybis_bbs/driver_OutputInput_Typical.sub`
- `ngspice_pybis_bbs/Agilent_E5071B_GSPICE.txt`
