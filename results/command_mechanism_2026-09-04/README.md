# command_mechanism_2026-09-04

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 20M, 9 files, written 2026-09-04 to 2026-09-04
- location before archiving: `results/command_mechanism_2026-09-04`

## Contents (top level)

```
command_mechanism.csv                              6.5M
delay_cmd/                                         6.4M  4 files
gate_state/                                        7.0M  4 files
```

## Produced by

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

`scripts/probe_command_mechanism.py`:

> Probe the command node of both builds, so how delay_cmd works can be shown.
> 
> The difference between the two is one line of the generated subcircuit:
> 
>     gate_state   CGUPCMD GUPCMD 0 {gate_c} ic=0            a capacitor
>                  RGUPCMD GUPCMD 0 1e15                     across 1e15 ohm
>                  BGUPCMDON  I = -{gate_c}*V(PUONP)/edge_delay   a packet per edge
>     delay_cmd    BGUPCMD GUPCMD 0 V = V(PUCMDLVL)          driven by the level
> 
> The first integrates a fixed packet of charge on every input edge and has no
> resistive path to remove it, so a truncated pulse leaves some behind. The second
> is a function of the present input level, so it returns to exactly zero.
> 
> That is the whole mechanism, and it is visible directly on the command node --
> but nothing in the study had ever plotted the two side by side. This runs both
> builds on one truncated io_buf pulse and saves the command, the gate state it
> drives, Ku, and the pad, so the chain can be shown rather than asserted.
> 
>     py -3.14 scripts/probe_command_mechanism.py
> 

