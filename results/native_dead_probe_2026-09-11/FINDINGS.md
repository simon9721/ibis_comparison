# Why HSPICE native IBIS is "dead" on the regenerated variant files

*2026-09-11.* `scripts/native_dead_probe.py` plus the ad-hoc runs in this directory
(each subdirectory holds the edited `input.ibs`, `run.sp`, `run.tr0`).

**Symptom.** On the tr1ps variant IBIS files (all ex2 variants, inv_stage4) HSPICE
native with `ramp_rwf=2 ramp_fwf=2` produces no pulse: pad peak 23 mV, Ku never
above 0.1, Kd dips to 0.4 and returns to 1, no warning. `ramp_rwf=1` (single
waveform) runs. The same buffer's shipped file (8 ps sampling, 5 ps input edge) runs.

**The files are the same waveform.** ex2_base tr1ps vs shipped ex2: same [Model]
keywords, same C_comp, same DC levels (rising into 0: 0 → 1.545 V; into 3.3: 1.338 →
3.3 V), 10–90 % times within 5 ps, values at 100–375 ps identical to 0.1 mV. The
only structural difference: 1000 rows over 2.67 ns (2.7 ps steps) instead of 1000
rows over 8 ns (8 ps steps). Our own two-fixture solve gives clean Ku/Kd on both.

**What revives native** (ex2_base, 812 ps pulse; alive = pad peak ≈ 1.27 V):

| edit to the V-T tables | result |
|---|---|
| as is (1000 rows, 2.67 ns) | dead |
| resampled to 8 ns span, 1000 rows | dead |
| resampled to 8 ns span, 500 rows | alive |
| same 2.67 ns span, 100 / 300 / 500 rows | alive |
| same span, 600 / 700 / 900 / 999 / 1001 rows | dead |
| 13 ps moving average, whole table | alive |
| 13 ps moving average, t < 1 ns only | alive |
| 13 ps moving average on 0.1–0.5, 0.5–1.0 or 1.0–2.7 ns only | dead |
| first 300 ps (or 400) held at the first value | alive |
| first 10 / 20 / 50 / 100 / 200 ps held flat | dead |
| typ column copied into min/max | dead |
| shipped file resampled to 1000 rows over 2.67 ns | alive |
| shipped, same, + 0.3 mV rms white noise for t < 1 ns | **dead** |
| shipped, same, + 0.3 mV rms noise for t > 1 ns only | alive |
| shipped, same, + 0.1 mV rms noise for t < 1 ns | alive |
| shipped, 300 rows, + 0.3 mV rms noise for t < 1 ns | alive |
| inv_stage4 as is / first 20 ps flat / 500 rows | dead / alive / alive |

**Cause.** HSPICE's two-waveform algorithm is sensitive to sample-to-sample ripple
of a few hundred microvolts in the *pre-transition* part of the tables when the
samples are closer than about 5 ps. The regenerated tables carry 0.2–0.4 mV rms of
that ripple before the edge (a 1 ps input edge simulated at 2 ps steps, and the
gate-to-pad feedthrough of that edge); the shipped tables carry about 0.1 mV at 8 ps.
In that region both fixtures' currents are microamps, so the per-point 2×2 solve
for the two switching states is ill-conditioned; the states come out unphysical,
HSPICE silently falls into a mode where Ku stays near zero, and nothing recovers at
the real edge. Coarser sampling, smoothing, or a flat lead-in all keep the solve
sane. It is a property of the simulator's solver, not of the buffer or of our flow's
electrical content, and it is why no warning appears.

**What to do.** Nothing for our model: it is unaffected. For native as a reference
on the variants, regenerate or post-process the V-T tables with ≥ 5 ps spacing or a
13 ps smoothing of the pre-transition region (either restores the +64…+71 % result
that matches ours). The `native_valid` flag in `cross_device_stress_metrics.py`
stays as the guard. Related: the book's warning that the two-waveform data must be
"consistent" or the simulator "can use a single waveform or ramp data instead
(issues a warning)" (Leventhal & Green p.276): here the fallback did not fire.

## Addendum: full swing is fine

`native_fullswing.png`: with a 10 ns pulse the variant files as used (ex2_base, inv_stage4)
give the full swing with Ku/Kd indistinguishable from the shipped file's. The failure needs
the second edge to arrive inside the rising table's lead-in (the 812 ps reversal lands at
0.8 ns, before the transition starts at ~1.0 ns): the lead-in solve on the rippled, finely
sampled table leaves the states slightly off at that instant (Ku -0.10, Kd 0.86 in the dead
trace) and the falling-edge logic never recovers from it. So: native reads these files
correctly and is dead only on stressed pulses; the shipped 8 ps tables survive the same
early reversal.
