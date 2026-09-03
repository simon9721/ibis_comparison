# Agilent Channel io_buf Pulse Train: HSPICE IBIS vs ngspice pybis/BBS

This is the repeated-pulse version of the Agilent channel transient comparison. It uses the same models and 75 ohm matched terminations as the single-pulse run, but drives a 10-pulse train so the RX response is dominated by repeated excitation instead of isolated ring-down.

## Bench Setup

- Pulse train: `10` pulses, `1 ns` high, `1 ns` low.
- Edge rate: `5 ps`.
- Terminations: `p2`, `p3`, and `p4` each to `75 ohms`, matching the Agilent Touchstone `R 75` reference.
- Port convention: `p1` driven Tx, `p3` observed RX, `p2` and `p4` unused/terminated.
- Transient: `.tran 2p 2.4e-08`.

## Run Status

- HSPICE return code: `0`
- ngspice return code: `0`

## Plots

- `plots/01_all_pulsetrain_overlay.png`
- `plots/02_all_pulsetrain_zoom_15_22ns.png`
- `plots/03_tx_p1_zoom_15_22ns.png`
- `plots/04_rx_p3_zoom_15_22ns.png`

## Metrics

| Node | Active RMSE V | Active Max Abs V | Steady RMSE V | Steady Max Abs V | HSPICE range V | ngspice range V |
|---|---:|---:|---:|---:|---:|---:|
| p1 | 0.772113 | 2.76529 | 0.894515 | 2.76529 | -0.0334077..0.33091 | -0.181176..2.89254 |
| p2 | 0.187714 | 0.43132 | 0.214187 | 0.43132 | -0.0589921..0.0710519 | -0.36446..0.346512 |
| p3 | 0.0720009 | 0.142048 | 0.075467 | 0.12646 | -0.0187484..0.0186662 | -0.134403..0.128011 |
| p4 | 0.0641933 | 0.125237 | 0.0667651 | 0.118832 | -0.0201513..0.0210816 | -0.131841..0.137423 |
| in_dig | 0.00037084 | 0.003267 | 0.000435805 | 0.0032422 | 0..3.3 | 0..3.3 |

## Interpretation

This does not remove the channel's natural decay; it keeps exciting the channel before the previous response fully dies out. That makes the overlay easier to compare for repeated digital activity, but it is still a band-pass/coupled channel response rather than a DC-settling digital through path.
