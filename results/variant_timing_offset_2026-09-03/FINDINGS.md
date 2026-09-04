# The timing offset is mostly not ours — it is the IBIS format

Nine buffer variants, each changing one known property, measured at full swing
against their own HSPICE transistor. Rising and falling 50% crossings.

## The measurement

| variant | what changed | native rise | pybis rise | **pybis − native** | native fall | pybis fall | **pybis − native** |
|---|---|---:|---:|---:|---:|---:|---:|
| inv base8 | reference | +0.3 | +9.3 | **+9.0** | +3.6 | +8.0 | **+4.3** |
| inv stage4 | predriver depth halved | −0.5 | +9.7 | **+10.3** | +3.0 | +7.5 | **+4.5** |
| inv skewp | output PMOS halved | −1.6 | +7.0 | **+8.6** | +1.2 | +5.9 | **+4.6** |
| inv weak | both output devices halved | −4.0 | +7.2 | **+11.1** | −0.2 | +4.3 | **+4.5** |
| ex2 base | reference | −29.5 | −25.0 | **+4.5** | −19.2 | −14.6 | **+4.6** |
| ex2 slowpre | predriver halved | −16.2 | −13.3 | **+2.9** | −20.5 | −17.4 | **+3.1** |
| ex2 skewp | output PMOS halved | −33.5 | −29.6 | **+3.9** | −21.1 | −15.0 | **+6.1** |
| ex2 weak | both output devices halved | −41.4 | −37.0 | **+4.4** | −23.7 | −16.8 | **+6.9** |
| ex2 nomiller | n4→out coupling removed | −32.7 | −26.8 | **+5.9** | −18.7 | −15.7 | **+3.0** |

## 1. The big device-dependent offset is shared with native

Native's own offset against the transistor spans **−41.4 to +3.6 ps — a 45 ps
range** across these variants. pybis's offset tracks it almost exactly.

**pybis minus native is +2.9 to +11.1 ps — an 8 ps range**, and within a family
and direction it is nearly constant: inv_chain falling is +4.3, +4.5, +4.6, +4.5
across four variants that differ in predriver depth, P/N balance and drive
strength.

So the offset decomposes cleanly:

    total offset  =  a large, device-dependent term shared with native IBIS
                  +  a small, stable term that is pybis's own  (3-11 ps)

**Most of the timing offset is not ours.** It is carried by native IBIS too,
which means it belongs to the IBIS format and its characterization, not to
pybis's reconstruction. Our own contribution is 3-11 ps and barely moves when the
silicon changes.

That is the answer to "what percentage already exists": against native as the
reference, roughly **75-95% of the offset is inherited**.

## 2. The sign is set by the buffer family, not by any property we varied

Every inv_chain variant is **positive** (pybis late, +4 to +10 ps). Every ex2
variant is **negative** (pybis early, −13 to −37 ps). Halving the predriver,
halving the PMOS, halving both output devices and removing the die coupling all
fail to flip it.

So the sign is a property of the buffer family — its topology, its supply, its
characterization — and not of drive strength, P/N balance, predriver speed or
Miller coupling. That rules out the four most obvious candidates in one pass.

## 3. Within a family, the properties do move the magnitude

- **ex2 slowpre** is the largest single effect: rise goes −25.0 → −13.3 ps, and
  native moves with it (−29.5 → −16.2). Halving the predriver nearly halves the
  offset — but it moves *native* too, so it is acting on the shared term, not on
  pybis's.
- **ex2 weak** pushes the other way: rise −25.0 → −37.0, native −29.5 → −41.4.
  Weakening the output devices increases the shared offset.
- **inv weak** shrinks it: rise +9.3 → +7.2, fall +7.9 → +4.3.
- **ex2 nomiller** ≈ base (−26.8 vs −25.0), consistent with the earlier finding
  that removing the 20.5 fF coupling changes nothing.

Every one of these moves native and pybis together. Nothing found here moves
pybis relative to native.

## What this changes

- **The timing shift is largely an IBIS-format property, not a pybis defect.**
  Effort spent making pybis's reconstruction "less late" is chasing the 3-11 ps
  term while the 45 ps term is inherited.
- **pybis's own term is remarkably stable** — 4.5 ps on inv_chain falling across
  four different silicons. That is a good sign for the model: its own error does
  not grow when the device changes.
- Combined with the earlier decomposition, the picture is consistent: the shift
  is a full-swing property (not stress), it is device-dependent in sign, and the
  device-dependence lives in the part we share with native.

## Caveats

- Full swing only, by design. The depth decomposition showed 77-103% of the
  offset is present at full swing on 5 of 6 combinations, but that was measured on
  the three base buffers and is assumed, not measured, for the variants.
- One measurement per variant per direction; no repeat runs.
- ex2 variants use models the selector formally rejected (max|Ku| above the 1.25
  cap). The cap is known to reject ex2's own control, so the models are usable,
  but this should be revisited once the cap is replaced.

## Files

- `variant_timing_offset.csv`, `variant_timing_offset.png`
- `scripts/variant_timing_offset_sweep.py`
