# stage_law_flow_animation_2026-10-15

The stage-law flow, animated with manim (Community v0.22), as a companion to
`results/stage_law_doc_2026-10-01/stage_law_derivation_v2.docx`. Seven parts in the order of
the document, each with captions that say what the viewer is looking at:

1. **The problem.** ex2's complete transition (what the file records), then the 810 ps pulse:
   transistor netlist against HSPICE native IBIS (+71 % on the peak).
2. **The idea.** The signal path (comparator, K stages, map, I-V tables), the stage law, and one
   stage's step response as s_up and v_t are changed.
3. **Step 0, the target.** The file's two-fixture V-T waveforms, the converter's balance equation,
   the solved Ku(t) and Kd(t), the normalised target (25) with the chain input.
4. **Step 1, the fit.** The target, a trial model and its residual; s_up, s_dn and v_t varied one at
   a time with the residual updating; the fit (0.023). Then the residual landscape over (s_up, v_t)
   with the three Nelder-Mead runs walking on it: only the start at 2/ns reaches the minimum.
5. **What the file cannot tell.** Two maps, the stage law fitted through each: both land on the
   file; for the 810 ps pulse one gives Ku = 0.51 and the other 0. Stage counts 3, 4, 5 fit alike:
   nine candidates.
6. **Steps 2-4, the measurement.** The measured pulse; the nine candidates as fitted (peaks
   0.01-1.28 V); the bisection of v_t on one candidate, iteration by iteration (+40 % ... +0 %);
   all nine after calibration; the waveform rms of each and the selected one (K = 3, (0.5, 0.7)).
7. **The result.** The selected model at five widths against the transistor; the worst stressed
   peak error on the twelve buffers, proposed against native; the five steps as a closing card.

Every curve is a stored result of the project, gathered by
`scripts/stage_law_flow_animation_data.py` into `data/flow_data.npz` (105 arrays: the stress
matrix references, ex2's IBIS tables and waveforms, the converter's Ku/Kd solution, the stage-law
doc's `fit_search`, `calib_iterations`, `before_calibration` and `shape_from_file` results, the
step-6/8 candidate builds, the selector tables). Nothing is simulated by the animation.

## Build

    py -3.14 scripts/stage_law_flow_animation_data.py
    py -3.14 -m manim -qm --disable_caching --media_dir results/stage_law_flow_animation_2026-10-15/media ^
        scripts/stage_law_flow_animation.py StageLawFlow

The scene is `StageLawFlow` in `scripts/stage_law_flow_animation.py`; `P1` ... `P7` render one part
each for checking (`-ql` for a quick look). manim 0.22 was installed into the project's Python
3.14 (`pip install manim`; PyAV bundles ffmpeg, so no system ffmpeg is needed). There is no LaTeX
toolchain on this machine, so formulas are typeset by matplotlib's mathtext into SVG
(`media/mtex/`) and loaded as vector mobjects; captions and labels are Pango `Text` (Arial).
White background, the figure palette of the document (teal: fitted / model; blue: native or the
late map; red: measured or the early map; grey: from the file).

## Output

`StageLawFlow.mp4` at the folder root (copied from `media/videos/stage_law_flow_animation/720p30/`),
1280x720, 30 fps. `media/` holds manim's own tree (partial movie files, the mtex SVGs, the
landscape PNG) and is regenerable; the mp4 and `data/flow_data.npz` are what to keep.

Rendered 2026-10-15: 3 min 08 s (5631 frames, 181 animations), 7.6 MB. `contact_sheet.png` shows
24 frames at equal spacing.
