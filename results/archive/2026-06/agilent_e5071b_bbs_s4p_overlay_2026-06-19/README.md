# Agilent_E5071B_17b7949f BBS Touchstone Overlay

This folder compares an original Touchstone channel with the fitted Touchstone response written by BroadbandSPICE next to the generated General SPICE model.

Important detail: the frequency-domain comparison uses BBS's exported fitted Touchstone response. That is the BBS model's own S-parameter response, not a separate ngspice AC extraction from the `.sp` wrapper.

## Inputs

- Original Touchstone: `results\agilent_e5071b_bbs_s4p_overlay_2026-06-19\artifacts\Agilent_E5071B_original.s4p`
- BBS fitted Touchstone: `results\agilent_e5071b_bbs_s4p_overlay_2026-06-19\artifacts\Agilent_E5071B_Fitted_bbs_fitted.s4p`
- BBS General SPICE model: `results\agilent_e5071b_bbs_s4p_overlay_2026-06-19\artifacts\Agilent_E5071B_GSPICE.txt`
- ngspice wrapper: `results\agilent_e5071b_bbs_s4p_overlay_2026-06-19\artifacts\Agilent_E5071B_17b7949f_bbs_passivity2_gspice_clean_ngspice_wrapper.sp`

## Source Metadata

- Original option line: `# Hz S dB R 75`
- Fitted option line: `#	Hz	S	RI	R	75`
- Ports: `4`
- Original format: `DB`
- Fitted format: `RI`
- Z0: `75`

## BBS Ranking Context

- Candidate: `bbs_passivity2_gspice_clean`
- Independent trust class: `FAIL`
- RX trust class: `FAIL`
- Full-model trust class: `FAIL`
- ngspice smoke pass: `False`

## Plots

- `plots/01_sparameter_magnitude_matrix_overlay.png`
- `plots/02_sparameter_phase_matrix_overlay.png`
- `plots/03_sparameter_error_matrix.png`
- `plots/04_dominant_transmission_paths.png`
- `plots/05_reflection_paths.png`
- `plots/06_error_summary_by_path.png`

Available transient HSPICE-vs-ngspice audit overlays copied from the BBS campaign:

- `results\agilent_e5071b_bbs_s4p_overlay_2026-06-19\plots\transient_overlays\bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50.png`
- `results\agilent_e5071b_bbs_s4p_overlay_2026-06-19\plots\transient_overlays\bbs_passivity2_gspice_reciprocity_audit_amp1p5_edge5_r50.png`

## Fit Metrics

| Path | Complex RMS | Complex max | Mag dB RMS | Mag dB max | Mag dB max above -40 dB | Phase RMS deg |
|---|---:|---:|---:|---:|---:|---:|
| all | 0.00753121 | 0.104814 | 2.29842 | 34.3502 |  |  |
| S11 | 0.0200217 | 0.104814 | 0.501921 | 4.30001 | 4.30001 | 3.37842 |
| S12 | 0.000515839 | 0.00172428 | 2.03371 | 14.555 | 0.177807 | 12.8814 |
| S13 | 0.00142877 | 0.00343242 | 4.06092 | 34.3502 | 0.329818 | 303.939 |
| S14 | 0.000517008 | 0.00425804 | 3.00213 | 12.2471 | 2.21881 | 328.053 |
| S21 | 0.000464924 | 0.00175462 | 2.78957 | 22.8455 | 0.1724 | 356.626 |
| S22 | 0.0189776 | 0.0937087 | 0.294579 | 2.9543 | 2.9543 | 3.1376 |
| S23 | 0.000433543 | 0.001903 | 0.829261 | 8.50138 | 0.384495 | 5.39795 |
| S24 | 9.8025e-05 | 0.000440208 | 3.1724 | 14.5452 |  | 334.895 |
| S31 | 0.000414197 | 0.00141703 | 3.01809 | 33.7909 | 0.112549 | 6.87764 |
| S32 | 0.000236011 | 0.00058258 | 0.432475 | 1.74407 | 0.303285 | 3.20899 |
| S33 | 0.00776507 | 0.0295454 | 0.0925299 | 0.594898 | 0.594898 | 0.461685 |
| S34 | 0.000276438 | 0.000854523 | 0.72232 | 5.91023 | 0.110181 | 3.88058 |
| S41 | 0.000609428 | 0.0036811 | 3.51272 | 16.5142 | 1.96517 | 89.3409 |
| S42 | 0.000148697 | 0.000548738 | 3.69635 | 19.7979 |  | 359.206 |
| S43 | 0.000177271 | 0.000833626 | 0.36875 | 1.8099 | 0.202798 | 2.32941 |
| S44 | 0.00908167 | 0.0496177 | 0.217676 | 2.28539 | 2.28539 | 1.42613 |

## Reading The Result

Use the matrix plots to see whether the converted model preserves the full multiport behavior. The dominant-path plot focuses on the strongest off-diagonal transmission terms, while the reflection plot isolates the diagonal terms.

A low complex RMS can still hide larger dB error on very small coupling paths. For deciding simulation readiness, this should be read together with transient ngspice/HSPICE correlation, not by frequency fit alone.
