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

---

# Update: repeated on the depth-target family — defect B's own cases

The width-sweep result above left two things unresolved: whether the level-driven
build behaves the same on defect B's actual cases, and whether the 24 ps I
measured versus the quoted 69–99 ps was a reference-level artifact or a family
difference. Both are now settled, because the depth family turns out to carry
both builds:

- `_baseline_edgecmd` — edge-integrating, all 14 depth cases
- `_diag_level` — level-driven, all 5 io_buf depth cases

io_buf, depth-target, timing at 50% of each case's own transistor excursion:

| case | edge-cmd | level-cmd | closer |
|---|---:|---:|---|
| short_high depth43 | 28.5 ps | 38.1 ps | edge |
| short_high depth86 | **72.4 ps** | 90.8 ps | edge |
| short_low depth20 | 34.3 ps | 50.2 ps | edge |
| short_low depth56 | 31.3 ps | 45.0 ps | edge |
| short_low depth63 | 34.8 ps | 50.7 ps | edge |
| **mean** | **40.3 ps** | **55.0 ps** | |

**Level-driven better on 0 / 5.**

## 1. The result holds on the right cases

The level-driven command does not fix the timing shift on defect B's own family
either — it is worse on all five, mean 40.3 -> 55.0 ps. Together with 0/14 on the
width family, that is 0 for 19. **The offset and the timing shift are separate
mechanisms**, and removing the stranded charge does not touch the timing.

## 2. Correcting my "reference artifact" explanation

I attributed the gap between my 24 ps and the quoted 69–99 ps mainly to the
reference level. **That was mostly wrong.** Measuring the depth family with the
*same* excursion-relative reference gives mean 40.3 ps and max 72.4 ps — the max
landing inside the quoted range.

So the difference is mainly **family, not reference**: the depth-target cases
genuinely carry larger timing shifts than the width-sweep cases. Reference choice
still matters, but it is the smaller term.

## 3. Consolidating on the depth family

Everything the width family was used for is available on the depth family, which
is the better standard: it is parameterised by output excursion, so a case means
the same thing across devices, and it is the family defect B was quoted on.

The one thing the width family has that the depth family does not is breadth of
method builds — `stress_method_matrix` carries 19 of them (gate_state, delay_cmd,
predriver_cmd, legacy, hybrid, pad_match ...) against the depth family's three.
So method surveys still need the width family; anything about *defect B itself*
should use the depth family.

