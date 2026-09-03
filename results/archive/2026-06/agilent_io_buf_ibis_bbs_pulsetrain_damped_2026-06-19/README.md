# Agilent Channel io_buf Pulse Train: HSPICE IBIS vs ngspice pybis/BBS

This is the repeated-pulse version of the Agilent channel transient comparison. It uses the same models and 75 ohm matched terminations as the single-pulse run, but drives multiple pulses so the RX response is dominated by repeated excitation instead of one isolated ring-down.

## Bench Setup

- Profile: `settled_5ns_slow500ps_src75`.
- Pulse train: `4` pulses, `5 ns` high, `5 ns` low.
- Edge rate: `500 ps`.
- Source series resistor: `75 ohms` between the IBIS output and channel p1.
- Terminations: `p2`, `p3`, and `p4` each to `75 ohms`, matching the Agilent Touchstone `R 75` reference.
- Port convention: `p1` driven Tx, `p3` observed RX, `p2` and `p4` unused/terminated.
- Transient: `.tran 2p 4.4e-08`.

## Run Status

- HSPICE return code: `0`
- ngspice return code: `0`

## Plots

- `plots/01_all_pulsetrain_overlay.png`
- `plots/02_all_pulsetrain_zoom.png`
- `plots/03_tx_p1_zoom.png`
- `plots/04_rx_p3_zoom.png`

## Metrics

| Node | Active RMSE V | Active Max Abs V | Steady RMSE V | Steady Max Abs V | HSPICE range V | ngspice range V |
|---|---:|---:|---:|---:|---:|---:|
| p1 | 1.06064 | 2.81098 | 1.29496 | 2.79294 | -0.170843..3.73265 | -0.0648608..2.38946 |
| p2 | 0.0435518 | 0.140771 | 0.0424171 | 0.134915 | -0.114215..0.126294 | -0.0555373..0.0566654 |
| p3 | 0.0229111 | 0.0791461 | 0.0234664 | 0.078369 | -0.0521654..0.0539863 | -0.0254607..0.0266904 |
| p4 | 0.0107371 | 0.0179882 | 0.0127717 | 0.0176364 | -0.0134545..0.0173909 | -0.0106473..0.0105465 |
| in_dig | 5.20062e-06 | 3.24e-05 | 7.01237e-06 | 3.17e-05 | 0..3.3 | 0..3.3 |

## Interpretation

This does not remove the channel's natural decay; it keeps exciting the channel before the previous response fully dies out. That makes the overlay easier to compare for repeated digital activity, but it is still a band-pass/coupled channel response rather than a DC-settling digital through path.
