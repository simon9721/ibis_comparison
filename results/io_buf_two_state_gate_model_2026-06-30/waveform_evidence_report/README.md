# io_buf Waveform Evidence Report

Cached data only. No HSPICE or ngspice simulations were rerun for this deliverable.

Color key is fixed across all figures: HSPICE native IBIS is thick black, HSPICE transistor `io_buf.sp` is thick gray on pad panels only, legacy pybis is orange, value-match v2 is purple, directional+residual is red, and recover-mean is green.
Sparse, staggered markers identify ngspice traces even where curves overlap; the continuous line color remains the primary flow key.

## Figures And Captions

### `plots\edge_1ps_base_50r_2pf_waveform_evidence.png`
- Normal long-pulse control: legacy pybis should stay closest to native-IBIS Ku/Kd.
- Use the Ku/Kd panels to verify that experimental models do not earn credit from pad-only agreement.
- The pad panel includes transistor io_buf.sp only as a pad-level reference; it has no Ku/Kd coefficients.
- The wide native-vs-transistor pad difference is a setup/reference warning, not a pybis coefficient result.
- This is the preservation check: any short-pulse fix that breaks this case cannot become default.

### `plots\short_pulse_1ns_high_waveform_evidence.png`
- The shaded band is the native-IBIS Kd hold/recovery region after the reverse falling edge.
- Legacy pybis overdrives Ku toward a full pulse; value-match/two-state methods keep Ku partial.
- Kd is the hard problem: several methods improve pad shape while still missing native-IBIS Kd recovery.
- The transistor pad returns much sooner than the shaded native-IBIS Kd hold, so the hold is a playback target.
- This is the clearest evidence that pad improvement and coefficient correctness must be judged separately.

### `plots\short_pulse_2ns_high_waveform_evidence.png`
- The shaded native-IBIS Kd hold is even later here, while the transistor pad still returns quickly.
- Two-state directional models make Ku more partial than legacy, but Kd recovery remains model-dependent.
- Recover-mean improves native-IBIS Kd timing for this width more than for 1 ns, showing width sensitivity.
- The pad panel shows that transistor and native IBIS disagree in amplitude as well as timing.
- This case argues against a single fixed Kd recovery delay as a production solution.

### `plots\short_pulse_1ns_low_waveform_evidence.png`
- This mirrored direction behaves differently: short-low is generally easier for the two-state model.
- Watch Kd first: directional/residual variants track the native coefficient much better than short-high.
- Ku still matters because it carries the pullup-side recovery during the low pulse interruption.
- The transistor pad remains a pad-only reference and should not be read as a coefficient truth source.
- The contrast with short-high points to directional recovery logic, not static map fitting, as the remaining gap.

### `plots\waveform_evidence_contact_sheet.png`
- The contact sheet is a navigation aid for all four required waveform evidence cases.
- Read rows from top to bottom inside each case: Ku, Kd, then pad voltage.
- Use color consistency to track how each model behaves across directions and pulse widths.
- Short-high shaded regions identify the native-IBIS Kd hold region visually.
- For detailed inspection, open the individual full-size PNGs rather than this compressed sheet.

### `plots\short_pulse_1ns_high_kd_evolution.png`
- Each small panel compares one model generation against the same native-IBIS Kd reference.
- Legacy and value-match show why table replay/retiming alone is not enough for Kd.
- Identity/PWL/two-state variants improve hidden-state structure but still miss recovery behavior.
- Directional residual restores undershoot better, while recover-mean moves the Kd return earlier.
- The progression shows the real lever: Kd onset/recovery policy, not only Ku amplitude or pad shape.

## Cleaner Comparison Sets

### Short pulses without legacy pybis

These figures remove the grossly incorrect legacy replay so differences among the newer methods and native IBIS remain visible.
- `plots\short_pulse_no_legacy\short_pulse_1ns_high_new_methods_vs_native.png`
- `plots\short_pulse_no_legacy\short_pulse_2ns_high_new_methods_vs_native.png`
- `plots\short_pulse_no_legacy\short_pulse_1ns_low_new_methods_vs_native.png`
- `plots\short_pulse_no_legacy_contact_sheet.png`

### Directional + residual vs HSPICE native IBIS

These pairwise figures show Ku, Kd, and pad together. Native IBIS is the only HSPICE reference that exposes Ku/Kd.
- `plots\directional_residual_vs_native_ibis\edge_1ps_base_50r_2pf_directional_residual_vs_native_ibis.png`
- `plots\directional_residual_vs_native_ibis\short_pulse_1ns_high_directional_residual_vs_native_ibis.png`
- `plots\directional_residual_vs_native_ibis\short_pulse_2ns_high_directional_residual_vs_native_ibis.png`
- `plots\directional_residual_vs_native_ibis\short_pulse_1ns_low_directional_residual_vs_native_ibis.png`
- `plots\directional_residual_vs_native_ibis_contact_sheet.png`

### Directional + residual vs HSPICE transistor io_buf.sp

These pairwise figures compare pad voltage only because the transistor-level deck does not expose IBIS Ku/Kd coefficients.
- `plots\directional_residual_vs_hspice_sp\edge_1ps_base_50r_2pf_directional_residual_vs_hspice_sp.png`
- `plots\directional_residual_vs_hspice_sp\short_pulse_1ns_high_directional_residual_vs_hspice_sp.png`
- `plots\directional_residual_vs_hspice_sp\short_pulse_2ns_high_directional_residual_vs_hspice_sp.png`
- `plots\directional_residual_vs_hspice_sp\short_pulse_1ns_low_directional_residual_vs_hspice_sp.png`
- `plots\directional_residual_vs_hspice_sp_contact_sheet.png`

## Numeric Data

- `data/<case>_aligned_1ps.csv`: one shared 1 ps time axis matching the plotted zoom window, with `Ku`, `Kd`, and pad columns by flow.
- `data/<case>_metadata.csv`: edge times, shaded native-Kd hold interval, labels, and colors used in the figures.
- `data/raw/<case>/<flow>_signals.csv`: original cached time samples for the plotted signals before interpolation.
- `data/short_pulse_1ns_high_kd_evolution_aligned_1ps.csv`: numeric source for the Kd evolution figure.

- `data\edge_1ps_base_50r_2pf_aligned_1ps.csv`
- `data\edge_1ps_base_50r_2pf_metadata.csv`
- `data\short_pulse_1ns_high_aligned_1ps.csv`
- `data\short_pulse_1ns_high_metadata.csv`
- `data\short_pulse_2ns_high_aligned_1ps.csv`
- `data\short_pulse_2ns_high_metadata.csv`
- `data\short_pulse_1ns_low_aligned_1ps.csv`
- `data\short_pulse_1ns_low_metadata.csv`
- `data\short_pulse_1ns_high_kd_evolution_aligned_1ps.csv`
- `data\short_pulse_1ns_high_kd_evolution_metadata.csv`
