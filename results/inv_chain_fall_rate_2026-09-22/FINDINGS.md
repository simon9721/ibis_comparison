# Can the chain's gate be made to fall faster? - findings

*2026-09-22* · script `scripts/inv_chain_fall_rate.py` · follows
`results/inv_chain_single_curve_2026-09-22/`

## Why

inv_chain's modelled gate reaches the right height, peaks ~45 ps late and stays up 10-20 ps
too long; the surplus charge is its 26 % pad overshoot. The stage law's one knob for the
discharge direction is `--dn-ratio R`: the discharge `x_lin` becomes `x_lin * R`, so a smaller
R saturates the pull-down current nearer the rail and should sharpen the tail. `s_dn` and
`x_lin` are refitted at each R against the same full-swing Ku(t), so a ratio that helps the
stressed fall *and* keeps the full-swing rms is a gain rather than a trade.

## Result

inv_chain, K = 7, C_comp 0.60, family shape, calibrated on the 104 ps pad run as always.
`fall_rate.csv`.

| dn-ratio | worst peak | peaks, 135 / 119 / 111 / 106 / 104 ps | gate area excess | full swing |
|---:|---:|---|---|---:|
| 0.3 | 20.2 % | +4.2 / +11.3 / +19.9 / +20.2 / -0.8 | +19 / +27 / +31 / +19 / -4 % | 84.7 mV |
| **0.5** | **23.2 %** | +2.7 / +8.8 / +18.2 / +23.2 / +0.8 | +5 / +13 / +20 / +15 / -9 % | **52.6 mV** |
| 1.0 (as built) | 25.8 % | +3.0 / +9.6 / +19.2 / +25.8 / +4.1 | +7 / +15 / +22 / +19 / -6 % | 54.0 mV |
| 2.0 | 27.2 % | +3.8 / +11.0 / +20.8 / +27.2 / +11.8 | +14 / +23 / +30 / +25 / +4 % | 64.5 mV |

* **The direction is right and the size is small.** R = 0.5 is better than the default on both
  the stressed peak (23.2 against 25.8 %) and the full swing (52.6 against 54.0 mV) - free, but
  2.6 points.
* R = 0.3 buys 5.6 points and costs 31 mV of full swing. That is the trade the single knob
  makes: past a point it sharpens the stressed fall by distorting the fitted one.
* **It is not enough.** The best of these is 20.2 %, against a ±10 % target.
* Across ratios the gate area no longer tracks the peak (R = 0.3 has the largest areas and the
  smallest peak) because refitting moves `s_up` and `s_dn` too, and with them the gate's
  arrival. Within one build, across widths, the area rule still holds.

## What this says about the stage law

One discharge knob cannot give the chain a gate that arrives on time, reaches the right
height, and comes back quickly, while the full swing pins `s_dn`. The 09-10 train round
reached the same conclusion from the other side (peak and lag could not both be met by
`x_lin`). The degree of freedom that is missing is a **stage that is not identical to the
others** - most plausibly the last one, which drives the output gate and sets its fall.
`fit_chain` (per-stage numbers) already exists next to `fit_chain_shared`; making the final
stage's four numbers free, fitted against the same full-swing Ku(t), is the next test, and it
is a change to the model rather than another measurement.
