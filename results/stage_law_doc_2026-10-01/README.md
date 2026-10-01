# Stage-law derivation document

*2026-10-01*

`stage_law_derivation_v2.docx` — the derivation of the stage law from the α-power law
(Sections II-A to II-E) followed by how it is used and verified (II-F to II-M). Native Word
equations, ten figures, eight tables.

| | |
|---|---|
| builder | `python scripts/build_stage_law_doc.py` (toolkit: `scripts/stage_law_docx.py`) |
| figures | `python scripts/build_stage_law_doc_figures.py` → `figures/` |
| source | `source/stage_law_derivation_original.docx` — the draft this continues; its Sections A–E are kept verbatim, everything from its Section F on is rebuilt |

## What changed against the draft

The draft's Sections F–K carried twelve `[CONFIRM]` and three `[MISSING]` flags. Each was
resolved from the code or the result files, not from memory:

| draft flag | resolution | source |
|---|---|---|
| pad-current equation (24) | `Ku·I_PU + Kd·I_PD` + clamp tables when the file has them; `C_comp` at the die | a generated `driver.sub` (B3, B4, C2), `subcircuit.py` clamps |
| why `G_DN = 1 − G_UP` | single-inverter output stage; io_buf gets a second chain | `chain_command.patch_shared_gate` / `patch_chain` |
| how K is selected | rms of the pad waveform over `[t_f − 0.3, t_f + 1.5]` ns among 9 candidates | `selector_from_one_run.py` |
| `v_t` calibration objective | zero of the signed pad **peak** error, bisection on [0, 0.7], 3 + 7 runs | `gate_chain_prototype.calibrate_pad` |
| 217.3 mV against 52.3 mV | mean pad-waveform rms over all five widths, by selection rule | `selector_from_one_run_2026-09-23/FINDINGS.md` |
| io_buf "linear end to end" | high-going pulses of 1505–2354 ps; pad 0.373 vs 0.371 | `predriver_stages_2026-09-09/FINDINGS.md` |
| inv_chain gate node | `vout7` | `current_limited_stage_model.py` |
| pad-level results on 12 buffers | Table VII, Fig. 9, Fig. 10 | `selector_picks.csv`, cascade sweeps |
| stale inv_chain K = 5, 3 rows | regenerated, see below | `regen_inv_chain_shared.py` |
| references [2], [3] | [2] kept with the fields the book's bibliography confirms; [3] removed (uncited, uncheckable) | `docs/book/` |

## The regenerated inv_chain table

`results/current_limited_stages_2026-09-10/inv_chain_chain_shared_K.csv` was written on 09-09
at 23:39; `current_limited_stage_model.py` was last changed on 09-10 at 12:30, when explicit
Euler was replaced by Heun because Euler biased inv_chain's fast stages. That is why the
committed table stopped reproducing (`device_taper_2026-09-28/FINDINGS.md` §6b).

`regen_inv_chain_shared.py` re-runs the identical-stage fits with the current integrator, one
optimiser start per process (`fit_K*_s*.json`), and writes
`inv_chain_chain_shared_K_regenerated.csv`. K = 7 reproduces the 0.701 found independently on
09-28. What moved:

| K | 104 ps, committed | 104 ps, regenerated | 135 ps, committed | 135 ps, regenerated |
|---|---:|---:|---:|---:|
| 3 | 0 | 0 | 0 | 0 |
| 5 | 0 | 0 | 0.869 | **0.810** |
| 7 | 0.672 | **0.701** | 0.987 | 0.987 |
| 9 | 0.941 | 0.942 | 0.992 | 0.992 |

The K = 3 and K = 5 fits end with `v_t` on its 0.7 bound. ex2's table was re-run by the owner
script itself and its K = 3 row is unchanged to the third decimal (K = 2: 0.287–0.520 →
0.303–0.538).

## One thing found on the way

The bisection curves in the 09-24 deck's `calib_run.png` are plotted against time from the
input's **falling** edge (`export_method_animation_data`: `bis_t = g − rev`) under an axis
labelled "time from the input edge". Fig. 7(b) here shifts them onto the rising edge.

## Checked against the paper (2026-10-01, later the same day)

Reference [1] (Sakurai & Newton 1990) was read in full. The stage law stands: its equations
(2)-(5) are the paper's (2)-(4), the straight-line triode region is the paper's own, and one
stage reproduces the paper's delay formula (5) within 4 ps (`check_delay_formula.py`).

Two corrections came out of it, both to the device extraction, not to the law:

- Appendix A extracts `V_TH` and alpha only. The first build of this document said `V_D0` was
  taken "following [1, App. A]" from the origin tangent; the paper prescribes no `V_D0`
  extraction, and the tangent reads low. Table II now uses the breakpoint that best fits the
  paper's piecewise model: `x0` 0.34-0.57 (was 0.23-0.42).
- alpha is now extracted the paper's way (the `V_TH` that linearises the log-log plot):
  1.10-1.63 (was 1.11-1.39).

Also added: a limits paragraph (the paper says the model fails near threshold and neglects the
opposing device - the regime a truncated pulse lives in), and reference [3] restored with the
details the paper's own reference list confirms.
