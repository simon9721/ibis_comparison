# cmd_clean_slides_2026-09-04

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 5.2M, 4 files, written 2026-09-04 to 2026-09-04
- location before archiving: `results/cmd_clean_slides_2026-09-04`

## Contents (top level)

```
cmd_clean/                                         5.2M  4 files
```

## Produced by

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

