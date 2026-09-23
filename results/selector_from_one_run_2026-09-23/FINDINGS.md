# A better selector from the same one stressed run - findings

*2026-09-23* · script `scripts/selector_from_one_run.py` · re-analysis of step 8's builds, no
new simulation

## Why

Step 8 chooses (K, shape) by the **alignment of the pad's falling leg** at the calibration
width - one number out of a whole measured waveform. Its grid holds builds at 1.2-4.2 % on
nine buffers and the timing finds them on two, so what loses those points is the selector, not
the model.

A user has the IBIS file and one stressed pad run, so a selector may use any feature of **that
one waveform** - but nothing from the other widths, which are the score. Three candidates:

| selector | what it reads |
|---|---|
| timing | \|lag\| of the falling leg (step 8's rule) |
| **pad rms** | rms between model and transistor pad over that pulse and its return |
| rms + peak gate | the same rms, after dropping builds whose calibration-width peak is off by more than 2 % |

## Result: the whole waveform gets 12 of 12

| buffer | by timing | by pad rms | best in the grid |
|---|---|---|---|
| ex2 | K3 0.5/0.7, 8.3 % | K3 0.5/0.7, 8.3 % | K5 0.5/0.7, 2.3 % |
| ex2_base | K3, 7.0 % | K3, 7.0 % | K4, 2.2 % |
| ex2_slowpre | K3, 5.4 % | K3, 5.4 % | K4, 2.5 % |
| ex2_skewp | K3, 10.0 % | K3, 10.0 % | K4 0.4/0.9, 1.2 % |
| **ex2_weak** | K3 0.4/0.9, **10.7 %** | K3 0.5/0.7, **8.7 %** | K5 0.4/0.6, 1.9 % |
| ex2_nomiller | K3, 7.2 % | K3, 7.2 % | K4, 1.9 % |
| inv_chain | K6 0.4/0.9, 5.1 % | K6 0.4/0.9, 5.1 % | the same, 5.1 % |
| inv_base8 | K7 0.4/0.6, 8.4 % | K7 0.4/0.6, 8.4 % | K5 0.5/0.7, 2.4 % |
| inv_stage4 | K3 0.4/0.9, 3.2 % | K3 0.4/0.9, 3.2 % | K3 0.4/0.6, 2.9 % |
| inv_skewp | K7 0.4/0.6, 8.1 % | K7 0.4/0.6, 8.1 % | K6 0.5/0.7, 4.2 % |
| inv_weak | K7 0.4/0.6, 4.1 % | K7 0.4/0.6, 4.1 % | K6 0.5/0.7, 1.9 % |
| **io_buf** | K1 0.4/0.9, 6.1 % | K1 0.5/0.7, **7.7 %** | K1 0.4/0.9, 6.1 % |
| | **11 of 12**, mean 7.0 | **12 of 12**, mean 6.9 | 12 of 12, mean 2.9 |

* **12 of 12 within ±10 %**, the first time the file-only recipe covers every buffer. The two
  selectors agree on ten; the rms rule rescues ex2_weak (10.7 -> 8.7 %) and gives up 1.6 points
  on io_buf.
* **Gating on the calibration-width peak changes nothing** - the calibration matches that peak
  almost everywhere, which is why the peak was useless as a selector in step 2. The information
  is in the rest of the waveform, not its height.
* A bonus on io_buf: the rms rule picks 0.5/0.7, avoiding the 0.4/0.9 build that the timing
  rule picks and that **ngspice cannot simulate on a train**
  (`results/train_check_today_2026-09-23/`).
* The oracle - the best pair in the grid, which needs the answer - averages 2.9 % on the peak.
  **That headroom is not real** (corrected after first writing this): those builds win the peak
  by arriving late with a badly wrong waveform.

| buffer | rms pick: lag / pad rms | best-by-peak: lag / pad rms |
|---|---|---|
| ex2 | -7 ps / 56 mV | **+300 ps / 400 mV** |
| ex2_base | -2 ps / 64 mV | +207 ps / 238 mV |
| ex2_slowpre | +8 ps / 36 mV | +300 ps / 313 mV |
| ex2_skewp | -27 ps / 61 mV | +155 ps / 99 mV |
| ex2_weak | +17 ps / 40 mV | +300 ps / 204 mV |
| ex2_nomiller | -11 ps / 59 mV | +204 ps / 238 mV |
| inv_base8 | -9 ps / 21 mV | -58 ps / 142 mV |
| inv_skewp | -8 ps / 15 mV | -25 ps / 58 mV |

  The score here is the worst stressed **peak**, and a chain that turns on late can hit the
  peak while getting the pulse wrong - the same trap step 2 found when the peak alone chose K.
  So the rms selector is not giving up 4 points; it is declining a bad trade, and the gap to
  the oracle is mostly an artifact of scoring peaks. A fairer target would score the waveform
  at every width, not its height.

## What it does not say

The grid is three shapes and three stage counts, chosen earlier; a selector that is better on
this grid is not necessarily better on a finer one. And the rms window (the pulse and 1.5 ns
of its return) was picked once, not tuned - which is deliberate, but it means the rule has one
free choice in it that nobody has tested.
