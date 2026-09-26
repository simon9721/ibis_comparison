# Prototype: the gate as a slow ramp with a re-derived map

*2026-09-09*

**Hypothesis.** `gate_physics_2026-09-08` found Ku to be a static map of a *slow*
predriver node. Our shipped model represents the same full-swing Ku(t) as a
command delay followed by a fast RC gate (τ_rise 20 ps on inv, 175 ps on ex2,
1127 ps on io_buf) and a map. The two descriptions are indistinguishable at full
swing and differ under truncation: a delay-then-fast-ramp is fully on at the
reversal, a slow ramp is partway. So: slow the gate by a factor k and re-derive
the map from the shipped full-swing gate-part Ku(t), so full swing is preserved
by construction; then score the stressed cases against the transistor.

Two fall treatments: `dual` derives a separate fall map the same way (exact at
full swing); `single` uses the rise map for both branches (the physics: one gate,
one map) with τ_fall fitted to the shipped fall.

`scripts/gate_ramp_prototype.py`, sweeps in `<variant>/sweep.csv`.

---

## Result: partial on inv, none on ex2's peak, decisive on io_buf's timing

Peak excess (%) and lag vs the transistor (ps), shipped → best prototype:

| buffer | best | 50 % / deepest peak | lag (mild → deep) | full-swing Ku rms |
|---|---|---|---|---|
| inv_base8 | dual k ≥ 4 | **65.1 → 49.2 %** | 67 → 55 ps (11 → 1 at 100 %) | 0.024 |
| ex2_base | dual k ≥ 4 | 70.9 → 66.9 % (no real change) | **124 → −7…17 ps** at 90 %, 245 → 148 at 70 % | 0.009 |
| io_buf | single k = 4 | −3.5 → −10.5 % (worse, deep only) | **63…69 → +10 / +9 / +2 / −4 / −20** | 0.019 |

Native for comparison: inv_base8 66.8 % / 63 ps, io_buf −20 % / −26 ps.

**inv_base8.** The slow fall with a dual map removes a quarter of the peak excess
and ~12 ps of lag, saturating beyond k = 4 (49.2 / 48.8 / 48.5 / 48.2 %). `single`
is worse than shipped. Full swing preserved (100 % depth: −0.5 %, 1 ps).

**ex2_base.** The lag falls by ~100 ps at 70–90 % depth, but the peak does not
move. The traces explain it: at 50 % depth our pad is already 46 % above the
transistor's at +600 ps, *before* our off-command arrives at rev + pu_off
(733 ps). The transistor's rise bends the instant the input reverses — its
predriver is a chain of analog stages — while our T-line delay blocks the
reversal until pu_off. Nothing done to the gate can act before the command does.
That is the next prototype (`gate_cascade_prototype.py`).

**io_buf.** A different regime, and here the slow gate is the pedestal fix:
`single`, k = 4 (τ_rise 4.5 ns, τ_fall 56 ps) takes the lag from +63…+69 to
+10 / +9 / +2 / −4 / −20 ps — the value `pu_off × 0.29` reached by tuning in
`pu_off_scale_2026-09-07`, now reached by a derived change with full swing kept
within 0.019 rms. The price is the same as before: the deep-stress peak drops
(−3.5 → −10.5 % at 1505 ps). `dual` over-corrects io_buf (lag −60…−100 ps).

## What it establishes

* The fall side of the story is right: entering the fall from a partial gate
  state is worth 100 ps of lag on ex2, 12 ps on inv, the whole pedestal on io_buf.
* The rise side is untouched by any gate change, because the command layer is a
  hard delay. The reversal has to be able to bend the rise. That is what the
  cascade prototype tests.
* io_buf and the eleven want different fall treatments (`single` vs `dual`): one
  more way the two regimes differ.

## Caveats

* Pull-down path unchanged; short-high only.
* The map re-derivation samples the shipped gate-part Ku(t) on a uniform grid in
  g and can only be as smooth as that; full-swing Ku rms 0.009–0.024 is the cost.
* io_buf's `single` fit quality for the fall is 0.015–0.043 (rms of the map
  reproducing the shipped fall); on inv/ex2 `single` fits the fall poorly
  (0.08–0.15), which is why `dual` wins there.
