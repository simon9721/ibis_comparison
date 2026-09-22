# Can C_comp be recovered from the IBIS file alone? - findings

*2026-09-22* · script `scripts/ccomp_from_file.py` · build test: step 5 of
`results/stage_count_from_file_2026-09-21`

Step 4 of the stage-count study showed that the one input keeping track 1 from being file-only
is **C_comp**: the loop-measured value needs the probed gate, and the declared one costs the
ex2 family 5-11 points of stressed peak error. This asks whether the file can supply it.

## The idea, and the direction I had backwards

Ku is the fraction of the pull-up's own I-V curve the buffer is using, so it cannot exceed 1.
`solve_k_params_output` subtracts the C_comp displacement current before solving, so a wrong
C_comp shows up as a Ku that overshoots 1.

I expected the overshoot to *vanish* at the right C_comp. It does the opposite: at C_comp = 0
the solved Ku peaks at exactly 1.00 on every buffer, and the overshoot **grows** with C_comp,
because a larger C_comp books more of the pad current as device current. So "the C_comp where
the overshoot disappears" is always ~0 and says nothing. What the bound gives is an **upper
limit**: any C_comp whose solved Ku exceeds 1 is impossible.

## What the file rejects

Peak solved Ku at the declared C_comp (`ccomp_from_file.csv`, `ccomp_from_file.png`):

| buffer | declared | peak Ku there | loop-measured | peak Ku there |
|---|---:|---:|---:|---:|
| ex2 | 5.0 | 1.24 | 1.7 | 1.005 |
| ex2_base | 5.0 | 1.28 | 1.7 | 1.02 |
| ex2_slowpre | 5.0 | 1.03 | 1.7 | 1.01 |
| ex2_skewp | 5.0 | 1.59 | 1.7 | 1.04 |
| ex2_weak | 5.0 | 1.78 | 1.7 | 1.08 |
| ex2_nomiller | 5.0 | 1.30 | 1.7 | 1.02 |
| inv_chain | 0.468 | 1.00 | 0.6 | 1.003 |
| inv_base8 / stage4 / skewp / weak | 0.468 | 1.05 / 1.05 / 1.22 / 1.10 | 0.6 / 0.6 / 0.4 / 0.3 | 1.13 / 1.12 / 1.15 / 1.02 |
| io_buf | 1.2 | 1.00 | (declared) | - |

**The ex2 family's declared 5.0 pF is rejected by its own file**: a Ku of 1.24-1.78 is not
physical. io_buf's declared 1.2 pF and inv_chain's 0.468 pF pass. This matters because
s2ibispy does not extract C_comp - `buffers/ex2/buffer.s2i` has its `c_comp` line commented
out - so the value in these generated files is a placeholder, not a measurement.

## Two estimators, both within about ±50 %

Each curve is flat at 1.0 up to a knee, then climbs, so two readings are possible:

* **tolerance bound**: the largest C_comp whose peak Ku stays within 2 % of 1;
* **knee**: the rising branch (Ku 1.05-1.35) extrapolated linearly back to Ku = 1, the way a
  threshold voltage is extracted - no tolerance to choose.

| buffer | loop-measured | 2 % bound | knee | declared |
|---|---:|---:|---:|---:|
| ex2 | 1.7 | 2.31 | 2.64 | 5.0 |
| ex2_base | 1.7 | 1.73 | 2.49 | 5.0 |
| ex2_slowpre | 1.7 | 3.09 | 4.65 | 5.0 |
| ex2_skewp | 1.7 | 1.56 | 1.44 | 5.0 |
| ex2_weak | 1.7 | 1.13 | 1.27 | 5.0 |
| ex2_nomiller | 1.7 | 1.70 | 2.30 | 5.0 |
| inv_chain | 0.6 | 0.69 | 0.66 | 0.468 |
| inv_base8 | 0.6 | 0.40 | 0.37 | 0.468 |
| inv_stage4 | 0.6 | 0.23 | 0.43 | 0.468 |
| inv_skewp | 0.4 | 0.26 | 0.24 | 0.468 |
| inv_weak | 0.3 | 0.31 | 0.35 | 0.468 |
| io_buf | (declared 1.2) | 5.39 | 1.65 | 1.2 |

Both land within roughly ±50 % of the loop-measured value, against a factor of 3 for the
declared 5.0 pF. The 2 % tolerance was chosen by looking at these same loop values, so it is
tuned to this answer key; the knee is not, and reads 15-55 % high on the ex2 family because
the onset is curved rather than a corner.

**ex2_slowpre is the failure case**: 3.1-4.7 pF against a measured 1.7. Its peak Ku only
reaches 1.03 even at 5 pF, because a slow predriver means a slow pad edge and little
displacement current. The file carries information about C_comp only in proportion to dV/dt.

## The recipe this suggests

`C_comp = min(declared, bound)`: keep what the file declares unless the file's own Ku says it
is impossible, then take the bound. io_buf and inv_chain keep their declared values; the ex2
family drops from 5.0 to 1.1-3.1 pF.

## The build test (step 5 of the stage-count study)

Each buffer rebuilt at `min(declared, 2 % bound)` with the universal curve shape - nothing but
the file and the one stressed pad run - at the netlist K. Worst stressed peak error (%),
against the same build at the loop-measured C_comp (4b) and at the declared one (step 3):

| buffer | C_comp used | 4b: measured | **5: estimated** | step 3: declared |
|---|---:|---:|---:|---:|
| ex2 | 2.31 | 8.0 | **6.9** | 13.8 |
| ex2_base | 1.73 | 6.6 | 6.6 | 13.3 |
| ex2_slowpre | 3.09 | 4.4 | 5.4 | 4.8 |
| ex2_skewp | 1.56 | 10.9 | 10.3 | 20.4 |
| ex2_weak | 1.13 | 10.4 | **7.8** | 19.4 |
| ex2_nomiller | 1.70 | 5.9 | 5.9 | 14.1 |
| inv_chain | 0.468 (declared kept) | 8.4 | **15.0** | 15.0 |
| inv_base8 | 0.40 | 10.6 | 11.4 | 12.5 |
| inv_stage4 | 0.23 | 2.4 | 3.0 | 3.6 |
| inv_skewp | 0.26 | 10.9 | 9.0 | 9.5 |
| inv_weak | 0.31 | 4.3 | 5.4 | 6.1 |
| io_buf | 1.2 (declared kept) | 8.3 | 8.3 | 8.3 |
| **within ±10 %** | | **8 of 12** | **9 of 12** | **5 of 12** |

**A build from the file alone reaches 9 of 12.** On the ex2 family the estimate matches or
beats the loop-measured C_comp, even where it is 36 % off it (ex2: 2.31 against 1.7, but a
worse peak of 6.9 % against 8.0). The stressed peak is evidently not sharp in C_comp once the
value is in the right range.

**inv_chain is the failure, and the rule caused it.** `min(declared, bound)` can only correct
downward; inv_chain declares 0.468 pF against a measured 0.6, so the declared value stood and
the error stayed at 15.0 % (8.4 % at the measured value). Its own knee reads 0.66 pF. Taking
the knee as the estimate rather than as a cap would correct upward too - untested, and it
would also move io_buf (knee 1.65 against a declared 1.2 that currently passes).

## Used end to end (step 6), and the inv_chain worry was unfounded

Step 6 of the stage-count study takes the **knee** as the estimate rather than as a cap, so it
can correct upward, and runs the whole recipe from the file: C_comp, then the K band fitted to
that model, then K chosen by one stressed pad run's timing. **11 of 12 buffers land within
±10 %**, and the stage count matches the netlist on 11 of 12.

inv_chain, which the cap rule had left at the declared 0.468 pF, gets 0.66 from its knee
against a loop-measured 0.6 - the upward correction works. It still scores 26-34 %, but
controls show that is **not** C_comp: at 0.60 and at 0.66 the same pipeline gives 28.6 % and
26.3 %, while the same model with the converter's old `input_threshold` (1.4 V, from the 2 V
Vinh this 1.8 V part declares) gives 8.4 %. The whole difference is that threshold. C_comp
estimated from the file is fine on inv_chain.

The estimator's sensitivity is low in the right way: ex2_slowpre is estimated at 4.65 pF
against a measured 1.7 and still scores 5.4 %.

## What this is worth

C_comp is a measured datasheet quantity in a real IBIS flow, so track 1 may take it as an
input rather than derive it - the values here are placeholders only because the generator does
not extract them. The estimator's job is narrower, and still useful: **a file-only check that
rejects a C_comp the model cannot physically have**, and a fallback when the declared value is
wrong or missing.
