# Open-drain support in the gate-state model, and the chain recipe on it

*2026-09-10*

Until today every gate-state builder in `subcircuit.py` refused `Model_type
Open_drain` and fell back to the legacy Kd control, so every "ours" number on the
three open-drain buffers (`opendrain_stress_*_2026-09-08`) was the table-replay
build with its wrong rest state. This adds the open-drain path, scores it on the
same bench (50 Ω to VCC, 2 pF, short LOW pulses, transistor and native HSPICE
IBIS as before), then applies the current-limited-chain recipe to it.

Figures: `opendrain_summary.png` (three buffers × four builds), `<variant>/
opendrain_stress.png` (pads, gate-state build), `../opendrain_chain_2026-09-10/
*/opendrain_chain.png` (pads, chain), `../opendrain_silicon_map_2026-09-10/
*_silicon_kd_map.png` (the NMOS map). Data: `<variant>/cases.csv` and
`../opendrain_chain_2026-09-10/*/cases.csv`.

---

## 1. The converter: one predriver, one device, so the pull-down half of the push-pull machinery is the model

`subcircuit.open_drain_tables_as_push_pull(kr, kf)` widens the two-column
open-drain tables `[t, Kd]` into `[t, 1 - Kd, Kd]` and the two-state gate builder
runs unchanged: GDN is the pull-down gate with its Kd map and residual; the GUP /
Ku half is a mirrored placeholder that nothing reads, because an open-drain file
has no `[Pullup]` table and so no pull-up current branch is emitted. The
delayed-level command makes the rest state a DC solution whichever way the input
rests. The push-pull output is byte-identical after the change (ex2 regenerated
and diffed: only the IBIS path comment differs).

| build, base OD | rest (input high) | full-swing fall / rise 50 % vs transistor | Kd at the pad minimum, 90 → 4 % depth |
|---|---:|---:|---|
| legacy Kd control | **1.33 V** (pulled low until the first edge) | n/a (starts low) / +141 ps | 1.01 … 1.00 at every depth |
| **gate-state (this change)** | 3.24 V (transistor 3.30) | **+132 / +76 ps** | 1.02 → 0.74 |
| native HSPICE IBIS | 3.30 V | −29 / −4 ps | 1.02 → 1.31 (rises above 1 at the deep end) |

The 56 mV rest offset is the file's own `kd_off` = 0.013 (the rising waveform's
end value) times the pull-down table.

Stress, all three open-drain buffers, model low minus transistor low (mV):

| depth | base: legacy / gate-state / native | od_weak: legacy / gate-state / native | od_slowpre (depth): legacy / gate-state / native |
|---:|---|---|---|
| 90 % | −195 / **+71** / −115 | (86 %) −185 / +190 / +423 | (90 %) −195 / **+11** / −99 |
| 79 % | −415 / **−105** / −321 | −271 / +144 / +801 | (83 %) −342 / **−93** / −224 |
| 65 % | −685 / **−340** / −579 | (72 %) −352 / +91 / +778 | (70 %) −590 / **−289** / −417 |
| 47 % | −1049 / **−670** / −933 | (61 %) −484 / **−16** / +746 | (57 %) −856 / **−508** / −681 |
| 28 % | −1419 / **−1001** / −1180 | (43 %) −709 / **−210** / +521 | (46 %) −1064 / **−680** / −874 |
| 4 % | −1891 / **−1385** / −1587 | (7 %) −1146 / **−590** / +84 | |

A quarter to a third of the legacy error is gone at every width, and the build
beats native at every depth on base and od_slowpre. On od_weak native
malfunctions (pad driven above VCC, Kd −0.8), so the gate-state build is the only
working IBIS model there. What remains is the eleven's regime: the gate is driven
by a delay plus an RC and is still far more "on" under a short pulse than the
transistor's.

## 2. The chain recipe on the pull-down gate: three things the push-pull matrix never tested

`scripts/opendrain_chain_build.py`: the converter's open-drain build → its
full-swing Kd(t) → K identical current-limited stages → one stressed pad run on
the open-drain bench to place the threshold → every width scored.

**Fit in the Kd domain.** The first attempt fitted through the mirrored Ku, as
the push-pull recipe does. The mirrored Ku is zero wherever the pull-down is on,
so the fit constrained only the release and left the onset free: the chain arrived
250 ps early at every width and the calibration could only scale the drive
(`base_calib680_ku`: −24 … +550 %). `gate_chain_prototype.fit_chain_ku` now
takes `which="kd_map"` (Kd = prior(1 − g) against the tables' Kd(t)).

**The open-drain NMOS map is not the pull-up map.** With the Kd-domain fit and
the ex2 family prior (threshold 0.52) the chain reproduced the calibration point
but not the depth law: −25 % at 90 % depth, +40 / +140 / +460 % at 28 / 13 / 4 %.
The bench's own pairs (n4 at the pad minimum, Kd there) said why, and
`scripts/opendrain_silicon_map.py` measured it: the transistor's Kd against its
own normalised gate, single-fixture solve at 3.0 pF, is one curve on all eight
widths (rms 0.008) with

| buffer | vt | alpha | gs | rms | (with declared 5.0 pF) |
|---|---:|---:|---:|---:|---|
| base | 0.20 | 1.30 | 0.88 | 0.008 | 0.21 / 1.35 / 0.78, rms 0.034 |
| od_weak | 0.23 | 1.15 | 0.92 | 0.011 | |
| od_slowpre | 0.24 | 1.15 | 0.90 | 0.010 | |

The NMOS turns on at a fifth of its gate swing where the pull-up map's threshold
is half. Push-pull stress never reached this region (its Kd was in its release,
the peak came from Ku); open-drain stress lives in it. The declared 5 pF gives a
visibly worse map (rms 0.034), a second confirmation of the 3.0 pF loop value.

**Bracket the threshold from the fitted value.** The stage rate is
((x − vt)/(1 − vt))^p, so lowering vt below the fitted value slows the stages as
much as it opens them earlier; the excursion is not monotone in vt over [0, 0.7].
The push-pull bracket happened to work. The open-drain script now bisects from
the fitted vt toward the side the sign asks for.

With all three (3.0 pF, the measured NMOS prior, K = 3, one pad run at 46–70 %
depth), chain excursion error as % of the transistor's excursion at each width,
and in mV against the other builds:

| depth | base: chain % (mV) · gate-state · native | od_weak: chain % (mV) · gate-state · native | od_slowpre: chain % (mV) · gate-state · native |
|---:|---|---|---|
| 90 % | **−12 % (+217)** · +71 · −115 | (86 %) **−11 % (+116)** · +190 · +423 | (97 %) **−1 % (+24)** · +59 · +4 |
| 79 % | **−14 % (+216)** · −105 · −321 | **−10 % (+100)** · +144 · +801 | (90 %) **−6 % (+103)** · +11 · −99 |
| 65 % | **−11 % (+137)** · −340 · −579 | (72 %) **−8 % (+73)** · +91 · +778 | (83 %) **−5 % (+83)** · −93 · −224 |
| 47 % | **−0 % (+3)** ¹ · −670 · −933 | (61 %) **−0 % (+1)** ¹ · −16 · +746 | (70 %) **−0 % (+2)** ¹ · −289 · −417 |
| 28 % | +21 % (−116) · −1001 · −1180 | (43 %) +31 % (−163) · −210 · +521 | (57 %) +9 % (−102) · −508 · −681 |
| 13 % | +75 % (−186) · −1257 · −1445 | (22 %) +128 % (−337) · −440 · +263 | (46 %) +20 % (−184) · −680 · −874 |
| 4 % | +221 % (−166) · −1385 · −1587 | (7 %) +509 % (−429) · −590 · +84 | |

¹ the calibration width.

Full swing is kept (−0.5 % excursion, and the release edge is now 100 ps earlier
than the gate-state build's, closer to the transistor). From 90 % down to the
calibration depth the chain is within 14 % on all three buffers. Below that it
over-drives: the transistor's cliff (90 → 4 % across 130 ps of width on base) is
sharper than the chain's, and the shallow-end percentages are large because the
transistor's excursion there is only 75–330 mV. In absolute terms the chain's
worst case is 186 mV on base and 429 mV on od_weak, against 1385–1587 mV for
the gate-state build and native.

## 3. What this settles, and what it does not

* Open-drain is supported by the converter's gate-state architecture: correct
  rest state, depth-dependent Kd, better than native at every stressed depth on
  the two buffers where native works, the only working model on the third.
* The output stage is a static map on the open-drain too, on eight widths, and it
  has the NMOS's own threshold. A model that carries one prior for both halves
  (Ku = prior(g), Kd = prior(1 − g)) is wrong for the pull-down by a factor of
  2.5 in threshold; it did not show on push-pull because the push-pull matrix
  never stressed the pull-down onset. The same is presumably true of the push-pull
  buffers' Kd maps and would show on short LOW pulses.
* The chain's depth cliff is softer than silicon's below ~30 % depth. Open-drain
  stress widths sit inside the predriver's propagation time, so they measure the
  chain's dead time and onset sharpness directly, where p = 1 and x_lin = 0.45
  were assumed. This is the same missing degree of freedom the trains asked for.

## Caveats

* Three open-drain ex2 buffers, one bench, one polarity (short LOW).
* C_comp 3.0 pF is the single-fixture loop value; the push-pull two-fixture solve
  on the same die gave 1.75. The two solves absorb the voltage-dependent
  capacitances differently and the gap is still open.
* The plateau rule picked K = 2 on od_weak and od_slowpre with the pull-up prior
  and K = 3 on base with the NMOS prior; K = 3 was forced on the two variants
  (the same predriver as base).
* Native's numbers on od_weak are a malfunction, not a reference.
