# method_animations_2026-09-17

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 56M, 11 files, written 2026-09-17 to 2026-09-17
- location before archiving: `results/method_animations_2026-09-17`

## Contents (top level)

```
bgm.wav                                             33M
bgm_source/                                        9.8M  2 files
bisection.gif                                      312K
fit_search.gif                                     492K
map_build.gif                                      588K
method_data.npz                                    1.4M
web/                                                11M  4 files
```

## Produced by

`scripts/build_0917_deck_figures.py`:

> Slide figures for the 2026-09-17 deck: inside the buffer, and the open question.
> 
> Conventions inherited from build_deck_figures.py, which the 0904 README sets out:
> 
> * **Simulation figures only.** No bar charts, no scatter plots, no schematics. A number is
>   explained by listing it on the slide.
> * **Drawn at the size they are placed**, so axis text is the size it claims. The study's
>   figures are 17-20 in wide; dropped into a 12 in slide box their labels come out at 5-7 pt.
>   Everything here is drawn at 12.2 x 5.2 (full width) or 6.0 x 4.9 (half) with 14-17 pt fonts.
> * Pad and coefficients side by side for the same case; bold pipe-separated titles
>   (device | pulse | quantity); the transistor as a thick pale trace with the models drawn
>   over it; the reversal marked with a dashed line.
> * The shipped model keeps the purple the audience already knows from the 0904 and 0911
>   decks. The real gate replayed into the model is teal, the one colour not yet spoken for.
> 
> Nothing is re-simulated - every panel is rebuilt from raw output already on disk.
> 
>     py -3.14 scripts/build_0917_deck_figures.py
> 

`scripts/build_0918_deck_figures.py`:

> Figures for Simon's 2026-09-18 deck, `0918_Simon_IBIS.pptx`, from the comments on it.
> 
>     slide 3          recap_pad.png                 io_buf 1792 ps: transistor, native, gate_state_fixed
>     slide 4          ex2_stress_levels.png         ex2 at 90 / 80 / 70 / 60 / 50 % depth, main bench
>     slide 5          inv_chain_stress_levels.png   inv_chain, the same
>     slides 10/13/16  four_panel_{io_buf,ex2,inv_chain}.png  real gate / GUP / Ku / pad
>     slides 11/14/17  real_gate_{io_buf,ex2,inv_chain}.png   the same four panels, GUP = the real gate
> 
> gate_state_fixed is the build the 09-04 deck called cmd_clean and the code calls delay_cmd
> (InputDrivenTwoStateGateDelayCommandFull). Everything is at the file's declared C_comp, like
> the recap and variant slides. Slides 10-17 are at 70 % stress, the width of the stage walks
> on slides 9 / 12 / 15: io_buf 2090 ps, ex2 858 ps, inv_chain 111 ps. Nothing is re-simulated.
> 
>     py -3.14 scripts/build_0918_deck_figures.py
> 

`scripts/build_method_animations.py`:

> Animated walkthroughs of how track 1 and track 2 actually work, from real runs.
> 
>     fit_search.gif      the four stage numbers being searched until the chain lands on one
>                         full-swing recording (the Nelder-Mead trial sequence, logged live)
>     bisection.gif       the one stressed pad run placing the stage threshold, replayed from
>                         the ten iteration directories the calibration actually wrote
>     map_build.gif       two fixture runs becoming the Ku map: a cursor sweeps time, and each
>                         instant drops a point onto the gate-versus-Ku plane
> 
> Everything drawn is measured or computed from runs already on disk; nothing is illustrated.
> 
>     py -3.14 scripts/build_method_animations.py
> 

`scripts/export_method_animation_data.py`:

> Export the data behind the method film to plain arrays.
> 
> The manim environment is a separate interpreter with none of this project's readers, so a
> scene cannot open the simulation runs itself. This dumps everything an animation needs into a
> single .npz of plain numpy arrays, from real runs only:
> 
>     stage_*      the predriver nodes on one full-swing run, each normalised to its own rest
>                  and full-swing level, so the pulse can be watched moving down the chain
>     fit_*        the Nelder-Mead trial sequence fitting four stage numbers to one full-swing
>                  recording: the target, and the chain output at each improving trial
>     bis_*        the ten iterations the threshold bisection actually wrote, with the threshold
>                  recovered from each emitted netlist
>     map_*        the two fixture runs, the Ku and Kd solved from them at each instant, and the
>                  gate node at the same instants
>     slv_*        ONE instant in full detail: both pad voltages, the I-V curves the two
>                  multipliers are read off, the term-by-term right-hand sides, and the answer.
>                  This is the beat that shows WHY two loads are enough to solve for two unknowns
>     cmp_*        the measured Ku map against the analytic prior track 1 uses from the file
>     pay_*        the payoff at the 810 ps stressed pulse: transistor, the file-only build, and
>                  the build that uses the measured maps
> 
> Each block is independent: a failure prints and continues, so one bad path does not cost the
> whole export. A missing key then fails loudly in the scene rather than silently drawing nothing.
> 
>     py -3.14 scripts/export_method_animation_data.py
> 

`scripts/film_scenes.py`:

> One continuous film: how an IBIS buffer becomes a gate-state ngspice model.
> 
> Single Scene, so manim emits a single mp4. Every beat is driven by real exported runs
> (method_data.npz) except the opening schematic, which is drawn from primitives.
> 
> Teaching happens through motion, not prose: on-screen text is limited to short labels, the
> act rail, and numeric readouts. Nothing here relies on an accompanying page.
> 
> No LaTeX anywhere - numbered manim axes render through MathTex and this machine has none.
> Labels are positioned against the Axes BOUNDING BOX, never against ax.x_axis / ax.y_axis,
> because manim draws those lines through the DATA ORIGIN, which on a plot whose range does not
> start at zero sits in the middle of the data.
> 
>     manimenv/Scripts/python.exe -m manim -qm --disable_caching \
>         --media_dir <scratch>/manim_media film_scenes.py Method
> 

`scripts/make_film_bgm.py`:

> Prepare the method film's background music from a public-domain recording.
> 
> The first attempt was a synthetic pad - five sines through a moving average - and it sounded
> like exactly that. This replaces it with a real recording, chosen for its licence as much as
> its mood, and records the provenance here so it lives with the file.
> 
> Source (primary)
>     Erik Satie, Gymnopedie No. 1, performed and uploaded by Wikimedia Commons user Teknopazzo.
>     https://commons.wikimedia.org/wiki/File:Gymnopedie_No._1..ogg
>     Direct: https://upload.wikimedia.org/wikipedia/commons/b/b7/Gymnopedie_No._1..ogg
>     Licence: CC0 1.0 (Creative Commons Zero, public domain dedication). No attribution required.
>     Composition: Satie, 1888 - public domain.
> 
> Source (fallback)
>     Same piece, performed by Robin Alciatore.
>     https://commons.wikimedia.org/wiki/File:Erik_Satie_-_gymnopedies_-_la_1_ere._lent_et_douloureux.ogg
>     Licence: public domain. No attribution required. 183.6 s - shorter than the film.
> 
> Both licence fields were read from the Commons API (extmetadata LicenseShortName /
> AttributionRequired), not from a search summary.
> 
> What this does: decode with the bundled ffmpeg, trim to just under the film's run time, fade
> in briefly and out over the last seconds, scale to a modest peak, write a 44.1 kHz stereo wav
> that Scene.add_sound mixes in.
> 
> THE LENGTH MATTERS. manim sets the output length to the LONGER of the animations and the
> audio, so audio longer than the film appends a frozen final frame. Keep `--seconds` below the
> film's run time (3:17.93 at the time of writing) and regenerate if the film grows past it.
> 
>     py -3.14 scripts/make_film_bgm.py [--seconds 196] [--peak 0.35] [--source PATH]

`scripts/method_scenes.py`:

> Track 1 and track 2, animated in manim, from the real exported runs.
> 
> No LaTeX anywhere: every label is Text (pango), and no Axes uses include_numbers, because
> numbered axes render through MathTex and this machine has no working LaTeX. Tick labels are
> drawn by hand as Text.
> 
> Layout note: labels are positioned against the Axes BOUNDING BOX, never against ax.x_axis or
> ax.y_axis. Manim draws those axis lines through the data origin, so on a plot whose x range
> starts below zero the x-axis line sits in the middle of the data and anything placed relative
> to it lands on top of the curves.
> 
> Data comes from results/method_animations_2026-09-17/method_data.npz, exported by the project
> interpreter, since this environment has none of the project's readers.
> 
>     manimenv/Scripts/python.exe -m manim -qm --disable_caching \
>         --media_dir <scratch>/manim_media method_scenes.py FitSearch Bisection MapBuild
> 

