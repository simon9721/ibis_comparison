# Does delay_cmd fix the timing shift? No — and the shift is smaller than quoted

Two questions answered, one of them not the one I set out to answer.

## 1. delay_cmd does not fix the timing. The two defects are separate.

The hypothesis was that the offset and the timing shift share a mechanism:
`GUPCMD` is an open-loop integrator with no DC path, so a truncated pulse strands
charge; the offset is that residue in the settled level, and the timing shift
might be the same residue delaying the next transition. If so, `delay_cmd` --
which is level-driven, returns the command to exactly zero and strands nothing --
should fix both. It fixes the offset (63.9 -> 3.7 mV at reversal).

Measured on the 14 io_buf cases present in both builds:

| | gate_state (edge-integrating) | delay_cmd (level-driven) |
|---|---:|---:|
| mean \|shift\| | **24.1 ps** | **26.5 ps** |
| max \|shift\| | 33.9 ps | 35.0 ps |
| better on | 14 / 14 | **0 / 14** |

`delay_cmd` is *slightly worse on every case*, by 0.6 to 5.1 ps.

**So the two defects do not share a mechanism.** Removing the stranded charge
removes the offset and leaves the timing shift untouched. That closes a
hypothesis that had been carried as the leading explanation, and it means the
timing shift needs its own root cause — the command layer's charge accounting is
not it.

## 2. The shift is 18–35 ps here, not the 69–99 ps quoted

Every case measures between +18 and +35 ps, both builds, consistently late.
Defect B was quoted at 69–99 ps.

The difference is the **reference level**. These stressed events are partial
excursions, so a fixed fraction of the full rail is not a safe threshold — on some
cases it is never crossed at all. Here timing is taken at **50% of each case's own
transistor excursion**, applied identically to every build, which is the
defensible choice when the excursion varies case to case.

Measured that way the shift is roughly a third of the headline figure. That does
not make it vanish — the model is genuinely late, consistently, on all 14 — but
**a large part of the quoted magnitude is a measurement-reference artifact rather
than model error.**

## Caveat on comparability

This is the **width-sweep** family. Defect B was quoted on the **depth-target**
family. The 24 ps here and the 69–99 ps there are therefore not a strict
like-for-like, and the gap could be family as well as reference level. What is
strictly like-for-like is the gate_state vs delay_cmd comparison in section 1,
since both were measured on the same cases with the same method.

## What this leaves open

- The timing shift now has **no candidate mechanism**. Stranded charge is ruled
  out; the fitted onset delays were already ruled out (they would show on full
  swing, and do not).
- Re-measuring defect B's own five depth-target cases with the excursion-relative
  reference, to separate how much of 69–99 ps is family and how much is reference.
- `delay_cmd` being slightly *worse* on timing while much better on amplitude is
  itself unexplained, and the penalty grows with pulse width on short_low
  (−0.6 ps at 163 ps to −5.1 ps at 307 ps).

## Files

- `scripts/delay_cmd_timing_test.py`
