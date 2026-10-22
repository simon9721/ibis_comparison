# stage_law_model_animation_2026-10-22

The stage-law model itself, explained with manim (Community v0.22), as a companion to the paper in
`results/stage_law_doc_2026-10-01` and to the earlier `results/stage_law_flow_animation_2026-10-15`,
which explained the fitting procedure. This one explains what a stage is, what its law means term
by term, how a chain behaves under a complete transition and a short pulse, what the map is, how
the pad is produced, and only then, briefly, what the file fixes and what one measurement settles.
Seven parts on the test buffer ex2, each with captions that say what the viewer is looking at:

1. **What the file knows, and what a short pulse does.** The buffer as a block diagram (input pin,
   predriver inverters, output stage, C_comp, package, pad); what the file describes and the
   predriver it does not. ex2's complete transition (input, probed gate, pad, normalised), the
   810 ps pulse on which the gate turns back at 0.76, and the pad in volts: transistor against
   HSPICE native IBIS (+71 % on the peak).
2. **One stage and its law.** (a) The inverter as a schematic, with u and v defined. (b) The
   bucket, animated: a tap fills the node, a drain empties it; the input ramps up, the tap opens
   at v_t, the level rises at s_up, tapers within x_lin of the brim, and the drain takes over when
   the input falls; v(t) is traced alongside, and each factor of the law is boxed as it acts
   (illustrative values v_t = 0.3, x_lin = 0.45, s_up = s_dn = 2/ns; the input is a 0.4 ns ramp, not
   a step, because a step makes the gate factor trivial). (c) Where the law comes from: the
   alpha-power law, the inv_chain NMOS output curves from HSPICE at five gate drives with the
   piecewise model (the drain factor r), the saturation current against gate drive on log axes
   (slope alpha = 1.28, the gate factor h; p = 1 used), and one stage's step response (ramp, then
   exponential with tau = x_lin/s_up). (d) The three knobs: s_up, v_t (on a 0.5 ns input ramp) and
   s_dn.
3. **The chain: delay is spent in handovers.** Comparator, three stages, the gate, with ex2's
   selected file-only numbers (K = 3, s_up 2.55/ns, s_dn 2.69/ns, v_t 0.632 after calibration,
   x_lin 0.45). Complete transition: the nodes one after the other, the handovers at 0.25 and
   0.66 ns, the gate at its rail by 1.73 ns. The 810 ps pulse: v1 turns back at once, v2 peaks at
   0.88, the gate at 0.71; the probed gate of ex2 (peak 0.76) alongside, which the model's gate
   leads by 68 ps.
4. **The map: from the gate to the conducting fraction.** (a) ex2's probed gate and the file's
   K_u(t) read at five instants; the pairs moved onto a (g, K_u) plane trace the map. (b) The
   formula M(g) with (v_t,map, a), fitted (0.57, 0.64); why the map cannot be read from the file;
   the three candidate shapes. (c) The two relations in series, mirroring the paper's Fig. 8: the
   chain's gate, the map read at six instants, K_u(t) against the file's own, for the complete
   transition and for the 810 ps pulse (gate turns back at 0.71, K_u peaks at 0.54).
5. **From K_u to the pad.** The die current I_die = K_u I_PU + K_d I_PD; ex2's pull-up and
   pull-down tables, the pull-up scaled by K_u = 0.54; the pad at 810 ps: transistor, native
   (+71 %), the model (-2 %).
6. **What the file fixes, what it cannot, and what one measurement settles.** The fit of s_up,
   s_dn, v_t to the file's K_u(t), one number at a time from a first guess (rms 0.291 to 0.023,
   v_t on its bound 0.7). The ambiguity: two maps, (0.6, 0.6) and (0.4, 0.6), each fitted through
   to the same file (rms 0.0241 and 0.0233), K_u peaks of 0.26 and 0 under the 810 ps pulse; stage
   counts 3, 4, 5 with rms 0.0233, 0.0229, 0.0212: nine candidates. The one measurement (peak
   0.77 V); the nine as fitted (peaks 0.01 to 1.28 V); the bisection of v_t on the selected
   candidate, five of its ten iterations; all nine after calibration; the waveform rms selects
   K = 3, (0.5, 0.7) at 56 mV; the selected model at the five widths (within 8.3 % on the peak).
7. **Closing card.** The parameter set and where each number comes from (fitted, calibrated,
   chosen by the measurement, built-in, from the file), and the result line.

Every curve is a stored result of the project, gathered by
`scripts/stage_law_model_animation_data.py` into `data/model_data.npz` (156 arrays; the docstring
lists each one and its source). The model curves are the model's own equations evaluated on
stored parameters (`current_limited_stage_model.simulate`, `build_stage_law_doc_figures.chain_stages`
and `prior`), as the previous data script did. Sources: the predriver_stages tr0 runs and the
stress matrix (part 1, 3, 4, 5), `device_taper_2026-09-28/alpha_extract` (part 2), the
gate_cascade ex2_c1.7 shipped run and `gate_physics_2026-09-08/FINDINGS.md` (part 4), the file-only
IBIS file `stage_count_from_file_2026-09-21/knee_models/ex2_c2.64/input_ccomp.ibs` for the I-V
tables and C_comp (part 5; the previous animation used the ex2_c1.7 file of the probed-map
setting), the stage-law doc's `shape_fileonly`, `fit_search_fileonly`, `before_calibration` and
`calib_iterations`, the step6/step8 candidate builds and the selector tables (part 6). Nothing is
simulated by the animation. The data script checks the storyboard's numbers against the stored
results and lists the differences (handovers 0.25/0.66 ns rather than 0.29/0.73; device alphas
1.10-1.63 rather than 1.0-1.4; K = 5 residual 0.0212 rather than 0.0220); the captions use the
stored values.

## Build

    py -3.14 scripts/stage_law_model_animation_data.py
    py -3.14 -m manim -qm --disable_caching --media_dir results/stage_law_model_animation_2026-10-22/media ^
        scripts/stage_law_model_animation.py StageLawModel

The scene is `StageLawModel` in `scripts/stage_law_model_animation.py`; `P1` ... `P7` render one part
each for checking (`-ql` for a quick look). The drawing helpers, palette and caption methods are
imported from `scripts/stage_law_flow_animation.py`, with its mathtext cache pointed at this
folder's `media/mtex/`; three helpers are new (a partial curve for tracing with a ValueTracker, log
axes, and a term box that locates one term of a mathtext formula by measuring ink widths with
matplotlib's TextPath). No LaTeX on this machine: formulas are mathtext SVGs; text is Pango Arial.
White background, the palette of the document (teal: the model; blue: native; red: measured or the
early map; grey: the file's own curves and inputs; orange: built-in or assumed things).

## Output

`StageLawModel.mp4` at the folder root (copied from `media/videos/stage_law_model_animation/720p30/`),
1280x720, 30 fps. `media/` holds manim's own tree (partial movie files, the mtex SVGs) and is
regenerable; the mp4 and `data/model_data.npz` are what to keep. `render.log` is the render's
console output.

Rendered 2026-10-22: 6 min 16 s (11 272 frames, 409 animations, 4 min of rendering at 720p30), 16.2 MB.
`contact_sheet.png` shows 24 frames at equal spacing.
