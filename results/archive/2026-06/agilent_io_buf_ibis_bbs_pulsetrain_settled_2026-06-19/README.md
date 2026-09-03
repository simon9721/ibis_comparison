# Agilent Channel io_buf Pulse Train: HSPICE IBIS vs ngspice pybis/BBS

This is the repeated-pulse version of the Agilent channel transient comparison. It uses the same models and 75 ohm matched terminations as the single-pulse run, but drives multiple pulses so the RX response is dominated by repeated excitation instead of one isolated ring-down.

## Bench Setup

- Profile: `settled_5ns`.
- Pulse train: `4` pulses, `5 ns` high, `5 ns` low.
- Edge rate: `5 ps`.
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
| p1 | 0.725618 | 2.17395 | 0.85865 | 2.17395 | -0.450685..3.74583 | -0.190899..2.90894 |
| p2 | 0.0447436 | 0.136707 | 0.0486496 | 0.136707 | -0.200038..0.211701 | -0.0878684..0.0846045 |
| p3 | 0.0139982 | 0.050648 | 0.016101 | 0.050648 | -0.058844..0.0615836 | -0.0321182..0.0329488 |
| p4 | 0.0111273 | 0.0230874 | 0.0130897 | 0.0217212 | -0.012745..0.020847 | -0.013366..0.0132273 |
| in_dig | 0.000216886 | 0.0032283 | 0.00035918 | 0.0032283 | 0..3.3 | 0..3.3 |

## Interpretation

This does not remove the channel's natural decay; it keeps exciting the channel before the previous response fully dies out. That makes the overlay easier to compare for repeated digital activity, but it is still a band-pass/coupled channel response rather than a DC-settling digital through path.
