# delay_pedestal_2026-09-04

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 15M, 48 files, written 2026-09-07 to 2026-09-07
- location before archiving: `results/delay_pedestal_2026-09-04`

## Contents (top level)

```
delay/                                             5.0M  16 files
tau/                                               5.0M  16 files
x0p05/                                             1.3M  4 files
x0p25/                                             1.3M  4 files
x0p5/                                              1.3M  4 files
x1/                                                1.3M  4 files
```

## Produced by

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

