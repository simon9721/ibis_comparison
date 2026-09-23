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

## Open

What over-drives the pad at 106-111 ps with the gate correct and the handoff removed. Two
candidates, neither tested: the rising branch's **level** (inv_chain's map is a 2-parameter
prior fitted to the file, vt 0.49 / alpha 0.60 - the measured Ku-vs-gate curve may sit lower),
and the **timing** of the drive (the build still lands 33-50 ps late, and a late drive on a
pad that is still rising reads as a higher peak). The track-2 measured map for inv_chain is
the direct way to separate them.
