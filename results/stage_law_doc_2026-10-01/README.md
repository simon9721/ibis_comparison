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

## Section H rebuilt around the gate-to-Ku construction (2026-10-02)

The stage law gives only the gate; `K_u` comes from a second, separate relation (the map).
Section H now says so and shows it: the separability assumption `I(V_pad, g) = K_u(g) I_PU(V_pad)`,
a hand-worked single-stage table (Table V), and Fig. 5 (`fig_gate_to_ku`), which traces the same
six instants from `g(t)` through the map to `K_u(t)`, for a full transition (where the result is
compared with the file - that comparison is the fit) and for an 810 ps pulse (where the gate
turns back and only part of the map is read).

Two statements corrected at the same time:

- `x_lin = 0.45` is **not** "fixed throughout": it is fixed on ten of the twelve buffers and was
  fitted to the file on inv_chain and io_buf. Section E now gives how the value was chosen.
- The method is not built from the IBIS file alone. Table IV lists every input and its origin:
  the file, the fit, one stressed measurement, and four built-in constants chosen during
  development with transistor-level information.

## Quick test: can the map shape be chosen from the file? (2026-10-02) - no

`shape_from_file.py` fits the stage law through six map shapes to the file's `K_u(t)`
(eq. 26, `x_lin` = 0.45). The residual is flat across shapes: 0.0214-0.0238 on ex2 (1.11x)
and 0.0078-0.0084 on inv_chain (1.08x). The slight preference is not for the measured shape
either - on ex2 the shape nearest the probed map, (0.6, 0.6), fits worst. The stage threshold
compensates (it runs to its 0.7 bound as the map starts earlier). So the file cannot choose
the map shape; it has to come from the stressed measurement, or from outside knowledge.

## Sections H, I and K rewritten: the map, the fit through it, the stressed run (2026-10-02)

The three things that were not coming across, each now with a figure drawn from real fits:

- **What the map M(g) is** (H, `fig_map`): a curve of K_u against the gate, measurable where the
  gate can be probed; the formula is a two-number description of that measured curve, its
  parameters empirical. A symbol table gives every value. The file cannot give the map because it
  has K_u against time and no gate; the three candidate shapes are built-in constants and the
  least well founded element of the method.
- **How the fit works** (I, `fig_ambiguity`): a map is assumed first, then the stage law is fitted
  through it. The fit succeeds whichever map is assumed (six shapes: residual within 11 % / 8 %).
  Two real fits on ex2 that the file cannot tell apart give K_u peaks of 0.51 and 0 for an 810 ps
  pulse.
- **Why and how the stressed run is used** (K, `fig_stress_use`): the nine candidates fitted to
  the same file give pad peaks of 0.01-1.28 V against 0.77 V measured; calibration puts them all on
  the peak; selection takes the waveform; the selected model is checked at five widths. The
  pre-calibration runs are re-simulated from the stored `calib/it00` subcircuits and cached in
  `before_calibration/*.npz`.

## Is the file-only model's internal gate the real gate? (2026-10-02) - close, not identical

`gate_internal_check.py` compares `v(x1.gup)` of the selected file-only build with the probed
gate (ex2 n4, inv_chain vout7), which the method never sees.

| | peak of the stressed gate, model minus real | timing | waveform rms |
|---|---|---|---|
| ex2 (5 widths) | -0.05 ... -0.03 | model leads by 56-74 ps | 0.06-0.08 |
| inv_chain (5 widths) | -0.08 ... -0.01 | model leads by 12-20 ps | 0.04-0.06 |

Full swing: rms 0.033 and 0.041, model leading by 40 and 22 ps. The model's gate has the
right height and shape and is slightly early and slightly low; its return is faster than the
real gate's on ex2. So the internals resemble the transistor's, although only the pad was
ever fitted - but they are not the same waveform.

## Section B made self-contained; the internal-gate check added to L (2026-10-08)

- The clip in (5) is declared ours (lower bound = the paper's cutoff row, upper bound = a
  numerical guard for node overshoot in the chain); it does not appear in [1].
- The `min` form (6) is derived instead of asserted: factor `I'_D0` out of the paper's triode
  row, and in each conducting row the multiplier is the smaller of 1 and `V_DS/V'_D0`. The
  paper has no single-expression form; this one is ours.
- Section L gains "2) The model's internal gate against the transistor's" (Table XI, Fig. 12,
  from `gate_internal_check.py`): the file-only model's gate is 0.03-0.08 low and 12-74 ps
  early against the probed gate, with a faster return on ex2.

## Read-through for a first-time reader; the fit walked through (2026-10-09)

A read of the whole document as someone with minimum background would read it. Five changes,
all in `build_stage_law_doc.py` (figures in `build_stage_law_doc_figures.py`):

- **Opening page.** "Preliminaries: the problem, the idea and the terms" before Section A: what
  an IBIS file contains and what the existing converter does with it; the problem, with
  `fig_problem` (Fig. 1: ex2's complete transition against an 810 ps pulse, native IBIS +71 %
  on the peak); the idea in one paragraph; Table II of the terms used throughout; and a
  warning that three thresholds (V_TH, v_t, v_t,map) and three exponents (alpha, p, a) appear.
  Title and date updated; the Section II intro now points to the preliminaries.
- **Symbols that change meaning.** Section C: why u is measured downward from the supply (the
  pull-up PMOS is driven harder as the input falls); a note after (9) that v_t is a device
  threshold there (0.14-0.33) and an effective fitted number from Section I onward (0.03-0.53).
- **"What the fit actually does"** (Section I, `fig_fit_knobs`, Fig. 9): where the information
  is (the two edges, about 0.7 ns each of a 17 ns window); what each of the three numbers does,
  one varied at a time around the ex2 fit (s_up: rising edge; s_dn: falling edge; v_t: the
  delay); how the search proceeds, and a fit built one number at a time from a poor first guess
  (rms 0.296 -> 0.201 -> 0.060 -> 0.023); why one stage is not enough (one-stage residual 0.083
  against 0.023, because one rate cannot give both a 1.1 ns delay and a 0.66 ns edge); what the
  fit decides and what it leaves open. Figures 1-16 and Tables II-XIV renumbered.
- **Parts and steps.** Section F now has "six parts", and "steps" is reserved for the numbered
  procedure of Table IV.
- **Table XII header** names the five stressed widths (narrowest ... widest) instead of blank
  columns.

Rendered through Word: 26 pages, 16 figures, 14 tables. Delivered as
`\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\stage_law_derivation_v2.docx`.
