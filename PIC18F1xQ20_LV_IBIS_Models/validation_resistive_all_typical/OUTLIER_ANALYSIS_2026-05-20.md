# PIC18F1xQ20 Outlier Analysis

This note summarizes the repeated outliers from the full `50 ohm` resistive validation of the converted
`InputDriven` models against each model's own `R_fixture=50`, `V_fixture=0` IBIS waveform pair.

Source summary files:

- `validation_summary.csv`
- `validation_summary.md`

## Core finding

The same outlier model families repeat across all 4 package files (`pdip20`, `soic20`, `ssop20`, `vqfn20`).
That means the dominant effect is model behavior, not package parasitics.

Examples:

- `ptc_i3c_std` is ranks `1-4` across the four packages.
- `io_vrefh10_slctrl` and `io_vrefh10_std` follow immediately after, again across all packages.
- `io_zxover_std` and `io_vrefh5_std` are the next repeated families.

## Broad pattern: slower families fit better

Grouping by suffix shows a clear trend:

- `slctrl`: mean rise RMS `0.0062 V`, mean fall RMS `0.0239 V`
- `std`: mean rise RMS `0.0347 V`, mean fall RMS `0.0339 V`
- `slctrl_fmp`: mean rise RMS `0.0013 V`, mean fall RMS `0.0136 V`
- `std_fmp`: mean rise RMS `0.0088 V`, mean fall RMS `0.0164 V`

So the converter is consistently happier with slower / slew-controlled families than with faster `std` families.

## Outlier regime 1: `ptc_i3c_std`

This is the only severe outlier family.

Observed behavior:

- rise RMS error about `0.208-0.211 V`
- fall RMS error about `0.167-0.170 V`
- rise timing late by about `+7.3 ns`
- fall timing early by about `-5.8 ns`

Repeated across all packages:

- `PIC18F1xQ20_pdip20_LV`
- `PIC18F1xQ20_soic20_LV`
- `PIC18F1xQ20_ssop20_LV`
- `PIC18F1xQ20_vqfn20_LV`

Useful metadata from the IBIS model:

- `model_type = I/O`
- `enable = Active-High`
- `C_comp ~= 13.62 pF`
- `R_fixture=50`, `V_fixture=0` rising waveform ends at about `1.603 V`
- second rising waveform (`V_fixture = VCC`) ends at `3.3 V`

Most important extraction clue:

- solved `Ku/Kd` ranges (vqfn20 typical):
  - rising: `Ku ~ [0.001, 1.003]`, `Kd ~ [-2.007, -1.288]`
  - falling: `Ku ~ [0.000, 1.004]`, `Kd ~ [-2.008, -1.344]`

Interpretation:

- `Kd` being strongly negative for the entire waveform is a red flag.
- That means the standard 2-waveform / 2-unknown push-pull decomposition is asking the pulldown branch to be
  "less than off" in order to fit the waveform pair.
- In other words, this model is not being represented naturally by the current `PU/PD + clamp + C_comp` scaling form.

Likely explanation:

- `ptc_i3c_std` behaves more like a special bus mode than an ordinary rail-to-rail digital I/O.
- Its large `C_comp` makes edge timing very sensitive.
- The waveform pair appears to require a branch combination that the current extraction/runtime form can only approximate badly.

This is the highest-priority model family to investigate next.

## Outlier regime 2: `io_vrefh10_slctrl` and `io_vrefh10_std`

These are moderate but very consistent outliers.

Observed behavior:

- rise RMS error about `0.050-0.062 V`
- fall RMS error about `0.046-0.052 V`
- timing offsets smaller than `ptc_i3c_std`, but still systematic

Useful metadata:

- `C_comp ~= 8.72 pF`
- `R_fixture=50`, `V_fixture=0` rising waveform ends at about `1.232 V`
- second rising waveform ends at about `3.193 V`, not `3.3 V`

Solved `Ku/Kd` ranges (vqfn20 typical):

- `io_vrefh10_slctrl`
  - rising: `Ku ~ [-0.042, 1.315]`, `Kd ~ [0.175, 1.033]`
  - falling: `Ku ~ [0.000, 1.301]`, `Kd ~ [0.160, 1.030]`
- `io_vrefh10_std`
  - rising: `Ku ~ [0.000, 1.336]`, `Kd ~ [0.169, 1.037]`
  - falling: `Ku ~ [0.000, 1.302]`, `Kd ~ [0.162, 1.033]`

Interpretation:

- These models do not look like ordinary "PU on, PD off" high-state outputs.
- The solve wants both branches active over much of the transition / hold region.
- `Ku > 1` and `Kd` staying well above `0` suggest a reduced-voltage / reference-like output behavior.

Likely explanation:

- These models are acting more like limited-voltage analog-ish outputs than standard digital high drivers.
- The current converter architecture can represent them, but only approximately, so the repeated `50-60 mV` error is not surprising.

## Outlier regime 3: `io_zxover_std` and `io_vrefh5_std`

These are mild-to-moderate outliers.

Observed behavior:

- `io_zxover_std`: rise RMS about `0.024-0.027 V`
- `io_vrefh5_std`: rise RMS about `0.023-0.025 V`
- fall errors are smaller than the rise errors
- timing is fairly close; these are not "totally wrong" models

Useful metadata:

- `io_zxover_std`: `C_comp ~= 3.18 pF`
- `io_vrefh5_std`: `C_comp ~= 4.85 pF`

Solved `Ku/Kd` ranges stay relatively sane:

- `io_zxover_std`
  - rising: `Ku ~ [-0.007, 1.002]`, `Kd ~ [0.000, 1.001]`
- `io_vrefh5_std`
  - rising: `Ku ~ [-0.043, 1.022]`, `Kd ~ [0.000, 1.000]`

Interpretation:

- These do not look fundamentally broken like `ptc_i3c_std`.
- They look more like fast-edge fidelity issues, especially on the rising edge.
- The corresponding `slctrl` variants are consistently better, which supports that reading.

Likely explanation:

- This is probably a normal "faster edge is harder to fit exactly" regime rather than a categorical model mismatch.

## Why package is probably not the main cause

The package still changes the exact numbers a little, but it does not change the ordering:

- the same family is bad everywhere,
- the same family is good everywhere,
- and package only nudges the metric up or down.

For example, `ptc_i3c_std` remains the worst family in all 4 packages, and `ptc_i2c_slctrl_fmp` remains among the best.

That is why the next debugging pass should focus on model behavior and extraction assumptions, not package handling.

## Recommended next steps

1. Deep-dive `ptc_i3c_std`
   - inspect the two IBIS waveform pairs directly
   - inspect branch-current balance around the rise and fall
   - understand why the solver wants `Kd < 0` everywhere

2. Deep-dive `io_vrefh10_slctrl/std`
   - treat them as reduced-voltage / reference-style outputs, not ordinary digital highs
   - inspect whether a variant extraction or runtime treatment is needed

3. Use `io_zxover_std` as a "fast but not catastrophic" case
   - useful to separate general fast-edge fidelity limits from special-model failures
