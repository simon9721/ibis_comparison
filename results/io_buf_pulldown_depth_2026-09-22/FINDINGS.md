# io_buf's pull-down: does its chain depth matter, and does the model track it? - findings

*2026-09-22* · script `scripts/io_buf_pulldown_depth.py`

## Why

Step 2 of the stage-count study swept io_buf's pull-down chain over Kd = 2...5 and found the
scores identical to 0.1 % and 1 ps - but every case there was a short-HIGH pulse, whose
falling leg barely exercises the pull-down path. The 08-14 loaded-swing sweep already selected
five short-LOW widths for io_buf and ran the transistor at each, so the question could be
asked without any new HSPICE.

Both sides are measured the same way: the extremum of the dip against that model's own
long-pulse swing. Our full swing in this direction is 1.547 V against the transistor's
1.553 V - 0.4 % apart - so the comparison is about stress, not calibration.

## 1. The pull-down chain depth is unidentifiable, not merely unexercised

| width (ps) | 163 | 191 | 220 | 223 | 256 | 307 | 322 |
|---|---|---|---|---|---|---|---|
| spread of the pad minimum across Kd = 2, 3, 4, 5 (V) | 0.0001 | 0.0001 | 0.0001 | 0.0004 | 0.0001 | 0.0002 | 0.0001 |

Four different pull-down chain depths put the pad within **0.4 mV** of each other on the very
pulses that drive it hardest. So Kd cannot be read from the pad in either direction: it is not
a parameter the recipe has to get right, and the step-2 result was not an artifact of the
short-high cases.

## 2. But the pull-down direction is 16-21 points too shallow

| width (ps) | 163 | 191 | 220 | 223 | 256 | 307 | 322 |
|---|---:|---:|---:|---:|---:|---:|---:|
| transistor depth (% of full swing) | 47.5 | 58.5 | 68.3 | 69.4 | 78.8 | 89.6 | 91.8 |
| our depth | 31.1 | 38.5 | 47.0 | 48.2 | 60.7 | 84.2 | 89.0 |
| **error (points)** | **-16.4** | **-19.9** | **-21.3** | **-21.2** | **-18.1** | **-5.4** | **-2.8** |

The model under-drives the pull-down badly on a short pulse and converges only as the pulse
gets long enough to finish. This is the **opposite sign** to everything measured on the
short-high side, where io_buf's error is +7.7 % (too much), and it is on the buffer that has
looked the best of the twelve.

Nothing in the track-1 work touched this: the recipe's one characterisation point is a
short-HIGH pulse (1505 ps), and its threshold calibration places the pull-up chain. The
pull-down chain gets the same universal shape and no calibration point of its own.

## What to do with it

* Kd needs no attention. Fix it at 1 stage or at the pull-up's count; the pad cannot tell.
* The pull-down path needs its own characterisation point - a short-LOW pulse - if this
  direction is to be within ±10 %. That is a second stressed run, and the recipe currently
  claims one. Whether one short-low run fixes the direction, or whether the pull-down map
  itself is wrong, is untested.
* The decks and the summary tables describe io_buf as the well-behaved buffer. That is true
  only of its pull-up direction.
