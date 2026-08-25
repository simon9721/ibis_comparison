# Ku/Kd animation — feedback log

A running record for `scripts/animate_kukd_extraction.py`. Each round of
feedback is kept verbatim, with what was actually changed underneath it, so a
point that comes back a second time is visibly a second time.

---

## Round 1 — 2026-08-25

this is a good start, few feedbacK:
1. the subtitle 'the transistor has no ku/kd...' is not useful, remove it
2. the first scene 'how ku/kd are extraced': don't just show equation, but also diagram like scene two.
3. scene two 'drive a buffer through...' is great, i like it.
4. scene three 'at one instant...' i see you show two euqations and two unknowns, but the origin of the numbers in the two equations are not clear, viewer can get lost (-0.606/0.0457/-0.404/0.0725, and the current)
5. the last scene you have 'the coefficients silicon actually require', that's just confusing.
6. you mentioned this machine don't have latex, can you install latex so that we can have better equation render (if that will help)?

### Response

**1. Subtitle — removed.** The title now stands alone and the scene moves
straight to the schematic.

**2. Act 1 now opens on a diagram.** A drawn IBIS output stage: VCC and GND
rails, the pullup and pulldown I-V blocks tagged `x Ku` and `x Kd` in their own
colours, C_comp on its own branch, all meeting at one pad node. The equation
comes in underneath it, so each term is visibly one branch of the node rather
than a symbol. Colours carry through to the coefficient curves in the last act.

**3. Act 2 — untouched.**

**4. The origin of every number is now its own act.** This was the real gap: four
decimals used to arrive with no provenance. The act is now built as two worked
passes, one per fixture, each showing all three sources:

- *the multipliers* — the pad waveform is read at the chosen instant
  (V = 0.327 V), a dashed line carries that voltage across to the IBIS I-V
  tables plotted beside it, and a cursor there drops onto both curves. Those two
  intersections **are** the two multipliers: I_pu = −60.57 mA, I_pd = +45.73 mA.
  The curves are the real tables from the IBIS file, read with the same call the
  per-timestep solve uses.
- *the right-hand side* — assembled term by term rather than asserted:
  `(V_fix − V)/R = (0.000 − 0.327)/50 = −6.55 mA`, then
  `C_comp·dV/dt = 0.468 pF × 41.3 V/ns = +19.35 mA`, then the sum, −25.89 mA.
  This buffer has no clamps, so those two terms are the whole of it, which is
  what makes the case worth showing: the right-hand side is not measured, it is
  everything in the pad current that is already known.
- *the equation* those three numbers make, which then parks at the side.

The second fixture repeats the same three steps at ~0.6× the pace, since by then
the viewer knows the moves. Only after both rows exist does the solve happen.

Currents are now shown in **mA** rather than amps. `−0.0605697 A` at projector
distance is unreadable; `−60.57 mA` is not. The solve is unchanged.

**5. Closing line — replaced.** "the coefficients silicon actually requires" is
gone. It now reads *"Ku and Kd say how much of each device is on, at every
instant"*, which states what the two curves mean instead of gesturing at why
they matter.

**6. LaTeX — installed.** See the note below; the script renders either way.

### On the LaTeX question

Worth being straight about how much it buys. The equations here are small —
one display equation, two numeric rows, two answers — so LaTeX improves
subscripts, the `dV/dt` fraction, and spacing, and changes nothing structural.
It was cheap enough to be worth having, and the fallback keeps the scene
buildable on a machine without it.

What went in: **TinyTeX**, not MiKTeX or full TeX Live. There is no `winget`,
no `choco`, and no existing TeX on this machine, and TinyTeX is ~100 MB more
modest than the alternatives.

Four things bit, all recorded so they don't cost time again:

- The vendor's `install-bin-windows.bat` has a cmd operator-precedence bug:
  `where /q powershell || echo PowerShell not found && exit /b` runs `exit /b`
  even when PowerShell *is* found, because `&&` binds to the whole preceding
  chain. It exits instantly and silently. Run the `.ps1` it downloads directly.
- **`%APPDATA%` on this machine is a redirected network share**, which is where
  TinyTeX installs by default. `tlmgr` there ran at roughly 350 KB/min and would
  have taken hours just to fetch the package database. The fix was to robocopy
  the 292 MB tree to `%LOCALAPPDATA%\TinyTeX` and run `tlmgr` from the copy: TeX
  Live derives its root from the binary's own location, so the tree relocates
  without reinstalling, and `tlmgr` immediately reported the new root. The same
  install then finished in about ten seconds. Anything else set up here that
  writes heavily under `%APPDATA%` will hit the same wall.
- manim's default TeX template pulls in a dozen packages (tipa, wasysym,
  physics, calligra, doublestroke…) that a small distribution does not ship.
  Rather than install all of them, the script defines its own minimal
  `TexTemplate` with amsmath and amssymb only. Beyond base TinyTeX that needs
  only `dvisvgm`, `standalone` and `preview` — amsmath and amsfonts were already
  present.
- `set_color_by_tex` does nothing useful on a single-string `MathTex`: there is
  only one submobject, so it recolours the whole equation rather than the
  matched term, and the last call wins. `tex_to_color_map` isolates the
  substrings into their own submobjects first, which is what lets Ku stay red
  and Kd green inside an otherwise orange row.

One real consequence for layout: **typeset maths is wider than the unicode
fallback** — wide enough that act 4's working block and its equation overlapped
once TeX was on. Both are now capped by measured width rather than by a font
size picked against whichever mode happened to be active.

The script detects TeX itself: it adds TinyTeX's bin directory to `PATH` (the
installer puts it somewhere the render process would not otherwise look), then
checks for both `latex` and `dvisvgm`. If either is missing it falls back to
unicode `Text` and still builds. `KUKD_NO_TEX=1` forces the fallback, which is
also the fast path for checking layout.

---

## Structure as it stands

| act | what it does |
|-----|--------------|
| 1 | the IBIS output stage as a schematic, then the equation, Ku and Kd marked as the only unknowns |
| 2 | one fixture, one recorded pad waveform → one equation, two unknowns |
| 3 | second fixture → two equations, two unknowns |
| 4 | every number in both equations, read off the I-V tables or assembled from the known pad current |
| 5 | the 2x2 solve → Ku = 0.495, Kd = 0.090 |
| 6 | repeat at every timestep; Ku(t) and Kd(t) trace out |

## Provenance

`scripts/prep_kukd_animation_data.py` pulls the two fixture waveforms already
simulated for inv_chain short_high w135ps, runs the same 2x2 solve the study
uses, and dumps `results/kukd_animation/data.json`. Nothing in the animation is
drawn freehand: the waveforms, the I-V curves, the four multipliers, both
right-hand sides and the solved pair all come from that file.

The worked instant is chosen as the timestep where Ku is nearest 0.5, so both
devices carry real current and neither term dominates. It checks by hand:
0.4953 × (−60.57 mA) + 0.0898 × (45.73 mA) = −25.89 mA.

## Commands

    py -3.14 scripts/prep_kukd_animation_data.py          # data (project deps are on 3.14)
    py -3.13 -m manim -qh scripts/animate_kukd_extraction.py KuKdExtraction
    py -3.13 scripts/grab_kukd_stills.py                  # slide stills from the render
    KUKD_NO_TEX=1 py -3.13 -m manim -ql ...               # fast layout check

manim lives on Python 3.13 and the project's vendored numpy is built for 3.14,
so the two halves deliberately run on different interpreters.

`grab_kukd_stills.py` holds a named time per act. Those times are placed by hand
against the finished render rather than computed, because the act boundaries are
the sum of a few dozen `run_time`s and a still that lands mid-fade is useless.
Retime them if the pacing changes.
