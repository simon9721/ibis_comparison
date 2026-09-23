# Is inv_chain's 26 % the handoff between the two Ku curves? - findings

*2026-09-22* · script `scripts/inv_chain_single_curve.py` · follows step 7 of
`results/stage_count_from_file_2026-09-21`

## Why ask

With today's converter (input threshold clamped to 0.9 V) inv_chain's error at the track-1
settings is **25.8 %**, not the 7.2 % the cached 09-09 models reported. At the worst width its
gate is right - 0.95 against the transistor's 0.94 - and the pad is still 26 % high, so the
error is in the map, not the gate. The suspect: the file's falling Ku table sits ~19 ps early
against the gate, so `KUGATE_OFF` reads 0.49 where `KUGATE_ON` reads 0.96 at the same gate,
and a stressed pulse turns round in exactly that region.

## The test

Three builds of one model (K = 7, C_comp 0.60, family shape), differing only in the pull-up
map: the file's two curves as built; `KUGATE_OFF := KUGATE_ON` (one curve both ways, no
handoff step); and the average of the two. `single_curve.csv`.

| map | worst peak | peaks, 135 / 119 / 111 / 106 / 104 ps | lag (ps) | full swing |
|---|---:|---|---|---:|
| as built | 25.8 % | +3.0 / +9.6 / +19.2 / +25.8 / +4.1 | 44-67 | 54 mV |
| **one curve** | **17.4 %** | +2.4 / +8.0 / +16.2 / +17.4 / -10.7 | 33-50 | 39 mV |
| average | 24.4 % | +0.2 / +5.7 / +14.6 / +24.4 / -3.1 | 69-100 | 89 mV |

## What it says

* **The handoff is worth about a third of the error**: 25.8 -> 17.4 %, and the pad arrives
  ~15 ps earlier as well. Removing the step between the two curves helps on every width.
* **It is not the whole story.** With one curve the model is still +16-17 % at 111 and 106 ps,
  the widths where its gate already matches the transistor to 0.01-0.02. Something other than
  the gate and other than the handoff over-drives the pad there.
* **Averaging the curves is not a fix** - it halves the step but costs 25-35 ps of timing and
  doubles the full-swing error, because it drags the rising branch down as well.
* The same map edit moves the shipped model by only 1-2 points (65.9 -> 64.0 %), so the
  handoff matters to the chain build, not to the shipped one. The shipped model's 66 % at the
  narrowest width is a separate, larger failure.

## The rest of it: the gate is the right height and the wrong pulse

The map's *level* is not the cause. `physics_map_gate_2026-09-10` fitted inv_chain's measured
Ku-vs-gate curve with this very prior (vt 0.49, alpha 0.60, rms 0.070), and where the two
differ - above Ku 0.8 - the real map saturates *earlier*, so the prior under-drives there. It
cannot make the pad 17 % high.

Measuring the whole gate pulse instead of its height settles it
(`scripts/gate_pulse_shape.py`, `gate_shape.csv`, read off the step-7 builds, no new runs):

| inv_chain, K = 7 | 135 | 119 | 111 | 106 | 104 |
|---|---|---|---|---|---|
| height, model / transistor | 1.00/1.00 | 1.00/0.99 | 0.99/0.97 | 0.95/0.94 | 0.77/0.88 |
| peaks at (ps after the reversal) | 282/248 | 284/242 | 280/236 | 278/234 | 276/230 |
| width at half height (ps) | 138/128 | 120/106 | 110/90 | 96/80 | 84/76 |
| **area above 0.1 (the charge)** | **+7 %** | **+14 %** | **+22 %** | **+18 %** | **-7 %** |
| pad peak error | +3.0 | +9.6 | +19.2 | +25.8 | +4.1 % |

**The pad error tracks the gate's area, not its height.** The modelled gate reaches the right
height, arrives ~45 ps late, and stays up 10-20 ps too long; that surplus charge is the
overshoot. ex2 says the same from the other side: its gate area runs a steady -4...-5 % and
its pad a steady -5...-8 %, at every width.

So the stage law gets *how far* the gate goes right and *how fast it comes back* wrong. On a
buffer whose real gate turns round in 29 ps, 10-20 ps of extra width is most of the pulse.

## Open

Why the chain's gate falls too slowly. The current-limited stage has one drive per direction
(`s_up`, `s_dn`) and the discharge fraction `x_lin * XLIN_DN_RATIO`; inv_chain is fitted with
`x_lin` free. Whether the fall can be sharpened without spoiling the full swing - which is what
fixes `s_dn` - is the next question, and it is the same degree of freedom the 09-10 train work
concluded was missing.
