# Overnight, 2026-09-22 into 09-23

Written for Simon to read first thing. Figures in this folder; each claim links the study that
made it. Nothing here is pushed; nine commits on
`iobuf-calibration-and-native-anchored-sweep`.

## The headline

**A model built from the IBIS file and one stressed pad run now holds 12 of 12 buffers within
±10 %, and on inv_chain it beats the model built from probed silicon.**

The last point came free: selecting the stage count and curve shape on the **whole** pad
waveform of that one run, rather than on the alignment of its falling leg, takes the recipe
from 11 of 12 to 12 of 12 (mean 6.9 %) with no new simulation
(`selector_from_one_run_2026-09-23`). The best pairs in the same grid average 2.9 %, so the
selector is still the limiting part, not the model.

The recipe reads four things from the file plus one measurement:

| what | where it comes from | study |
|---|---|---|
| C_comp | the file's own Ku overshoot knee - Ku cannot exceed 1, so the file rejects an impossible value | `ccomp_from_file_2026-09-22` |
| stage count K | fit K = 1...10 to that model's Ku(t), build the band, keep the K whose **pad timing** matches | `stage_count_from_file_2026-09-21` step 6 |
| curve shape | chosen with K, from the same timing | step 8 |
| stage threshold | calibrated on the same stressed run | (existing) |

`endtoend.png` is the per-buffer picture; the shipped IBIS model is at 35-70 % on the same
pulses where ours is at 5-10 %.

## What changed tonight

* **inv_chain, 34 % -> 5.1 %.** Its failure was the **map shape**, not the discharge: the IBIS
  tables pin only the product Ku(t), and with one universal shape the implied gate was square
  where the real gate rolls off with pulse width. Choosing the shape and K together from the
  one pad run fixes it, and improves its full swing too (54 -> 36 mV). This file-only build
  beats the track-1 build (25.8 %), which uses the measured C_comp, the measured shape and the
  netlist stage count.
* **A correction you should know about.** inv_chain's older 7 % numbers were wrong: the models
  they used carried the converter's old input threshold (1.4 V, from the 2 V Vinh its IBIS
  declares on a 1.8 V part), which masks its error threefold. Rebuilt on today's converter it
  is 25.8 %, and the 12-of-12 baseline is really 11 of 12. Only inv_chain moved; every other
  buffer is identical to the decimal.
* **io_buf is not the well-behaved buffer** - only its pull-up is. On short-LOW pulses it is
  16-21 points too shallow, and the reason is structural: its pull-down chain never turns on
  at all (each stage must drag the next past 0.7 of the swing, so a 163-322 ps pulse dies in
  the first or second stage, and GDN never rises). The dip the model makes is just the pull-up
  releasing into the load. What sets the depth is the **pull-up's turn-off**: scaling that by
  1.2 takes the worst error from 21.3 to 8.9 points. `io_buf_pulldown.png`.
* **The train is where we still lose.** On a stressed 8-pulse train the *shipped* model beats
  ours on ex2 (-3.8 against -9.5 / -19.1 %) and io_buf (-2.0 against +4.7 / +6.6 %); only
  inv_chain's track-1 build wins. Everything tonight optimised the single-pulse regime.
* **But the train carries C_comp**: its settled error is monotone in C_comp at about -5 % per
  pF on ex2, where the single-pulse peak is nearly blind to it. A stressed train is the
  obvious second characterisation point - though no C_comp zeroes the train error, so there is
  a deficit underneath it.

## Two negative results worth keeping

* **A free final stage does not help from the file.** Giving the chain's last stage its own
  discharge rate improves the stressed pad by hand (25.8 -> 16.6 %) and the full swing with it,
  but when the scale is *fitted* against the full-swing Ku(t) the fit chooses 1.0 - the full
  swing cannot see it. Another parameter only a stressed observation can select.
* **The timing selector is loose.** The step-8 grid contains builds at 1.2-4.2 % on nine
  buffers; timing picks them on two. It is what makes K identifiable at all, but it is a proxy
  for the peak, and ex2_weak got worse (8.7 -> 10.7 %) when the shape search followed it.

## Where I would go next

1. **A better selector.** Timing alone leaves 1-6 points on the table on most buffers. Using
   timing and peak together over the (K, shape) grid is cheap - the builds already exist.
2. **The train as the second characterisation point**, to pin C_comp and the recovery the
   single pulse cannot see.
3. **io_buf's pull-down**, which needs its own stressed point and a chain that a short pulse
   can actually propagate through.

## The studies

| folder | what it settles |
|---|---|
| `stage_count_from_file_2026-09-21` | steps 1-8: K from the file, C_comp, shape, the end-to-end recipe |
| `ccomp_from_file_2026-09-22` | C_comp from the Ku overshoot |
| `inv_chain_single_curve_2026-09-22` | the handoff between the two Ku curves is a third of inv_chain's old error |
| `inv_chain_fall_rate_2026-09-22` | the discharge knob is worth 2-6 points |
| `inv_chain_last_stage_2026-09-22` | a faster final stage helps, but the fit will not choose it |
| `io_buf_pulldown_depth_2026-09-22` | Kd is unidentifiable; the pull-down direction is 16-21 points shallow |
| `io_buf_pulldown_calib_2026-09-23` | why: the pull-down chain is inert; the pull-up's turn-off is the knob |
| `train_check_today_2026-09-23` | the train, where the shipped model still wins |
