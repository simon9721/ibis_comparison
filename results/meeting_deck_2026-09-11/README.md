# meeting_deck_2026-09-11

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 13M, 31 files, written 2026-09-11 to 2026-09-18
- location before archiving: `results/meeting_deck_2026-09-11`

## Contents (top level)

```
0911_Simon_IBIS_updated.pptx                       5.6M
figures/                                           6.8M  29 files
od_ccomp3.ibs                                      288K
```

## Produced by

`scripts/build_0911_deck.py`:

> Update the 2026-09-11 deck. Inserted, in order:
> 
>   after 'Fix from last time' (old 6):  the cmd_clean command slide
>   after 'New fix: result' (old 8):     two identical pulses (does the error accumulate?)
>   old 9 'More SPICE buffer mockups' -> variant table (open-drain included)
>   after it:                            six variant slides, message titles, + wrap-up
>   after the wrap-up:                   four open-drain slides
> 
> Each picture slide has a 'How to read it' box and a 'What it shows' box (and the same text in
> the speaker notes). Everything else in the deck is untouched.
> 
>     py -3.14 scripts/build_0911_deck.py --src <path to 0911_Simon_IBIS.pptx> --out <path>
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

`scripts/build_od_slide_figures.py`:

> Open-drain slides: full swing and stressed cases, transistor vs native vs our builds,
> pad and Kd on the same axes. Drawn from existing runs:
> 
>     transistor, native   results/opendrain_gatestate_2026-09-10/base/w*/{transistor,native}
>     ours, legacy build   results/opendrain_stress_2026-09-08/w*/ours          (before 2026-09-10)
>     ours, gate-state     results/opendrain_gatestate_2026-09-10/base/w*/ours  (converter now)
>     ours, chain          results/opendrain_chain_2026-09-10/base_c3_calib680_odprior/w*  (recipe)
> 
>     py -3.14 scripts/build_od_slide_figures.py
> 

`scripts/build_stage_walk_figures.py`:

> The transistor's internal stages probed, one figure per buffer, same size and layout for
> the full-swing and the stressed case so the two can be read against each other.
> 
>     --full        a long-enough input pulse (ex2 3 ns, inv_chain 1 ns, io_buf 10 ns): every
>                   stage completes its leg on both edges
>     (default)     the short pulse whose pad reaches --target of full swing (0.70)
> 
> Reads the probe runs of `predriver_stage_probe.py` (and `build_full_swing_probes.py` for the
> shorter full-swing pulses); nothing is re-simulated. Every node is normalised to its own full
> swing, 0 = rest, 1 = fully on, and `pad_sp` / `in_dig` are labelled `pad` / `input`.
> 
>     py -3.14 scripts/build_stage_walk_figures.py [--full] [--target 0.70]
> 

`scripts/two_pulse_probe.py`:

> Two identical stressed pulses: does the second one carry the first one's error?
> 
> Same benches as the pulse train (`pulse_train_accumulation.py`), same three builds
> (transistor, native HSPICE IBIS, ours = cmd_clean), two pulses of the same width W with
> a gap G between the first falling edge and the second rising edge:
> 
>     settled    G = 6 ns, the pad and every internal node have returned to rest
>     unsettled  G = W, 50 % duty, the second pulse lands on the tail of the first
> 
> Per pulse: model pad-peak time minus the transistor's, and the best-fit lag.
> 
>     py -3.14 scripts/two_pulse_probe.py
> 

