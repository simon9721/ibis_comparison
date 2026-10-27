# presentation_2026-10-27

Figures for the slide version of the stage-law paper, per `1027_presentation_materials.md`.
Built by `scripts/presentation_2026-10-27_figures.py` from stored runs only; nothing was
simulated. One palette throughout: transistor black, HSPICE native IBIS blue dashed, the
stage-law model teal, the value-matched replay orange, the file's own curves grey.

| slide | file | what it shows | source |
|---|---|---|---|
| challenge | `challenge_ex2.png`, `challenge_inv_chain.png` | transistor against native IBIS at 50, 70, 90 % of the settled swing | `stress_method_matrix_2026-08-20/delay_cmd/waveforms` |
| previous methods | `value_match_ex2.png` (810 ps), `value_match_inv_chain.png` (104 ps), both 50 % | the pad and K_u of the value-matched replay against transistor and native; the instant the value is matched is marked | `reversal_rules_ex2_inv_chain_2026-10-27/coeff_match` |
| previous methods | `time_match_ex2.png`, `time_match_inv_chain.png` | the file's rising and falling K_u and K_d tables on one clock; the step time matching demands at the reversal (ex2 810 ps: 0.88 + 0.95; inv_chain 104 ps: 1.00 + 1.00), which is why it never simulates | the file's two-waveform solve (pybis2spice) |
| K-stage model | `kstage_blocks.png` | Fig. 6 of the paper without equation numbers | `build_stage_law_doc_figures.fig_blocks(eq_numbers=False)` |
| mapping | `map_derivation.png` | the map from the alpha-power law in four lines, Times-like face | — |
| mapping | `maps_and_shapes.png` | the maps measured on the probed gates of ex2 and inv_chain, and the three candidate shapes over them | `gate_cascade_prototype_2026-09-09` shipped runs and the probed matrix runs, as Fig. 8 of the paper |
| fitting | `knob_sup.png`, `knob_sdn.png`, `knob_vt.png`, `knob_fit.png` | the four panels of Fig. 12 as four figures: one number moved around the fit, and a fit built one number at a time (rms only there) | the file's K_u(t) target and the selected chain, as fig_fit_knobs |
| fitting | `band_K.png` | residual of the fit against K with the band rule: the three smallest K within 25 % of the best are kept and the measured pulse chooses | `stage_count_from_file_2026-09-21/step1_summary.csv`, pass est_knee |
| verification | `fullswing_ex2.png`, `fullswing_inv_chain.png` | the model's complete transition against the transistor's, 50 % crossings dashed: ex2 1323 against 1400 ps, inv_chain 343 against 353 ps | the selected builds' `full` runs, `predriver_stages_2026-09-09` |
| result | `result_ex2.png`, `result_inv_chain.png`, `result_table.md/.csv` | transistor, native and the model at the five widths; peak error and lag per width, native beside | the selected builds (ex2 K = 3, inv_chain K = 7), `stress_method_matrix` native |

The result table:

| buffer | pulse width | depth | transistor peak | model peak error | model lag | native IBIS peak error |
|---|---:|---:|---:|---:|---:|---:|
| ex2 | 810 ps | 50 % | 0.77 V | −1.8 % | −7 ps | +71 % |
| ex2 | 830 ps | 60 % | 0.93 V | −5.5 % | −8 ps | +43 % |
| ex2 | 858 ps | 70 % | 1.09 V | −7.4 % | −10 ps | +24 % |
| ex2 | 895 ps | 80 % | 1.25 V | −8.3 % | −15 ps | +11 % |
| ex2 | 975 ps | 90 % | 1.40 V | −6.6 % | −20 ps | +1 % |
| inv_chain | 104 ps | 50 % | 0.69 V | −5.4 % | −9 ps | +89 % |
| inv_chain | 106 ps | 60 % | 0.85 V | −1.2 % | −8 ps | +54 % |
| inv_chain | 111 ps | 70 % | 1.01 V | +5.8 % | −3 ps | +32 % |
| inv_chain | 119 ps | 80 % | 1.14 V | +3.4 % | −6 ps | +19 % |
| inv_chain | 135 ps | 90 % | 1.28 V | +0.1 % | −12 ps | +7 % |

A negative lag means the model arrives early. The model was calibrated on the 50 % pulse of
each buffer; the other four widths are held out.
