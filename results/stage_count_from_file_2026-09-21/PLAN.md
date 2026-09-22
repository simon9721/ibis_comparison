# Can track 1 find the predriver stage count from the IBIS file?

*2026-09-21* · script `scripts/stage_count_from_file.py` · results in this folder

## Why

After the 09-18 meeting the focus is track 1: build the model from what an IBIS file holds,
plus one stressed pad run, with no internal probing. Track 1 models the predriver as K
identical current-limited stages. **Every track-1 result so far was handed K**:

| buffer | real predriver stages (netlist) | K the track-1 build used | how |
|---|---:|---:|---|
| ex2 and its 5 variants | 3 (in -> n2 -> n3 -> n4) | 3 | `--K 3` |
| inv_chain, inv_base8, inv_skewp, inv_weak | 7 (VIN -> VOUT1 ... VOUT7) | 7 | `--K 7` |
| inv_stage4 | **3** (VIN -> VOUT1 -> VOUT2 -> VOUT3) | **4** (also 5, 7 tried) | `--K 4` |
| io_buf pull-up | 1 (NAND to n2) | 1 | picked from the shortlist {1, 2, 3} |
| io_buf pull-down | 3 (INV -> NAND -> INV to n3) | 3 | picked from the shortlist {1, 2, 3} |

Where K was not given it was picked from a per-family shortlist (`FAMILY_KS` in
`build_chain_model.py`: ex2 {2, 3, 4}, inv {5, 7, 9}, io_buf {1, 2, 3}) written knowing the
netlists. The 09-10 finding "the stage count is recoverable from full swing alone" (rms plateau
at 3 and 7) was made by fitting the **probed** gate, not the file.

## Questions

1. **Can the file tell K?** Fit K = 1 ... 10 identical stages to the file's own full-swing Ku(t)
   (the file-only fit, `fit_chain_ku`) and take the smallest K on the rms plateau (within 5 % of
   the best, the existing `pick_K` rule). Does it land on the netlist count, with no shortlist?
2. **Does a wrong K matter** once the threshold is placed by the one stressed pad run? Build and
   score the picked K, K - 1, K + 1 and the netlist K.

## Method

Everything held at each buffer's existing track-1 settings, only K varied:

| buffer | C_comp (pF) | Ku-vs-gate curve shape | stage resistive fraction | pad calibration |
|---|---:|---|---|---|
| ex2 | 1.7 | prior 0.57 / 0.64 | 0.45 | 810 ps |
| ex2 variants | 1.7 | prior 0.57 / 0.64 | 0.45 | 50 % depth |
| inv_chain | 0.6 | prior 0.49 / 0.60 | free | 104 ps |
| inv_base8, inv_stage4 | 0.6 | prior3 0.42 / 1.15 / 0.87 | 0.45 | 50 % depth |
| inv_skewp, inv_weak | 0.4, 0.3 | prior3 0.42 / 1.15 / 0.87 | 0.45 | 50 % depth |
| io_buf | declared | prior 0.50 / 0.78 | free | 1505 ps |

**Step 1 (Python only).** For each buffer, fit K = 1 ... 10 in the Ku domain; record the rms
curve and the picked K (io_buf: the pull-up and the pull-down chain separately). A second pass
repeats it **strictly file-only**: the declared C_comp and one universal curve shape (vt 0.5,
alpha 0.7) for every buffer, resistive fraction 0.45 - because the settings above carry two
other inputs that are not in the file (see below).

**Step 2 (ngspice).** ~~For each buffer, build with the pick from K = 1 ... 10, with K - 1 and
K + 1, and with the netlist K where different.~~ *Changed after step 1 (09-21 16:50): the picks
were scattered, so step 2 sweeps one range per family that covers every pick and the netlist
count - ex2 family K 2...7, the 7-stage inverter chains K 5...10, inv_stage4 K 2...6, io_buf
pull-up 1 with pull-down 2...5 (`--Kd`, added to `gate_chain_prototype.py`) - 69 builds.* Each
is calibrated on the one stressed pad run and scored on the five stressed widths (peak error,
lag) and the full swing, at the buffer's track-1 settings.

**Step 3 (added 09-21 evening, after step 2).** Step 2 again, strictly file-only: the C_comp
declared in each IBIS file and one universal curve shape (vt 0.5, alpha 0.7) for every
buffer. Everything else as step 2 - the same K ranges, resistive fraction, and calibration
width. The shipped models are generated from the IBIS files into `file_only_models/`. Questions:
does track 1 still reach the track-1 error band without the two non-file inputs, and does the
timing of the one pad run still pick K?

## Two other non-file inputs, noted and not tested here

* **C_comp.** The track-1 builds use the loop-measured C_comp (ex2 1.7 pF against the
  declared 5.0). The loop method needs the probed gate.
* **The curve shape.** The priors above were fitted to each family's measured Ku-vs-gate curve;
  `build_chain_model.py --family` selects them by family, which is itself a label.

Step 1's strictly-file-only pass shows whether the K pick survives without them; their effect
on the pad is a separate study.

### Step 4 (added 09-22): which of the two costs the accuracy

Step 3 removed both at once, and the ex2 family went from 12/12 within ±10 % to 13-20 % low.
Step 4 changes one at a time, at each buffer's netlist K, pad-calibrated and scored as in
steps 2 and 3:

| pass | C_comp | curve shape |
|---|---|---|
| step 2 (done) | loop-measured | family |
| **4a** | declared in the file | family |
| **4b** | loop-measured | universal (vt 0.5, alpha 0.7) |
| step 3 (done) | declared in the file | universal |

22 builds; io_buf needs none, its C_comp is the declared one in every pass (4a = its step 2,
4b = its step 3). Expected from step 3's reading: 4a carries most of the loss on the ex2
family (declared 5 pF inflates the file Ku to 1.23-1.74), 4b little. If 4b also loses, the
family shape is a second hidden input.

## What counts as an answer

* Q1 yes: the full-range pick equals the netlist count on the 12 buffers (both passes).
* Q2: the spread of the five-width peak error across K - 1 / K / K + 1 after pad calibration;
  "K does not matter" if it stays within the track-1 error band (±10 %) on every buffer.
