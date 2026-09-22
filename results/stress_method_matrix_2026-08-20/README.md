# stress_method_matrix_2026-08-20

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 24G, 13261 files, written 2026-06-04 to 2026-08-26
- location before archiving: `results/stress_method_matrix_2026-08-20`

## Contents (top level)

```
coeff_match/                                       593M  962 files
delay_cmd/                                         2.2G  962 files
figures/                                           7.7M  34 files
gate_match/                                        828M  724 files
gate_match_aligned/                                762M  240 files
gate_match_delayed/                                330M  242 files
gate_match_equiv/                                  695M  240 files
gate_match_equiv_delaycmd/                         927M  240 files
gate_match_hybrid/                                 725M  240 files
gate_match_shared/                                 568M  724 files
gate_state/                                        3.4G  954 files
hybrid/                                            763M  774 files
legacy/                                            236M  964 files
measured_rate/                                     334M  724 files
pad_match/                                         529M  991 files
pad_match_slew/                                    1.6G  1212 files
per_case.csv                                        12K
predriver_cmd/                                     4.2G  950 files
summary.csv                                        4.0K
time_match/                                        1.2G  678 files
time_match_hybrid/                                 1.4G  720 files
value_match_full/                                  2.5G  684 files
```

`summary.csv` columns: `group,cases,native,gate_state,delay_cmd,predriver_cmd,legacy,time_match,gate_match,measured_rate,gate_match_shared,value_match_full,coeff_match,pad_match,pad_match_slew,hybrid` (5 rows)

## Produced by

`scripts/archive/analyse_reversal_discontinuity.py`:

> Why some reversal policies will not simulate: the jump they demand.
> 
> At a reversal every replay method must choose where to re-enter the opposite
> coefficient table. Whatever it chooses, the coefficient generally does not equal
> what it was an instant earlier, and the difference is a step discontinuity the
> solver has to pass through. A big enough step and the timestep collapses.
> 
> This computes that step for each policy without needing the simulation to
> succeed, which matters because the ones that fail leave no waveform behind:
> 
>   time      re-enter at the same elapsed offset -- match nothing
>   value     re-enter where the opposite table holds the present coefficient
>   gate      re-enter at the time the opposite gate trajectory holds the present
>             hidden state, taken separately for Ku and Kd
> 
> The coefficient at the reversal is read from a run that did converge, so the
> starting point is real rather than assumed.
> 

`scripts/archive/analyse_stress_matrix_shapes.py`:

> Check the stress-matrix waveforms for defects a mean error cannot show.
> 
> An RMSE ranks methods but hides shape. A model can win on error while producing
> a trace no buffer would produce -- an extra dip, a response that starts before
> the input edge, a peak in the wrong place -- and those are the failures that
> matter when the model is driving a channel simulation rather than a scoreboard.
> 
> Three measures, all against silicon on the same grid:
> 
>   glitches   extra local extrema in the model's pad between the reverse edge and
>              3 ns after it, beyond the number silicon shows. This is what caught
>              the transport-delay command splitting one pulse into two.
>   peak       how far the model's extreme pad excursion misses silicon's, in mV,
>              signed so over-response is positive.
>   early      how long before silicon the model first leaves its starting rail.
>              Positive means the model moves first, which is unphysical.
> 

`scripts/archive/build_comprehensive_offset_chain_figure.py`:

> Build a complete causal view of the io_buf short-high offset.
> 
> The figure follows one event through the model:
> 
>     input -> command capacitor -> gate state -> Ku/Kd -> pad
> 
> HSPICE native IBIS is shown for Ku, Kd and pad. The HSPICE transistor pad is
> shown directly, while transistor Ku/Kd are derived from two cached fixture
> runs on the corrected uniform 5 ps solve grid.
> 

`scripts/archive/build_flat_figure_set_2026_08_20.py`:

> One figure per case, flat and numbered, for dropping straight into slides.
> 
> Follows the layout of the 2026-08-18 hybrid sweep set so the two are directly
> comparable: wide single-panel pad plots, stacked Ku/Kd plots, a bold
> `buffer | direction | target` title, the transistor drawn thick and grey behind
> native IBIS in black, and the reverse edge marked.
> 
> Three types per case rather than two. The gate-state plot is new: GUP and GDN
> for every case, not just the few that made the talk, so a claim about the hidden
> states can be checked anywhere rather than trusted from a sample.
> 
> Panels are cropped where the traces stop moving. inv_chain pulses are around
> 110 ps and these records run to 22 ns, so a fixed window is mostly flat.
> 

`scripts/archive/build_method_explainer_figures.py`:

> Two figures: what the silicon extraction actually adds, and how the two
> command layers differ mechanically.
> 
> An earlier version of this script drew three figures arguing for the silicon
> Ku/Kd extraction. They were withdrawn because none of them needed it. The
> native-IBIS-invents-a-pulse figure was a pad comparison, which requires no
> coefficient extraction at all; the dead-zone figure repeated what the IBIS table
> already says; and the bump-on-a-pedestal figure could have been drawn against
> native IBIS Ku, whose bump peaks at 0.0469 against silicon's 0.0460.
> 
> So the question is answered by measurement instead. Silicon Ku/Kd and native
> IBIS Ku/Kd are both available on all 17 recovery cases. Where they agree, the
> extraction only confirmed what was already on hand; where they disagree over a
> sustained stretch -- not merely at an edge, where silicon is known to be
> unreliable -- it carries information nothing else does:
> 
>     io_buf short-high    slow-moving |dKu| = 0.0020   the offset cases
>     io_buf short-low     slow-moving |dKu| = 0.2494   sustained 2.3 ns
>     ex2    short-low     slow-moving |dKu| = 0.2023   sustained 0.6 ns
> 
> That is the honest split. On the cases this investigation was about, the
> extraction added nothing. On short-low it disagrees with native IBIS by a
> quarter of full scale for nanoseconds at a time, and that has not been used yet.
> 
> The command figure zooms to picosecond scale on the two instants where the
> command changes, because that is where the mechanism is: the shipped block
> integrates a 10 ps pulse and lands wherever the solver's timesteps put it, while
> the level block steps to an exact rail.
> 
>     py -3.14 scripts/build_method_explainer_figures.py

`scripts/archive/build_offset_all_cases_figures.py`:

> Figure 13, repeated for every stress case that has both builds.
> 
> One figure per case: the full response above, the post-reversal tail below, with
> the transistor, native IBIS, the shipped gate-state model and the level-driven
> command on the same axes. The restore-term probe only exists for the five
> io_buf short-high targets, so it appears on those and is absent elsewhere.
> 
> The reversal is located from the data rather than assumed, because short-high
> and short-low start their edges at different times: the first sample where the
> transistor pad leaves its initial level by 5% of the record's full range is the
> edge, and the reversal is one pulse width later.
> 
> The tail measurement is the mean absolute gap to the transistor between the
> reversal + 1.0 ns and + 1.7 ns. On io_buf that window sits after the pad has
> discharged and before the pulldown finally engages at + 1.83 ns, so it reads the
> stranded-charge pedestal and nothing else.
> 
>     py -3.14 scripts/build_offset_all_cases_figures.py
> 

`scripts/archive/build_offset_eventual_settling_figure.py`:

> Show that the io_buf short-high offset eventually decays to zero.
> 
> Uses the cached command-probe CSV only. No simulation is launched.
> 

`scripts/archive/build_offset_solved_figure.py`:

> Does the level-driven command actually remove the settled offset?
> 
> Four pad traces on the two io_buf short-high cases where the defect is visible
> (the other three are the ones the clamp made look clean):
> 
>     HSPICE transistor      ground truth
>     HSPICE native IBIS     the bar
>     shipped gate-state     the defect -- edge-integrating command
>     restore-term fix       cleanup started sooner and decayed faster
>     delay_cmd              the structural repair -- command is a delayed level
> 
> The measurement is the pad plateau between reversal + 1.0 and + 1.7 ns, taken
> before the pulldown bump so it reads the stranded-charge pedestal and nothing
> else. Averaged over the four cases that ran:
> 
>     native IBIS          2.0 mV from the transistor
>     shipped gate-state  28.6 mV
>     restore-term fix    14.3 mV
>     delay_cmd            2.2 mV
> 
> The cleanup halves the error; the level-driven command removes it. That is the
> expected shape -- a restore term acts only after the charge is already stranded,
> and it is gated off for 2.99 ns precisely so it cannot disturb a command still
> in flight, so it cannot help during the window that matters.
> 
>     py -3.14 scripts/build_offset_solved_figure.py
> 

`scripts/archive/build_presentation_figures_2026_08_20.py`:

> Figures for the 2026-08-20 talk: hybrid and pad-matching only.
> 
> Deliberately narrower than the current state of the work. Transistor-derived
> Ku/Kd and the newer command formulations are held back, so everything here is
> scored against HSPICE native IBIS and the transistor pad, which is what the
> audience has seen before.
> 
> Three figures:
> 
>   gate_capacitors   the hidden gate states GUP/GDN on a few cases, to show they
>                     stay inside [0,1]. Only the gate-state family has them;
>                     pad-matched replay carries no hidden capacitor at all.
> 
>   coefficient_range Ku and Kd for the model and for native IBIS, with dV/dt
>                     underneath. The coefficients leave [0,1] and the pad slew
>                     underneath shows why: the current an IBIS buffer must supply
>                     includes C_comp*dV/dt, and near a sharp edge that term is
>                     larger than either device can source, so no combination of
>                     two coefficients inside [0,1] can produce it.
> 
>   stress_<device>   all five stress levels, both directions, hybrid and
>                     pad-matching against native IBIS and the transistor.
> 

`scripts/archive/build_stress_matrix_report.py`:

> Score every method in the stress matrix against silicon, per stress level.
> 
> Reads whatever `run_stress_method_matrix.py` has produced so far -- methods run
> in priority order and each is resumable, so a partial matrix is normal and is
> reported as such rather than being treated as an error.
> 
> Errors are time-weighted, since HSPICE's adaptive grid oversamples transitions
> by roughly ten to one and a sample mean would report the transition almost
> exclusively. HSPICE native IBIS is scored the same way in every table: it has
> exactly the information the models have, so it is the honest bar for them.
> 
> Writes summary.csv and per_case.csv, and prints the tables.
> 

`scripts/archive/build_table_entry_figures.py`:

> Where each reversal rule re-enters the falling table, drawn in table space.
> 
> The simulated Ku traces for t-matching and value matching look nearly identical
> -- both collapse almost vertically at the reversal -- which makes it impossible
> to see, from the waveform alone, that the two rules chose different entry
> points, or to rule out a bug.
> 
> Plotting the tables themselves settles it. The falling Ku table is a cliff: it
> leaves 0.94 and is under 0.03 within 500 ps, while the rising Ku table needs the
> full 6 ns to climb. So every entry rule lands on a curve that is already at or
> near zero, and the choice of entry point buys only a few hundred picoseconds.
> The near-vertical drop is the table's own shape, not a discontinuity the
> solver invented.
> 
> Two figures:
> 
>   table space   the rising and falling Ku and Kd tables against time-since-edge,
>                 with the exit point and both rules' entry points marked
>   real time     both methods and native IBIS on one axis, so the gap the two
>                 entry rules actually produce is visible at its true size
> 
>     py -3.14 scripts/build_table_entry_figures.py
> 

`scripts/archive/plot_stress_matrix_methods.py`:

> Plot the 90%-50% stress sweep: every method, every level, all three buffers.
> 
> Two views, because they answer different questions.
> 
> `{device}_stress.png` is the waveform grid -- five stress levels across, both
> directions down, every method overlaid on silicon. This is where shape defects
> live: an extra dip, a response that starts before the input edge, an excursion
> that overshoots. A mean error cannot show any of those.
> 
> `error_vs_stress.png` is the same data as curves of error against stress level.
> It answers the question the sweep was built to ask -- not which method is best
> on average, but how each one degrades as the pulse gets harder, and where the
> orderings cross.
> 
> An earlier version plotted only the mildest and harshest level, which left
> three of the five with no cross-method figure at all.
> 

`scripts/build_0911_deck_figures.py`:

> Figures for the 2026-09-11 deck update: the cmd_clean command (slide 7) and the variant
> stress results (slide 9). Nothing here re-simulates; every figure is drawn from existing runs.
> 
>     results/meeting_deck_2026-09-11/figures/
>       cmd_clean_command.png        io_buf 1792 ps: input, the command node, the gate, original vs cmd_clean
>       variants_same_stress.png     one family per panel: the transistor's pad on every variant at 50 % depth
>       variants_model_vs_si.png     one panel per variant at 50 % depth: transistor, ours, native
>       variants_peak_law.png        peak excess against depth, ours and native, one panel per family
>       variants_what_changed.png    what was changed in the silicon against how much the error moved
>       variants_entry.png           the mechanism: how far 'on' each model is when the transistor's pad peaks
>       variants_two_regimes.png     where each buffer's event sits: io_buf alone in the residual corner
> 
>     py -3.14 scripts/build_0911_deck_figures.py
> 

`scripts/build_0917_deck.py`:

> Build the 2026-09-17 deck: inside the buffer, what it taught us, and the open question.
> 
> This deck deliberately stops before the solution. It shows the internal-stage study on
> three buffers, what was learned, the verification that driving Ku/Kd from the transistor's
> own gate node works, why the shipped model's gate is not that node, the question that
> leaves, and the experiments that did not answer it. Track 1, track 2 and the four-number fit
> are not on these slides.
> 
> Style follows the 0904 and 0911 decks:
> 
> * Simulation figures only; a number is listed, not charted. One relaxation, agreed for this
>   deck: one slide of schematic, drawn as native shapes, for the stage structure.
> * Two or three lines state the point; the rest of the slide is the waveform.
> * The wrong turns stay on the slides with their corrections.
> 
> One layout rule learned on this deck's first render: the 0904 script placed every figure at
> a fixed y under a fixed 0.75 in per bullet, and any bullet that wrapped put the figure
> straight through the text. Here `points()` returns the y it actually used and figures are
> placed from that.
> 
>     py -3.14 scripts/build_0917_deck_figures.py     # first
>     py -3.14 scripts/build_0917_deck.py
>     powershell -ExecutionPolicy Bypass -File scripts/render_deck_slides.ps1 `
>         -Deck results/meeting_deck_2026-09-17/inside_the_buffer_2026-09-17.pptx
> 

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

`scripts/build_cmd_clean_slides.py`:

> Two figures: last week's pages redrawn with cmd_clean added as a third curve.
> 
> Last week's deck compared **original** against **fix** — the retuned restore term
> — on io_buf, short high, 1792 ps. These are the same two figures, same case, same
> wording and same colours, with **cmd_clean** (the build the code calls
> `delay_cmd`) drawn alongside so all three can be read at once:
> 
>     results/settled_offset_diagnosis_2026-08-27/
>         12_gup_ku_fix_comparison.png       ->  cmd_clean_gate_and_ku.png
>         11_pad_voltage_fix_comparison.png  ->  cmd_clean_pad.png
> 
> Last week's palette is kept exactly, so a curve that was purple last week is
> purple again: transistor #111111, native #2B6CA3, original #C05621, fix #7A3E9D.
> cmd_clean takes #2E8B57, the one colour in that palette not already spoken for.
> 
> The pad figure is one panel, not two. Last week's carried a post-reversal tail
> zoom underneath; this is the full view only.
> 
> Sources, all one bench -- nothing here re-simulates what already exists:
> 
>   * `settled_offset_diagnosis_2026-08-27/09_comprehensive_offset_fix_comparison.csv`
>     is what last week's pages were drawn from. It carries the input, every
>     internal node of both the original and the fix, and the transistor and native
>     references.
>   * `stress_method_matrix_2026-08-20/delay_cmd/waveforms/io_buf_short_high_w1792ps.csv`
>     carries cmd_clean's Ku, Kd and pad. Its transistor and native columns are
>     identical to the comprehensive CSV's to the last decimal, which is how we know
>     the two files are the same bench and can be combined.
> 
> cmd_clean's *internal* nodes (GUPCMD, GUP) are in neither file, so one ngspice run

`scripts/build_correction_shape_figures.py`:

> Before and after, against both references, as shapes rather than numbers.
> 
> `residual_rescale_time_2026-09-04` reports the two derived corrections as
> aggregate pedestal and RMSE. Those cannot show whether the *shape* survived --
> and three earlier candidate fixes in this investigation improved the aggregates
> while quietly destroying the Kd shape. So this draws it.
> 
> The window runs to +3 ns rather than +1, because the most informative event is
> not the fall. After the pad collapses to zero at about +1.2 ns it comes back up
> to a **secondary bump of ~52 mV at +1.8 ns** -- the pull-down finally being
> commanded on, with Kd running 0 -> 1 straight through it. That bump is a clean,
> well separated timing marker, and it is where the accumulating shift shows:
> 
>     transistor   1.905 -> 1.700 ns   as the pulse shortens (205 ps earlier)
>     native       1.905 -> 1.848 ns   (68 ps, a third of it)
>     ours         2.014 -> 2.014 ns   flat -- the command chain is fixed delays
>                                      from the input edge, so it cannot move
> 
>     py -3.14 scripts/build_correction_shape_figures.py
> 

`scripts/build_deck_figures.py`:

> Slide figures for the meeting deck: simulation waveforms only.
> 
> Two rules, both from comparing the deck against an earlier one that read better:
> 
> **Only simulation results.** No bar charts, no scatter plots, no schematics. A
> number is explained by listing it on the slide, not by drawing it as a bar. An
> earlier draft turned the error budget, the C_comp sweep and the max|Ku| table into
> charts; they looked tidy and told the reader less than the plain numbers would
> have.
> 
> **Drawn at the size they are placed.** The study's print figures are 11-13 in wide
> and up to 13 in tall with ~10 pt labels; dropped into a slide box their axis text
> measured 3.9-5.6 pt. These are drawn at the slide box size with 14-17 pt fonts, so
> the scale factor is 1.0 and the text is the size it claims.
> 
> Layout follows the earlier deck: pad voltage and the coefficients side by side for
> the same case, a bold pipe-separated title carrying device, pulse and quantity,
> the transistor as a thick pale trace with native IBIS drawn over it, and the
> reversal marked with a dashed line.
> 
> Nothing is re-simulated -- every panel is rebuilt from raw output or CSVs already
> on disk.
> 
>     py -3.14 scripts/build_deck_figures.py
> 

`scripts/build_delay_cmd_dead_zone_figure.py`:

> What the transport-delay command buys, and what it costs.
> 
> `delay_cmd` is the "stop integrating a pulse" formulation: the command is a
> delayed copy of the input *level*, so it is exactly 0 or 1 at the rails by
> construction and cannot strand charge. It has the best pad RMSE in the study --
> 92.2 mV over 30 stress cases, the only method to beat native IBIS.
> 
> The cost is visible in the top two panels. io_buf turns its pullup *off*
> 0.068 ns after the input falls but does not turn its pulldown *on* for
> 1.831 ns. Two independently delayed levels therefore both read "off" for the
> 1.25 ns in between, and the pad is left with no driver at all -- both
> coefficients go slightly negative and the node keeps only C_comp and the load.
> 
> The shipped edge-integrating command is drawn alongside. It has no dead zone,
> because the pulldown command is a capacitor that was already charged; it pays
> for that with the stranded charge instead.
> 
>     py -3.14 scripts/build_delay_cmd_dead_zone_figure.py
> 

`scripts/build_ibis_intro_figures.py`:

> Intro-slide figures: what Ku/Kd are, and where the short pulse breaks them.
> 
> Four figures telling one story on one buffer, so the audience tracks the same
> two traces throughout:
> 
>     1  full swing, pad voltage      HSPICE native IBIS vs our ngspice model
>     2  full swing, Ku and Kd        the same agreement, in the coefficients
>     3  short pulse, pad voltage     where it stops agreeing
>     4  short pulse, Ku and Kd       why: the legacy model restarts the opposite
>                                     table from its beginning at the reverse edge
> 
> The model is `pybis2spice` in its shipped `InputDriven` mode -- the converter
> before any interruption handling. Slides call it "ngspice" because on an intro
> slide the tool matters and the mode does not.
> 
> Both traces come from the same joint record the rest of the study uses, so the
> grid is identical for both and no resampling favours either one.
> 
>     py -3.14 scripts/build_ibis_intro_figures.py --device io_buf
> 

`scripts/build_implementation_comparison_figure.py`:

> The shipped builds, not the mechanism: gate-state against every Vc-matching.
> 
> Figure 18 shows the two *mechanisms* agree to 0.08 mV once everything else is
> stripped away. This shows what the actual implementations do on a real case,
> which is a different and less flattering picture: the production models carry
> residual corrections, arming and sampling machinery, and read Ku from different
> places, so they do not produce the same waveform.
> 
> io_buf short_high at 2226 ps is the only width where all five builds converge,
> so the comparison is made there rather than on the deck's 1634 ps case, which
> pure gate-state and two of the Vc builds do not solve.
> 
>     py -3.14 scripts/build_implementation_comparison_figure.py
> 

`scripts/build_machinery_explainer_figures.py`:

> Two figures for the machinery walkthrough, drawn from probed netlist nodes.
> 
> 21  event vs continuous   the integrator's state moves smoothly and latches
>                           nothing; the replay's sample and entry are staircases,
>                           and every step is an event that had to be detected.
> 
> 22  why the residual       the map alone does not reproduce the recorded Ku, and
>                           the residual is exactly that shortfall. Vc-matching
>                           reads the recorded table directly, so it has no map to
>                           correct.
> 
> Both read the raw ngspice output rather than the resampled CSVs, because the
> staircases in figure 21 are step changes a union grid would smear.
> 
>     py -3.14 scripts/build_machinery_explainer_figures.py
> 

`scripts/build_offset_chain_figure.py`:

> The settled offset traced through one buffer, one case, one link per panel.
> 
> Figure 03 reads top to bottom. Each panel is the input to the panel below it,
> so the pad offset can be followed upward until it reaches the layer that
> created it:
> 
>     GUPCMD      the command capacitor          <- created here
>     GUPTARGET   after the clamp
>     GUP         the gate state
>     Ku          the map of the gate, plus the residual
>     pad         what the load sees
> 
> Only the 60% case is drawn. An earlier version put 60% and 70% side by side to
> contrast a bad case with a good one, which is misleading: 70% is *not* good.
> Its command error is -0.0056 and the clamp erases it, so a reader comparing the
> two would conclude the defect is case-dependent when in fact all five cases
> carry it. That comparison belongs in figure 02, where the clamp is the subject.
> 
> Figure 04 is the same case before and after the restore-term fix.
> 
>     py -3.14 scripts/build_offset_chain_figure.py
> 

`scripts/build_reversal_method_figures.py`:

> Slide figures for the two reversal-entry rules that did not work.
> 
> Two policies, each shown as a pad plot and a Ku/Kd plot, on the same io_buf case
> the intro figures use:
> 
>     t-matching       at the reversal, enter the opposite table at the same
>                      elapsed offset the current one had reached
>     value-matching   enter the opposite table where it already holds the Ku and
>                      Kd the model has right now
> 
> Both are the `...ReplayFull` builders, which replace the whole waveform path
> rather than only the reversal. That matters for how these read: neither trace
> is wrong only after the reverse edge, and the figures show it. `coeff_match` is
> built alongside as the guarded variant that leaves the normal transition alone.
> 
> No annotations by request -- traces, a reverse-edge marker, and a legend. The
> transistor is on the pad plots because "failed" only means something against
> the thing being reproduced.
> 
>     py -3.14 scripts/build_reversal_method_figures.py
> 

`scripts/build_settled_offset_diagnosis.py`:

> Trace the io_buf short-high settled offset from the pad back to the command.
> 
> The 2026-08-20 stress figures show io_buf short-high leaving the pad elevated
> for several nanoseconds after the reversal at targets 90/60/50, while 80 and 70
> return cleanly. This walks that back one layer at a time:
> 
>     pad  <-  Ku  <-  pwl(GUP)  <-  GUP  <-  GUPTARGET  <-  command capacitor
> 
> Left column is the shipped edge-integrating command, right column the
> transport-delay command, on the same five cases. Time is measured from the
> reversal so the five widths overlay.
> 
>     py -3.14 scripts/build_settled_offset_diagnosis.py
> 

`scripts/coefficient_shapes.py`:

> Look at the Ku/Kd shapes, across stress, against the transistor.
> 
> Every measurement in the pedestal investigation so far has been a *number* -- a
> best-fit lag, sometimes with a residual to say whether the lag meant anything.
> That has been enough to eliminate causes but not to find one, and a lag by
> construction cannot see a change of shape.
> 
> So this draws them. Three sources on one axis, for every io_buf short_high width
> plus the unstressed control:
> 
>     silicon_*   the transistor, through the two-fixture solve -- ground truth
>     hspice_*    native IBIS's own St_pu / St_pd
>     pybis_*     ours
> 
> Time is plotted relative to each case's own reversal, so the widths overlay and
> the question "what changes as the pulse gets shorter" is answerable by eye.
> 
>     py -3.14 scripts/coefficient_shapes.py
> 

`scripts/cross_device_stress_metrics.py`:

> One instrument, every stressed buffer: the io_buf findings tested for generality.
> 
> Everything established on io_buf short-high in the 2026-09-07 series is a claim
> about one buffer. This runs the same measurements over every stressed short-high
> case that exists -- the three base buffers in the stress matrix and the nine
> variants at five depths -- so trends can be read across families.
> 
> v2. The first pass scored Ku in a window 50-400 ps *after the pad peak*, which is
> right for io_buf and empty for everyone else: on inv_chain the whole event is a
> ~200 ps spike, on ex2 the pull-up is fully off by then. So the scoring window is
> now the **event itself**, bounded by the transistor's own coefficients:
> 
>     t_on   first time after the reversal the transistor's Ku exceeds 0.10
>     t_off  first time after the pad peak its Kd is back above 0.90
> 
> and the timing metrics are the two crossings that the traces showed carry the
> defect on every buffer:
> 
>     ku_off50   when Ku falls back through 0.5 after its peak   (pull-up turn-off)
>     kd_on50    when Kd rises back through 0.5                  (pull-down re-engage)
> 
> reported as model minus transistor, ps, so positive means late.
> 
> The reference is the transistor: pad into the study load, Ku/Kd re-solved from
> its two fixture runs at 5 ps (2/10 ps spread recorded in-window). Native is
> flagged invalid where its pad never rises (all ex2 variants and inv_stage4 on the
> tr1ps IBIS files); our `delay_cmd` build is scored everywhere.
> 
> The "bump" is kept only where it is a genuine secondary event: the pad must fall
> below 5% of its peak and then rise by more than 5 mV. io_buf has one; ex2 and

`scripts/delay_cmd_timing_test.py`:

> Does delay_cmd fix the timing shift, or only the offset?
> 
> The offset defect was traced to `GUPCMD`: an open-loop integrator with no DC path,
> so a truncated pulse strands charge. `delay_cmd` is level-driven -- the command is
> a function of the current input level rather than accumulated edge history -- so it
> returns to exactly zero and strands nothing, and it removes the offset
> (63.9 -> 3.7 mV at reversal).
> 
> The timing shift ("defect B") was separately shown to be **stress-specific**: the
> gate-state build is ~9 ps from native on a clean full-swing edge but ~75-125 ps
> under stress. Truncation is the same trigger as the offset, so the two defects may
> be one mechanism -- and if they are, delay_cmd should already fix the timing too.
> 
> Nobody has checked. delay_cmd's *amplitude* was measured (RMSE 108.6 -> 92.2 mV,
> best in the study); its *timing* never was. This measures it.
> 
> Method note: these stressed events are partial excursions, so a fixed 50%-of-rail
> threshold is not a safe reference -- on some cases it is never crossed. Timing is
> taken at 50% of *each case's transistor excursion*, applied identically to every
> build, so the comparison does not depend on how far the pulse happened to get.
> 
>     py -3.14 scripts/delay_cmd_timing_test.py
> 

`scripts/delay_pedestal_test.py`:

> Is the stress pedestal the fitted command delays?
> 
> `pedestal_localization.py` showed the pedestal is already present in Ku and Kd at
> the same size as in the pad, so it is made upstream of the output stage. And on
> io_buf, native's Ku tracks the transistor's own Ku to +1..+19 ps while ours is
> +64..+111 ps late -- so it is our coefficient timing that is wrong, not native's.
> 
> What generates our coefficient timing is the command layer, and it is built from
> **two delayed copies of the input** combined with a gate:
> 
>     TPDCMDA NINX 0 PDCMDA 0 Td=0.850179n      the shorter delay
>     TPDCMDB NINX 0 PDCMDB 0 Td=1.831336n      the longer one
>     BPDCMDLVL = (V(PDCMDA) > 0.5) || (V(PDCMDB) > 0.5)
> 
> The gap between the two copies is what sets when the command turns on and off.
> Fitted per device:
> 
>     io_buf      PU 0.925 ns   PD 0.981 ns      pulses 1.505 - 2.354 ns
>     ex2         PU 0.333      PD 0.275         pulses 0.688 - 0.975
>     inv_chain   PU 0.021      PD 0.035         pulses 0.104 - 0.135
> 
> On io_buf the gap is **half the entire stressed pulse**. When the pulse is that
> short the two delayed copies straddle the next input edge, and the gate sees a
> combination it never sees on a long pulse -- which is exactly the shape of a
> defect that is absent at full swing and present under stress.
> 
> This tests it the only way that settles it: scale every fitted delay and see
> whether the pedestal follows. Measured as the lag of our pad against native's
> over the outward leg, on io_buf's own stressed case.
> 

`scripts/ex2_ccomp_correction_test.py`:

> ex2 with the C_comp the device actually has: does the stressed pad improve?
> 
> `gate_physics_2026-09-08` measured ex2's C_comp at 1.5-1.75 pF from the Ku-vs-gate
> loop, against a declared 5.0. Both IBIS models simulate with the declared value
> and every coefficient table was solved with it. This tests the correction the way
> a user would apply it: edit the .ibs, rebuild, re-run.
> 
> Two stressed widths from the matrix (858, 975 ps) plus the 10 ns control,
> transistor references already on disk. Native and ours are run at the declared
> 5.0 pF and at 1.7 pF; the transistor's Ku is re-solved at both so the coefficient
> comparison is apples to apples.
> 
>     py -3.14 scripts/ex2_ccomp_correction_test.py
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

`scripts/gate_ramp_prototype.py`:

> Hypothesis: the gate should be a SLOW ramp with a STEEP map, not a delay plus a fast ramp.
> 
> `gate_physics_2026-09-08` measured the real predriver gate and found Ku to be a
> static map of it. The real gate is a slow node: on inv_chain it takes ~250 ps to
> arrive, on ex2 ~700 ps. Our shipped model instead represents the same Ku(t) as
> 
>     command delay (pu_on, 0.27 ns on inv)  ->  fast RC gate (tau_rise 20 ps)  ->  map
> 
> At full swing the two descriptions are indistinguishable -- both reproduce the
> same Ku(t) -- so the characterisation cannot tell them apart. Under truncation
> they differ completely: a delay-then-fast-ramp is either fully on or fully off
> at the reversal, while a slow ramp is *partway*, and a steep map turns "partway"
> into a Ku that has not reached 1. `cross_device_stress_2026-09-08` measured that
> exact symptom (entry excess, r = 0.889 with the peak error).
> 
> So this rebuilds the gate as slow-ramp-plus-steep-map, **derived so that the
> full-swing Ku(t) is preserved by construction**: pick tau_rise' = k x shipped,
> take the shipped full-swing gate-part Ku(t) on the rise, and define
> 
>     map'(g) = Ku_shipped(t)   where   g = 1 - exp(-(t - t_on) / tau_rise')
> 
> Two variants of the fall: `dual` keeps a separate fall map derived the same way
> (exact at full swing, may jump at a truncated reversal); `single` uses the rise
> map for both branches -- the physics -- with tau_fall' fitted to the shipped fall.
> 
> Then run the stressed widths and score against the transistor. If the peak excess
> collapses as k grows while full swing stays put, the hypothesis stands.
> 
>     py -3.14 scripts/gate_ramp_prototype.py --variant inv_base8
> 

`scripts/gate_tracking_vs_transistor.py`:

> Does the corrected model's internal gate follow the transistor's real gate?
> 
> The prototypes reproduce the stressed pad on twelve buffers. That could be a
> good curve fit or the right physics. The matrix transistor runs recorded the
> real predriver gate (ex2 `n4`, inv_chain `vout7`, io_buf `n2`), so the question
> is answerable: normalise the real gate to its own full-swing excursion and
> overlay the model's command/gate nodes under stress.
> 
> For ex2 the cascade's last stage (`PUP5`) is the model's predriver and `GUP`
> its gate; for inv_chain the hybrid stage (`PUCMDLVL`) and `GUP`. If the
> model's node tracks the transistor's in time and in how far it gets, the
> structure is physical. If it tracks only at full swing, it is a fit.
> 
>     py -3.14 scripts/gate_tracking_vs_transistor.py --variant ex2 --build cascade5
>     py -3.14 scripts/gate_tracking_vs_transistor.py --variant inv_chain --build hybrid50ps
> 

`scripts/ku_excess_decompose.py`:

> Where does our excess Ku live -- the gate map, or the residual?
> 
> Scored against the transistor over +90..+400 ps from the reversal (the window
> where the two-fixture solve is trustworthy; nearer the reversal it goes
> ill-conditioned and reads 0.99 at 1792 ps, which the device does not do):
> 
>     Ku rms vs transistor        native 0.0167   shipped 0.1358   corrected 0.0903
>     Ku ratio to transistor      native 1.07     shipped 1.93     corrected 1.59
>     Kd rms vs transistor        native 0.0107   shipped 0.0411   corrected 0.0148
> 
> So Kd is essentially solved and **Ku is not** -- still 1.6x the transistor after
> the residual scaling. Since the correction already halves the residual, a 1.6x
> leftover implies the **gate part** over-predicts on its own.
> 
> Ku is built as:
> 
>     KUGATE_BASE = pwl(GUP, ...) selected on whether GUP is rising or falling
>     KURES_TABLE = pwl(HNX, ...) the residual
>     Ku          = KUGATE_BASE + KURES_TABLE
> 
> This probes all three plus GUP and HNX, so the excess can be attributed.
> 
>     py -3.14 scripts/ku_excess_decompose.py
> 

`scripts/ku_gate_hysteresis_ccomp.py`:

> Ku against the transistor's own gate voltage, and the C_comp that closes the loop.
> 
> Every base-buffer transistor run in the stress matrix recorded an internal
> predriver node (io_buf n2, inv_chain vout7, ex2 n4). Plotting the two-fixture Ku
> against that node over an event asks whether Ku is a static map of the gate --
> the premise of the gate-state model.
> 
> The two-fixture solve subtracts C_comp*dV/dt before dividing by I_pu(V). A wrong
> C_comp leaves displacement current booked as Ku, and dV/dt flips sign between
> the rise and the fall, so the error opens a **loop** in Ku-vs-gate. Sweeping the
> C_comp used in the solve and finding the value that minimises the loop measures
> the device's capacitance with no C-V run. A real capacitance is width-independent;
> the minimum has to be too, or the method is not measuring one.
> 
> Result 2026-09-08: ex2 minimises at 1.50-1.75 pF on all five widths against a
> declared 5.0; inv_chain at 0.50-0.60 against 0.468; io_buf is too shallow to
> decide (slow gate, small dV/dt) but agrees in direction with the direct C-V
> extraction. See results/gate_physics_2026-09-08/FINDINGS.md.
> 
>     py -3.14 scripts/ku_gate_hysteresis_ccomp.py
> 

`scripts/ku_overshoot_test.py`:

> Why does our Ku keep rising after the reversal, when native's turns around?
> 
> Looking at the coefficient *shapes* rather than a fitted lag
> (`coefficient_shapes.png`) makes the pedestal visible as something specific:
> 
>     io_buf 1792 ps, Ku after the reversal      peak     at
>         native                                 0.508    48 ps
>         ours                                   0.669    77 ps
> 
> Before the reversal all three curves lie on each other. At the reversal native
> turns around and ours **keeps climbing for another 29 ps and 0.16 higher**. That
> overshoot is the pedestal's origin, and it is a shape fact no best-fit lag was
> ever going to show.
> 
> The command layer gates the pull-up like this:
> 
>     TPUCMDA NINX 0 PUCMDA 0 Td=0.992581n     the on-delay
>     TPUCMDB NINX 0 PUCMDB 0 Td=0.0677n       the off-delay
>     BPUCMDLVL = (V(PUCMDA) > 0.5) && (V(PUCMDB) > 0.5)
> 
> With AND, PUCMDLVL **falls when the earlier copy falls** -- so the pull-up is told
> to stop `pu_off_delay` = 68 ps after the input reverses. Our Ku peaks at 77 ps.
> That is the hypothesis: the overshoot is the off-delay, and nothing else.
> 
> Earlier sweeps scaled all four delays together and measured the *pad* with a
> best-fit lag, which mixed four effects and hid this. This sweeps them one at a
> time and measures the Ku shape.
> 
>     py -3.14 scripts/ku_overshoot_test.py
> 

`scripts/native_reversal_entry.py`:

> What does native do with its falling trajectory when the pulse is truncated?
> 
> `native_st_vs_solved_2026-09-07` settled that native's stored Ku(t)/Kd(t) is the
> offline two-fixture solve, same shape to 0.4% of span. So native holds exactly one
> falling trajectory, recorded from a **fully on** pull-up, indexed by time since
> the edge -- the same thing we hold.
> 
> And the documented state mechanism (bracket V(out) between waveforms with
> different initial voltages) is dormant here: io_buf's .ibs carries exactly one
> pair per edge.
> 
> So native ought to have our defect. It does not -- its Ku sits +15 ps from the
> transistor under stress where ours sits +80. This asks what it actually does with
> the curve, by overlaying native's stressed Ku against its own full-swing falling
> Ku, aligned at the reversal:
> 
> * **replays from the start** -> stressed Ku jumps to the full curve's 1.0 and
>   follows it, and native has no state mechanism at all;
> * **enters partway** -> stressed Ku picks the full curve up at the value it had
>   reached, which is the entry condition working through some other route;
> * **scales** -> stressed Ku is the full curve multiplied down.
> 
>     py -3.14 scripts/native_reversal_entry.py
> 

`scripts/native_stress_law.py`:

> Is native IBIS's stressed-case behaviour predictable? Test the law out of sample.
> 
> On io_buf short_high, native IBIS under-swings the transistor by 60-124 mV and the
> error tracks how complete the transition was, with r = +0.94. That is one device
> and one direction -- enough to notice a pattern, not enough to call it a law.
> 
> This tests it on every device and direction available in the width-sweep family
> (io_buf, ex2, inv_chain; short_high and short_low). If native's error is a
> function of completion fraction across all of them, its stressed behaviour is
> predictable and can be corrected for rather than merely noted. If the slope or
> sign changes per device, it is not a law and the io_buf result was a coincidence.
> 
> Completion fraction is measured per device from its own largest observed
> excursion, so no external full-swing assumption is imported.
> 
>     py -3.14 scripts/native_stress_law.py
> 

`scripts/native_waveform_count_test.py`:

> Is the stress pedestal the difference between one V-T trajectory and two?
> 
> What is established about the pedestal (`pedestal_localization.py`,
> `delay_pedestal_test.py`):
> 
> * it is already present in Ku and Kd at the same size as in the pad, so it is
>   made upstream of the output stage;
> * on io_buf, native's Ku tracks the **transistor's own** Ku to +1..+19 ps while
>   ours is +64..+111 ps late -- our coefficient timing is the wrong one;
> * it is **not** the fitted command transport delays: scaled to 5% of nominal,
>   61 ps of the 85 survives, and the response is non-monotonic;
> * it is **not** the gate-state time constants: scaled to 5%, 95 ps survives.
> 
> Every timing parameter in the command layer has been ruled out. What is left is
> structural. Our Ku(t) is a **single fixed trajectory** played out by a scalar gate
> state, so the only thing the model knows at a reversal is "how far along" it is.
> HSPICE's B-element with `ramp_rwf=2` instead **interpolates between two recorded
> V-T waveforms using the actual pad voltage**, so it can represent a pad caught at
> an intermediate voltage.
> 
> That difference should vanish at full swing -- the pad is settled at the reversal,
> so there is nothing intermediate to represent -- and appear under stress. Which is
> exactly the pedestal's signature.
> 
> The test: run native with `ramp_rwf=1`, which forces it onto a single waveform
> like ours. If the pedestal is the one-trajectory limitation, native should acquire
> one too.
> 
>     py -3.14 scripts/native_waveform_count_test.py
> 

`scripts/pedestal_localization.py`:

> Where does the stress pedestal enter -- the coefficients, or the output stage?
> 
> `timing_shift_accumulation_2026-09-04` split the timing shift in two. The
> accumulating part is C_comp and is shared with native IBIS. What is left is a
> **constant pedestal that appears only under stress and is ours alone**: our pad
> runs +83..+99 ps later than native's on io_buf, and 12..41 ps *earlier* on
> inv_chain and ex2, where at full swing the two agree to 2-4 ps.
> 
> Nothing explains it. This localises it, the same way the full-swing lag was
> localised: the pad is built as
> 
>     pad  <-  Ku(t) x I_pu(V) + Kd(t) x I_pd(V) + clamps + C_comp dV/dt
> 
> so if the pedestal is already present in Ku(t) it is made upstream -- in the
> command layer, the gate state, or the table replay. If Ku(t) agrees and only the
> pad differs, it is made in the output stage.
> 
> No new simulation. The stress matrix already carries all three coefficient sets
> next to all three pads: `silicon_*` from the two-fixture solve on the transistor
> (ground truth), `hspice_*` from native's `xv_pu`/`xv_pd`, and `pybis_*` from ours.
> 
> Measure: the lag that best aligns one trace to another over the outward leg, by
> RMS. Reported with the residual after alignment, because a lag only describes the
> difference if the shapes match once shifted -- a large residual means the traces
> differ in shape and the number is not a delay.
> 
>     py -3.14 scripts/pedestal_localization.py
> 

`scripts/plot_stress_shapes.py`:

> What do the transistor and native IBIS actually DO under stress?
> 
> Everything measured on the stress cases so far has been scalar -- a 50% crossing
> and an RMSE. That hides the shape, and the shape turns out to matter, because
> these truncated pulses are *partial excursions*: on io_buf short_high the pad
> peaks at 0.57-1.22 V, which is 36-76% of the swing it actually reaches into this
> load. Note the reference -- the pad swings to ~1.6 V into 50 ohm, not to the
> 3.3 V supply, because the 50 ohm divider halves it. Comparing against 3.3 V (as
> I first did) makes these look far more truncated than they are.
> 
> Plotting them shows something the scalars never surfaced: **native IBIS
> systematically under-swings the transistor** on every width, by 60-124 mV, while
> pybis tracks the peak to within 3-29 mV. That matters for how defect B is stated,
> because a waveform that peaks lower reaches any fixed threshold at a different
> time, so part of the reported timing difference may be an amplitude difference
> read as one. That contribution is plausible but has not been quantified.
> 
>     py -3.14 scripts/plot_stress_shapes.py
> 

`scripts/predriver_stage_probe.py`:

> Where, inside the transistor buffer, does a short pulse stop being a pulse?
> 
> The matrix runs only recorded the last predriver node. This re-runs the same
> transistor decks (same stimulus, same load, hspice.mod) with EVERY internal
> stage probed, at full swing and at the five stressed widths, and asks two
> questions of each stage:
> 
> 1. **Stage by stage**: how far does each node get, and when, as the pulse walks
>    down the chain? The stage that first fails to complete is where the stressed
>    behaviour is born.
> 
> 2. **Is the stage linear?** A linear time-invariant stage answers a pulse with
>    the superposition of its own two full-swing step responses:
> 
>        P(t) = g_rise(t - t_on) + g_fall(t - t_off) - 1
> 
>    where g_rise / g_fall are the node's normalised responses to the full-swing
>    rising and falling input edges (measured in the full-swing run). Comparing
>    P(t) with the measured pulse response tests linearity with no model in the
>    loop. Where it holds, the right command structure is *the measured step
>    response itself*, and any linear filter (delay + RC, cascade) can only
>    approximate that. Where it fails, the failure's sign says what nonlinearity
>    is present (a slew-limited stage under-reaches; a regenerative one overshoots
>    the linear prediction).
> 
>     py -3.14 scripts/predriver_stage_probe.py            # all three devices
>     py -3.14 scripts/predriver_stage_probe.py --dev ex2
> 

`scripts/prep_kukd_animation_data.py`:

> Dump real numbers for the Ku/Kd extraction animation.
> 
> The animation should show the actual solve, not a sketch of it, so this pulls
> the two fixture waveforms that were already simulated, runs the same 2x2 solve
> the study uses, and records one representative instant in full detail.
> 
> Every number the animation shows has to be traceable on screen, so the dump
> carries more than the solve itself: the pullup and pulldown I-V curves the two
> multipliers are read off, and the term-by-term breakdown of each right-hand
> side. Otherwise a viewer sees four decimals appear with no origin.
> 

`scripts/prove_replay_equals_integrator.py`:

> One circuit, two gates: integrated and replayed, driving identical pads.
> 
> The question is small -- does replaying a fitted exponential from an inverted
> entry time give the same value as integrating it? -- and it does not need the
> production model to answer. Seven attempts to add this as another mode inside
> `create_ngspice_two_state_gate_input_control_netlist` (820 lines, 53 branches,
> 14 interacting flags) each failed on a coupling rather than on the physics.
> 
> So this builds the comparison standalone. Both gates live in one netlist, share
> one command, one transfer map and two identical pad stages, and are probed in a
> single run. Nothing here touches the production builder, so nothing in it can
> collide with those flags.
> 
>   gate A   integrated by ngspice:  dG/dt = (target - G) / tau
>   gate B   replayed:               invert to a table time at each edge, then
>                                    advance along the fitted curve
> 
> Gate B is computed in Python and played back as a PWL source. That is the
> honest division of labour: the replay *algorithm* runs where it can be checked,
> and ngspice does the integration and the circuit. The pad stage is lifted
> verbatim from the generated io_buf model, so both branches see the real I-V
> tables, clamps and C_comp.
> 
>     py -3.14 scripts/prove_replay_equals_integrator.py
> 

`scripts/pu_off_across_devices.py`:

> Does the pull-up off-delay explain the pedestal on the other two buffers?
> 
> On io_buf, scaling `pu_off` alone takes the stress pedestal from +73..+103 ps to
> about zero at every one of nine widths, with alignment residuals of 0.00-0.02, and
> *improves* the unstressed case at the same time (RMSE against the transistor
> 38.7 -> 20.1 mV, falling crossing +65.6 -> +1.7 ps).
> 
> io_buf's fit is also a striking outlier:
> 
>     device      PU on-delay   PU off-delay   ratio
>     io_buf         0.9926        0.0677      14.66
>     ex2            1.0015        0.6683       1.50
>     inv_chain      0.2684        0.2473       1.09
> 
> and io_buf is the one device whose pedestal is **positive** (ours later); on
> inv_chain and ex2 ours runs *earlier* than native. So the hypothesis is that the
> pedestal is the off-delay, and io_buf's sign and size come from its off-delay
> being 15x shorter than its on-delay where the others are near 1.
> 
> If that holds, the other two should respond to the same knob -- and, since their
> pedestal has the opposite sign, respond in the opposite direction.
> 
> Each device is run on its own bench and checked against the stress matrix's own
> `pybis_pad` column before anything is concluded, so a wrong load cannot be
> mistaken for a result.
> 
>     py -3.14 scripts/pu_off_across_devices.py
> 

`scripts/pu_off_conflict_sweep.py`:

> Is `pu_off` genuinely undecidable, or was three points just too few?
> 
> `pu_off_scale_2026-09-07` claimed the parameter cannot be derived because it sets
> two things at once -- when the gate decays, and the phase between the gate and the
> residual spike -- and they want opposite values. That was argued from three
> points (0.70 / 0.29 / 0.25) plus a mechanism read off the netlist. Three points
> cannot rule out an interior optimum that satisfies both.
> 
> This sweeps it properly. Two objectives, each measured against its own reference:
> 
> * **coefficient**  Ku rms against the transistor over +90..+400 ps from the
>   reversal, three widths. That window is grid-converged (spread 0.0012 against
>   0.0304 nearer the reversal, `silicon_kukd_conditioning_2026-09-07`), so the
>   reference is sound there.
> * **amplitude**    the full-swing reversal overshoot above the trace's own
>   settled plateau. The transistor's is +64.9 mV, native's +83.8.
> 
> If both objectives are monotone in `pu_off` and pull in opposite directions,
> there is no value that satisfies both and the claim stands. If either turns over,
> it falls.
> 
>     py -3.14 scripts/pu_off_conflict_sweep.py
> 

`scripts/pu_off_scale_derivation.py`:

> Re-derive PU_OFF_SCALE, which `residual_rescale_time_2026-09-04` got wrong.
> 
> That study set `pu_off` equal to the transistor's observed pull-up turn-around
> (48 ps), reasoning that our fitted 68 ps put ours at 69-77 so 68 x 0.70 = 48
> would land on it. It then dismissed x0.25 -- which scored far better -- as
> "compensating rather than fixing".
> 
> That derivation double-counts the input edge ramp. Measured on the corrected
> build (`ku_excess_decompose_2026-09-07`):
> 
>     pu_off 67.7 ps  ->  gate turns around at 96-98 ps
>     pu_off 47.4 ps  ->  gate turns around at 75-78 ps
> 
> A 20.3 ps change in `pu_off` moves the turn-around by 20 ps -- 1:1 -- on a
> constant offset of ~28.5 ps. That offset is the deck's own falling edge: the
> input takes 50 ps to cross, so the command sees it at +25 ps, and the T-line
> adds a few more.
> 
> So the turn-around is `pu_off + 28.5`, and landing it on the transistor's 47-51 ps
> needs `pu_off ~ 19.5 ps`, i.e. a scale of **0.29** -- not 0.70. x0.25 gives 45 ps,
> within 3 ps of the transistor. It was the measured answer all along.
> 
> This tests 0.70 against 0.29 and 0.25 on turn-around, Ku ratio, Kd, the stress
> pedestal and the unstressed control.
> 
>     py -3.14 scripts/pu_off_scale_derivation.py
> 

`scripts/pu_off_sweep.py`:

> Scale the pull-up off-delay: every stress level, and the unstressed control.
> 
> `ku_overshoot_test.py` found the pedestal by looking at the Ku *shape* rather than
> a fitted lag. Our Ku climbs past the reversal to 0.680 where native turns around
> at 0.508, and shortening `pu_off` alone brings the peak down (0.680 -> 0.544) and
> speeds the decay (345 -> 285 ps). On the pad at 1792 ps the pedestal against
> native falls monotonically:
> 
>     shipped      85 ps      pu_off x0.25    19 ps
>     pu_off x0.5  42         pu_off x0        0
> 
> with alignment residuals of 0.00-0.04 throughout, so the shape is kept rather than
> traded away. The earlier sweep concluded "not the delays" because it scaled all
> four together -- and `pu_on` pushes the other way (shortening it takes the Ku peak
> from 0.680 up to 0.954), so the two cancelled into a non-monotonic mess.
> 
> Two things decide whether this is a fix rather than a fluke:
> 
> * does it hold across the **whole stress family**, or only at 1792 ps;
> * does it damage the **unstressed** case, where the shipped model is already
>   within 2-4 ps of native.
> 
>     py -3.14 scripts/pu_off_sweep.py
> 

`scripts/pulse_train_accumulation.py`:

> Does the timing error accumulate over a train of stressed pulses?
> 
> Every stressed case so far is one pulse from a settled state. If the defect is
> state carry-over -- each event starting from where the previous one left the
> device -- then a train of pulses at 50% duty, where the pad never settles, should
> show the error growing (or not) pulse by pulse. One pulse cannot show that.
> 
> Three base buffers, transistor / native / ours, at one stressed width each and a
> full-swing control train. Per pulse k: the pad peak time of each model minus the
> transistor's, and the best-fit lag of each model onto the transistor over that
> pulse's own window. Plotted against k.
> 
>     py -3.14 scripts/pulse_train_accumulation.py
> 

`scripts/residual_depth_rule.py`:

> Scale the falling residual by the DEPTH the pad reached -- the 12/12 law -- instead of by GUP.
> 
> `cross_device_stress_2026-09-08` and the three open-drains found the same law on
> every buffer: the transistor's falling residual (its Kd minimum after the reversal)
> shrinks toward zero in proportion to how far the output got. Ours is a constant
> calibrated on a complete transition. The io_buf correction (`FRAC`, a peak-hold
> on GUP) scaled it by the *gate* state instead, and was measured 2.4x too steep.
> 
> This tests the law directly. Three builds per stressed case:
> 
>     shipped      the residual at full size
>     frac_gup     scaled by GUP held at the reversal      (the io_buf correction)
>     frac_depth   scaled by  pad peak / full-swing plateau (the measured law)
> 
> The plateau is the model's own settled full-swing level, so the scale is 1 at
> full swing by construction. Scored against the transistor: pad peak error, lag,
> and the Kd residual (rms and minimum) over the grid-converged window past the
> pad peak. On io_buf the +1.8 ns bump amplitude is reported too, since the earlier
> FRAC halved it by staying applied too long.
> 
>     py -3.14 scripts/residual_depth_rule.py --variant io_buf
> 

`scripts/residual_reindex_test.py`:

> Change only the residual table's index, from the stopwatch to the gate state.
> 
> Our Ku is built from two pieces added together:
> 
>     KUGATE_BASE = pwl(V(GUP), ...)        indexed by the GATE STATE
>     KURES_TABLE = pwl(V(HNX), ...)        indexed by HNX, time since the input edge
>     Ku = KUGATE_BASE + KURES_TABLE
> 
> The first already carries a partial transition correctly -- GUP is continuous, so
> a truncated pulse leaves it at 0.54 rather than 1.0 and the map reads the right
> value. The second is a correction table read off a **stopwatch that resets to zero
> at every input edge**, so it applies the correction for a transition that began
> from fully settled even when it did not.
> 
> `v_indexed_prototype_2026-09-04` showed that entering the reverse trajectory where
> the coefficient already is takes Kd from +191 ps to +1 ps against the transistor.
> This tests whether the residual's index is where that belongs, by changing **only**
> that and nothing else.
> 
> The re-index needs no latch and no per-edge reset. On a complete transition the
> model's own gate state traces out GUP(HNX); inverting it gives an
> equivalent-elapsed-time as a static function of the gate state:
> 
>     HNX_eff = pwl(V(GUP), <inverse of the recorded GUP(HNX)>)
> 
> On a complete transition that reproduces HNX exactly, so the unstressed cases
> cannot regress by construction. On a truncated one it enters partway.
> 
> Step 1 runs the unmodified model at full swing to record GUP(HNX) and GDN(HNX).
> Step 2 patches the four residual tables. Step 3 measures, stressed and unstressed.

`scripts/residual_rescale_time_test.py`:

> Scale the falling residual in amplitude **and** in time.
> 
> `residual_scaled_2026-09-04` established that the stress pedestal is the falling
> residual applied at full size to a half-completed transition: ours is 2x too
> negative on Kd (-0.171 against the transistor's -0.085 at +96 ps) and the factor
> the data demands is ~0.57, essentially constant, against a GUP of 0.498 at the
> reversal.
> 
> But a pure amplitude scale leaves a second error. Reading the tables directly:
> 
>     KURES_F   +0.183 at HNX 0.03, back to ~0 by 0.10 ns      a short sharp spike
>     KDRES_F   -0.160 at 0.06, -0.079 at 0.20, -0.038 at 0.50  a long tail
> 
> and the transistor's Kd is back to zero by 507 ps where ours is still at -0.040.
> 
> Both tables describe a **complete** fall. A fall that only got fraction `f` of the
> way is smaller *and* shorter -- so the correction has two parts, not one:
> 
>     amplitude   x f
>     time        read the table at HNX / f
> 
> If a complete fall takes T, a fall from fraction f takes about f*T. At elapsed
> time `tau` we are `tau/(f*T)` through our fall; the table at `s` is `s/T` through
> its own. Matching those gives `s = tau/f`.
> 
> `f` is GUP at the reversal, held by the peak detector so it does not decay with
> GUP during the fall. At full swing f = 1 and both parts are the identity, so the
> unstressed case cannot move by construction -- the property the earlier
> gate-state re-index claimed and did not have.
> 

`scripts/residual_scaled_test.py`:

> Scale the falling residual by how far the transition actually got.
> 
> Decomposing Ku into its two parts across a reversal (`ku_decompose_2026-09-04`)
> localises the pedestal exactly:
> 
>     t-rev      Ku    gate part   residual
>      -100    0.433     0.436      0.000
>        -4    0.476     0.479     -0.001
>       +69    0.680     0.513     +0.173     <- the whole excursion is here
>      +199    0.250     0.241     -0.001
> 
> The gate part is smooth through the reversal. The **residual** is zero all through
> the transition and then fires +0.173 -- a quarter of the total Ku -- in about
> 70 ps.
> 
> It is not misfiring. Its own table says so:
> 
>     KURES_F at HNX =  0.0    0.006   0.012   0.018   0.024   0.030
>                     -0.056  -0.102  -0.092  +0.088  +0.158  +0.183
> 
> The falling residual really does rise to +0.18 early in a fall. It has to: it
> corrects the gate map's lag at the start of a fall **from fully on**, where the
> true Ku is 1.0 and the map has not caught up.
> 
> On a truncated pulse we are falling from **0.48**, not 1.0 -- and the correction
> is applied at full size regardless. That is the defect: a correction measured for
> a complete transition, applied unscaled to a partial one.
> 
> The fix follows directly and needs no latch: scale the falling residual by the
> gate state, which *is* how far the transition got. On a complete fall GUP is 1.0

`scripts/silicon_kukd_conditioning.py`:

> Is the transistor's stressed Ku near a reversal an artifact? Prove it or drop it.
> 
> `pu_off_scale_2026-09-07` claimed the transistor's stressed Ku peak (1.2892 at
> +49 ps on io_buf 1792 ps, from a pull-up that entered the fall at 0.48) is a
> solve artifact and cannot anchor a delay. That claim was made on plausibility --
> "a pull-up that entered at 0.48 does not reach 1.29" -- not on a measurement.
> 
> It also sits against a standing negative result: `two_fixture_conditioning.py`
> found io_buf's *characterisation tables* well conditioned (2.7 median, 3.1 max).
> But that is a different solve. The stressed silicon coefficients come from two
> transistor runs under the stressed stimulus, and conditioning there depends on
> those trajectories, not on the recorded tables.
> 
> `solve_silicon_kukd` already returns cond(M) in column 3, and its own comment
> names the mechanism: the two fixtures stop giving independent information
> whenever both devices are nearly off. This reads it out at the reversal.
> 
> The test is falsifiable in both directions:
> 
> * cond spikes where Ku spikes  -> artifact confirmed, the claim stands;
> * cond stays low               -> the Ku excursion is real and the claim is wrong.
> 
>     py -3.14 scripts/silicon_kukd_conditioning.py
> 

`scripts/silicon_map_replay.py`:

> Real gate in, and the Ku/Kd maps taken from the transistor instead of the IBIS tables.
> 
> `gate_replay_prototype.py` feeds the model the transistor's real gate and keeps
> the maps the shipped model implies: Ku(g) is "the IBIS Ku(t) at the moment the
> real full-swing gate passed g". On inv_chain that under-drives the stressed pad
> by up to 54 %, although Ku is a single-valued function of the gate within every
> stressed event (loop <= 0.1). So either the map's shape is wrong, or the output
> stage is not a static map. This decides it.
> 
> The map is now the transistor's own two-fixture Ku(t)/Kd(t) plotted against its
> own gate, either
> 
>     --source full     at full swing (two new fixture runs, rise 5 ns, fall 15 ns)
>     --source stress   inside the middle stressed event (the matrix fixture runs)
> 
> and the stressed widths are replayed as before. If the silicon map reproduces
> the stressed pad, the output stage IS a static map of the gate and the IBIS
> tables place Ku wrongly against the gate for a fast gate. The map values are
> printed side by side so the difference can be read directly.
> 
>     py -3.14 scripts/silicon_map_replay.py --variant inv_chain --ccomp 0.6 --source full
> 

`scripts/stress_amplitude_survey.py`:

> Amplitude survey of stressed cases: transistor vs native IBIS vs pybis.
> 
> Pure analysis -- every waveform already exists on disk, nothing is re-simulated.
> 
> Two things this fixes over the first pass:
> 
> * **Direction-aware excursion.** `short_high` starts low and makes a brief
>   excursion up; `short_low` rises to a plateau and then makes a brief dip back
>   down. Measuring `min()` over the whole trace, as I did first, returns the
>   initial rest level for `short_low` rather than the dip, which is why those
>   families looked like they had no dynamic range.
> * **The depth-target family.** Defect B was quoted on depth-target cases, and
>   only the width-sweep family had been measured. Both are covered here.
> 
> The excursion is measured identically for all three builds, so the comparison
> does not depend on what `depth_target` is a fraction of.
> 
>     py -3.14 scripts/stress_amplitude_survey.py
> 

`scripts/timing_shift_accumulation.py`:

> Does the timing shift accumulate *within* one event, or is it a fixed offset?
> 
> Every timing number in this study so far is **one crossing per case**, almost
> always the 50% point. That cannot distinguish a model which is uniformly N ps
> late from one which starts aligned and falls progressively further behind as the
> transition proceeds. Those are different defects with different causes.
> 
> Method: crossing times at 10%, 15% ... 90% of the **transistor's own** excursion,
> model minus transistor, taken separately on the way *into* the event and on the
> way *out* of it. A fixed offset gives a flat ladder; accumulation gives a sloped
> one.
> 
> "Into" and "out" rather than "rising" and "falling", because the two directions
> are mirror images: a `short_high` pulse goes up into the event and comes back
> down, a `short_low` pulse dips down into it and comes back up. The interesting
> side turned out to be the way *out*, on both.
> 
> Three devices, both directions, plus an unstressed full-swing control wherever
> one exists on disk. The control is what separates "our model does this" from
> "IBIS does this": if native drifts by the same amount on a clean transition, the
> accumulation is not ours.
> 
>     py -3.14 scripts/timing_shift_accumulation.py
> 

`scripts/v_indexed_coefficient_probe.py`:

> Would indexing the coefficient by pad voltage instead of time actually help?
> 
> `native_waveform_count_2026-09-04` found the stress pedestal: our Ku(t) is one
> recorded curve played out against a **clock** (time since the input edge), where
> native with two V-T tables tracks the transistor's Ku to +13 ps under stress and
> ours is +80 ps late. Forcing native onto one table gives it the same +75 ps, so
> the defect is the single time-indexed trajectory.
> 
> Before building a SPICE model, this asks the cheap question offline: if the same
> Ku curve were looked up by **pad voltage** instead of by elapsed time, would it
> land closer to the transistor's Ku on a stressed pulse?
> 
> How:
> 
> 1. Take pybis's own `solve_k_params_output` for the rising and falling
>    transitions -- Ku(t), Kd(t), exactly what the model ships with.
> 2. Take the V-T waveform those were solved from, giving V(t) over the same
>    time base. Eliminating t between them gives **Ku(V)** and **Kd(V)** -- the
>    same coefficients, re-indexed.
> 3. On a stressed case, evaluate Ku(V) at the pad voltage the model actually
>    reaches, choosing the rising or falling branch by which transition is in
>    progress.
> 4. Compare that against the transistor's own Ku, and against what the shipped
>    time-indexed model produces.
> 
> If the V-indexed version is not closer, there is nothing to build.
> 
>     py -3.14 scripts/v_indexed_coefficient_probe.py
> 

