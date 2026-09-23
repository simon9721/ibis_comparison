# Can the one stressed run choose the Ku-vs-gate shape? - findings

*2026-09-22* · script `scripts/shape_from_stressed_run.py`

## Why

Track 1 uses one universal curve shape (vt 0.5, alpha 0.7) for every buffer. Step 4 showed
that costs inv_base8 and inv_skewp 3-4 points against their measured family shape, and nothing
else much. The shape cannot come from the full swing - any monotone re-pairing of (map, gate)
reproduces it (`predriver_stages_2026-09-09`) - but the one stressed pad run is a second
observation, and today it only places the stage threshold.

Six shapes, each pad-calibrated as usual, at the netlist K, with the measured C_comp and
today's converter. `shape_grid.csv`.

## Result

| shape (vt, alpha) | inv_base8 worst peak | lag at calib | inv_skewp worst peak | lag at calib |
|---|---:|---:|---:|---:|
| **0.40, 0.60** | 9.0 % | **-5 ps** | **7.9 %** | **-3 ps** |
| 0.40, 0.90 | **8.3 %** | +9 ps | 10.3 % | +12 ps |
| 0.50, 0.70 (universal) | 10.6 % | +13 ps | 10.9 % | +15 ps |
| 0.55, 0.70 | 10.4 % | +22 ps | 10.6 % | +26 ps |
| 0.60, 0.70 | 11.2 % | +34 ps | 11.5 % | +34 ps |
| 0.50, 1.00 | 13.9 % | +31 ps | 13.2 % | +31 ps |

For reference, the measured family shape (the 3-parameter prior 0.42 / 1.15 / 0.87) gives
6.9 % on inv_base8 and 7.5 % on inv_skewp.

* **The timing selector picks a better shape.** Smallest |lag| at the calibration width - the
  same rule that picks K, and measured on the same one stressed run - chooses (0.40, 0.60) on
  both buffers: **9.0 %** and **7.9 %**, against the universal shape's 10.6 % and 10.9 %.
* That cuts the price of not probing from 3.7 to 2.1 points on inv_base8, and from 3.4 to
  0.4 points on inv_skewp.
* **The selector matters again.** Choosing by full-swing error instead would keep the
  universal shape on both buffers (its full-swing rms is the smallest: 4.7 and 7.4 mV) and
  gain nothing. The stressed peak alone would pick (0.40, 0.90) on inv_base8 - the best peak,
  but a worse lag - and (0.40, 0.60) on inv_skewp.
* The shape the timing picks is not the measured one: the family prior has vt 0.42 with a
  much steeper alpha (1.15, with saturation at 0.87). A 2-parameter shape at vt 0.40 buys most
  of the difference without matching it.

## Caveats

* Six shapes, chosen by hand around the universal default; a finer grid would risk fitting
  these two buffers rather than testing a rule.
* K was held at the netlist count, so the shape and the stage count were not selected
  together. They interact through the same observation - the pad run's timing - and a joint
  search over (K, shape) is the honest version.
* Only the two buffers the shape costs anything on. Applying it to all twelve is ~72 builds
  and would show whether the rule ever *hurts* a buffer the universal shape already suits.
