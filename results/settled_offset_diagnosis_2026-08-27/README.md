# settled_offset_diagnosis_2026-08-27

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 69M, 103 files, written 2026-06-04 to 2026-08-31
- location before archiving: `results/settled_offset_diagnosis_2026-08-27`

## Contents (top level)

```
01_command_to_pad.png                              340K
02_command_clamp.png                               200K
03_offset_chain.png                                292K
04_offset_fix.png                                  308K
05_delay_cmd_dead_zone.png                         272K
06_offset_eventually_settles.csv                   4.0K
06_offset_eventually_settles.png                   184K
07_full_event_kukd_pad.csv                          24K
07_full_event_kukd_pad.png                         188K
08_comprehensive_offset_chain.csv                  620K
08_comprehensive_offset_chain.png                  352K
09_comprehensive_offset_fix_comparison.csv         964K
09_comprehensive_offset_fix_comparison.png         408K
10_offset_fix_tail_zoom.png                        372K
11_pad_voltage_fix_comparison.png                  224K
12_gup_ku_fix_comparison.png                       164K
12_gup_pad_fix_comparison.png                      292K
13_offset_removed_by_level_command.png             376K
all_cases/                                         5.2M  40 files
command_probe/                                     3.8M  6 files
explainers/                                        344K  2 files
fix_probe/                                         5.1M  10 files
full_event_fix_probe/                               20M  4 files
full_event_probe/                                   30M  4 files
full_event_transistor_kukd/                        436K  19 files
```

## Produced by

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

`scripts/build_command_clamp_figure.py`:

> The clamp between the command capacitor and the gate, and what it hides.
> 
> `GUPTARGET` is `min(max(GUPCMD, 0), 1)`. The shipped decks save only the
> clamped node, which is exactly the wrong one for asking whether the command is
> correct: an error that pushes GUPCMD below zero is erased by the clamp and the
> case reads clean. Probing the unclamped node on the five io_buf short-high
> targets shows all five commands are corrupted, not three.
> 
> Reads the slim CSVs written by ``extract_command_probe.py``; the raw ngspice
> records are ~100 MB and are not kept.
> 
>     py -3.14 scripts/build_command_clamp_figure.py
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

