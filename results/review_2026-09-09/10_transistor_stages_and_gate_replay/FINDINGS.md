# How the transistor buffer really behaves under a short pulse, stage by stage

*2026-09-09*  ·  tools: `scripts/predriver_stage_probe.py`, `scripts/kd_gate_hysteresis.py`,
`scripts/shared_gate_prototype.py`, `scripts/gate_replay_prototype.py`, `scripts/silicon_map_replay.py`

The question this round answers: **what does the transistor do between its input
pin and its pad when the pulse is too short, and which part of that does an IBIS
model (ours or native) fail to represent?** Everything below is measured on the
transistor with the model out of the loop, except the last two sections, where
the transistor's own internal node is fed into the model to split the error.

Data: the same three matrix decks (hspice.mod, 50 Ω ∥ 2 pF, 50 ps input edge)
re-run with every internal stage probed, at full swing (rise 5 ns, fall 15 ns)
and at the five stressed widths. `stages.csv` carries every number.

---

## 1. The three predrivers are three different machines

Full-swing step responses per stage, ps from the input edge (normalised to each
node's own swing):

| device | stage | t50 rise | 10–90 rise | t50 fall | 10–90 fall |
|---|---|---:|---:|---:|---:|
| **ex2** | n2 | 248 | 434 | 338 | 680 |
| | n3 | 730 | 904 | 694 | 626 |
| | n4 (output gate, drives P and N) | **1096** | **662** | 1170 | 798 |
| | pad | 1400 | 442 | 1142 | 366 |
| **inv_chain** | vout1 … vout7 | 58 → 302, +40/stage | 42–76 | 64 → 308 | 52–78 |
| | pad | 354 | 94 | 340 | 58 |
| **io_buf** | n1 (first inverter) | 632 | **1556** | 946 | 2158 |
| | nand_n3 → n3 (NMOS gate) | 718 → 1224 | 410 → 812 | 1622 → 2010 | 930 → 724 |
| | n2 (PMOS gate) | 1198 | **2566** | 260 | 448 |
| | pad | 1856 | 1766 | 346 | 396 |

* **ex2** is three slow inverters in series. A 50 ps input edge takes 1.1 ns to
  reach the output gate's 50 % point, and that gate's own 10–90 is 662 ps. The
  stressed widths (810–975 ps) are *shorter than the predriver's own delay*.
* **inv_chain** is seven fast stages, 40 ps each, all 50–75 ps 10–90. The gate is
  fully swung by 330 ps; the pad's 94 ps rise is the slowest edge in the chain.
* **io_buf** has two separate predriver paths. The PMOS gate n2 rises as a 2.6 ns
  ramp (a NOR pulled up through a single stack) and snaps back in 448 ps; the
  NMOS gate n3 is a NAND → inverter path, 1.2 ns to 50 %.

## 2. Is each stage linear? The superposition test

A linear time-invariant stage answers the pulse with the sum of its two
full-swing step responses, `P(t) = g_rise(t − t_on) + g_fall(t − t_off) − 1`.
The measured node against that prediction, peak of the normalised node:

| device | node | W (ps) | measured max | linear max | verdict |
|---|---|---:|---:|---:|---|
| ex2 | n2 | 810 | 1.033 | 1.034 | linear (rms 0.016) |
| ex2 | n3 | 810 | 0.780 | 0.818 | slightly under |
| ex2 | **n4** | 810 | **0.758** | **0.926** | under, rms 0.14 |
| ex2 | pad | 810 | 0.499 | 0.903 | far under |
| inv_chain | vout1–vout5 | 104 | 0.91–1.00 | 0.96–1.00 | linear (rms ≤ 0.04) |
| inv_chain | vout6, vout7 | 104 | 0.86, 0.88 | 0.96, 1.00 | slightly under |
| inv_chain | **pad** | 104 | **0.490** | **0.853** | far under |
| io_buf | n1, nand_n3, n3, n2 | 1505 | 0.89, 1.02, 1.01, 0.67 | 0.89, 1.02, 1.01, 0.67 | **linear** (rms ≤ 0.10) |
| io_buf | pad | 1505 | 0.373 | 0.371 | **linear** |

Figures: `<device>/stages_vs_linear.png` (every stage, measured vs linear) and
`<device>/pulse_down_the_chain.png` (all stages on one axis).

What the shapes say (checked visually):

* **io_buf is linear from input to pad.** Every node, every width, sits on the
  superposition of its own two step responses. Its stressed behaviour — the
  n2 ramp truncated at 67–88 %, the pad at 37–80 % — is nothing but the measured
  step responses being cut short. A linear filter with those exact step
  responses would reproduce io_buf's gates and pad under any stress. That is why
  the slow-gate prototype (an RC that approximates the n2 ramp) fixed io_buf's
  pedestal, and why nothing more exotic is needed there.
* **ex2's stages are sub-linear, more so down the chain, and the loss is in the
  return.** n3's rise is exactly the linear prediction; its return is faster.
  n4 starts on the linear curve, stops early (0.76 vs 0.93) and returns early.
  The deviation shrinks with width (n4: 0.76/0.93 at 810 ps, 0.94/0.97 at 975).
  Theory: each stage is a current-limited integrator. When its input is only
  briefly at the rail, the delivered charge is less than the superposition of
  two full-rail edges predicts, and the discharge from a partial level finishes
  sooner than the full-swing fall response shifted in time. A CMOS inverter
  into a large gate load is exactly that: saturated current while the input is
  at the rail, resistive only near the destination rail.
* **inv_chain's chain is nearly linear; the output stage is where the pulse is
  lost.** vout7 reaches 0.88 of full swing (linear says 1.00), but the pad
  reaches 0.49 where linear says 0.85. The output inverter drives 2 pF ∥ 50 Ω
  with a 94 ps 10–90 edge; under a gate pulse that is at 0.88 for a few tens of
  ps, the current-limited output stage cannot get there. This is the buffer on
  which "the gate is right but the pad is wrong" was seen in the slew-stage
  builds (`gate_tracking_slew56ps.png`), and this is why.

## 3. One gate drives both halves: Kd is a static map of the same node

ex2's and inv_chain's output stage is a single inverter — n4 / vout7 drive the
P and the N devices. The transistor's two-fixture Kd against that node
(`kd_gate_hysteresis.png`, loop = mean |up − down|), at the C_comp that closes
the Ku loop (ex2 1.75 pF, inv_chain 0.6, io_buf declared, vs n3):

| device | Ku loop | Kd loop | Kd minimum in the event |
|---|---:|---:|---:|
| ex2 | 0.08–0.09 | **0.035–0.063** | −0.07 … +0.03 (pull-down fully off) |
| inv_chain | 0.04–0.10 | **0.05–0.06** | −0.04 … −0.07 |
| io_buf | 0.07–0.11 | 0.055–0.08 | −0.46 … −0.78 (residual regime) |

Kd is single-valued in the gate on all three, tighter than Ku. On ex2 and
inv_chain both coefficients are maps of **one** node. Our model gives the
pull-down its own gate (GDN) from its own delay lines.

**Tying the model's GDN to 1 − GUP** (Kd maps re-derived, full swing preserved,
`shared_gate_prototype.py`): peak error unchanged within ±1.5 % on every ex2
and inv_chain build; ex2 lag improves 10–18 ps. Physically right, but not the
lever for the peak. `<variant>/shared_gate_sweep.csv`.

## 4. The decisive split: feed the model the transistor's real gate

`gate_replay_prototype.py` replaces the model's GUP by the transistor's own
normalised gate node (ex2 n4, inv_chain vout7; io_buf n2 for GUP and n3 for
GDN), replayed as a PWL source. Ku/Kd maps are re-derived from the shipped
full-swing gate-part K(t) against the real full-swing gate (full swing preserved
by construction), then the stressed widths are run. Whatever error remains is
the output stage's; whatever disappears was the predriver's.

### ex2

| build | d975 | d895 | d858 | d830 | d810 | lag d975…d810 (ps) |
|---|---:|---:|---:|---:|---:|---|
| shipped (C_comp 5 pF) | +1.4 | +9.8 | +22.3 | +40.7 | **+66.6** | 121 … 300 |
| real gate, C_comp 5 pF ¹ | −9.8 | −11.1 | −6.1 | −6.8 | −12.3 | −28 … −121 |
| real gate, **C_comp 1.7 pF** | **−3.3** | **−4.7** | **−5.8** | **−5.4** | **−5.5** | **+22 … +18** |

(`ex2/gate_replay/gate_replay.png`, `ex2_c1.7/gate_replay/gate_replay.png`. ¹ first selector, 4 ps lead; the 1.7 pF row is with the final mechanics of §5.)

With the real gate and the loop-measured C_comp, the output stage reproduces
all five stressed pads within −3…−6 % and ~20 ps. **The whole of ex2's stressed
error is the predriver trajectory plus the 3× C_comp error**; the static-map
output stage is right. The Ku map against n4 implied by the IBIS tables and the
one measured on silicon inside the stressed event agree to ±0.03 from g = 0.4
to 0.8 (`ex2_c1.7/gate_replay_silicon_stress/maps.png`), so on ex2 the IBIS
tables carry the correct output-stage information.

### inv_chain — the IBIS tables mis-place Ku against a fast gate

| build | d135 | d119 | d111 | d106 | d104 | lag |
|---|---:|---:|---:|---:|---:|---|
| shipped | −5.9 | −6.0 | −0.7 | +11.9 | +32.1 | 0 … 44 |
| real gate, IBIS-implied maps | −13.6 | −29.9 | −41.3 | −53.8 | **−68.8** | −15 … −29 |

Fed the real gate, the model now *under*-drives by up to 69 %. Ku is single-
valued in the gate on the transistor (§3), so the map's shape is wrong, not the
idea. The map implied by the IBIS tables versus the map measured on silicon in
the middle stressed event (C_comp 0.6 pF):

| g (gate, 0 off … 1 on) | Ku, IBIS-implied | Ku, silicon |
|---:|---:|---:|
| 0.5 | 0.00 | 0.13 |
| 0.6 | 0.02 | 0.34 |
| 0.7 | 0.19 | 0.57 |
| 0.8 | 0.40 | 0.83 |
| 0.9 | 0.79 | 0.99 |

The IBIS-implied map is **late in the gate**: it books Ku as still off when the
real gate is 60–80 % on. The map is "Ku(t) from the tables at the moment the
real gate passed g"; inv_chain's gate crosses 10–90 % in 50 ps, so a few tens of
ps of lag between the tables' Ku(t) and the real gate turns into this shape.
On ex2 the same lag is invisible because the gate takes 660 ps.

(Silicon-map replays — the model with the silicon map fed the real gate, and the
same from full-swing fixture runs — are in §5 below.)

## 5. The map from silicon: the output stage IS a static map of the gate

`silicon_map_replay.py` keeps the real gate replayed and takes the Ku/Kd maps
from the transistor's own two-fixture Ku(t)/Kd(t) plotted against its own gate —
from two new full-swing fixture runs (`--source full`), or from the middle
stressed event (`--source stress`). Final replay mechanics on every row below:
PWL gate → 3 ps RC into GUP, direction selector 20 ps ahead with a 0.005
deadband.

### inv_chain (C_comp 0.6 pF)

| g | Ku, IBIS-implied | Ku, silicon full swing | Ku, silicon stressed event |
|---:|---:|---:|---:|
| 0.5 | 0.00 | 0.14 | 0.13 |
| 0.6 | 0.02 | 0.35 | 0.34 |
| 0.7 | 0.19 | 0.57 | 0.57 |
| 0.8 | 0.40 | 0.84 | 0.83 |
| 0.9 | 0.79 | 0.98 | 0.99 |

The two silicon maps agree to 0.01 — **Ku(g) is one curve, the same at full
swing and inside a truncated pulse.** That is the static-map claim, proven on
the transistor.

| build (real gate in) | d135 | d119 | d111 | d106 | d104 | lag (ps) | full-swing pad rms |
|---|---:|---:|---:|---:|---:|---|---:|
| IBIS-implied maps | −13.6 | −29.9 | −41.3 | −53.8 | −68.8 | −15 … −29 | 19.6 mV |
| **silicon map, full swing** | **+2.0** | **+2.8** | **+4.6** | **+7.0** | **+9.4** | **+9 … +13** | **17.3 mV** |
| silicon map, stressed event ¹ | −0.3 | +1.0 | +3.8 | +7.4 | +11.3 | +6 … +12 | (map flat above g = 0.97) |

¹ measured with the previous selector (4 ps lead); its full-swing rerun stalled
in ngspice at 15.6 ns and was not repeated.

(`inv_chain_c0.6/gate_replay_silicon_full/silicon_map_replay.png`, `maps.png`.)
With the right map the same model reproduces inv_chain's stressed pads to
within +2…+9 % and ~10 ps at every width, from the pulse that reaches 1.29 V to
the one that reaches 0.69 V — and the full-swing pad is *better* than with the
IBIS-implied map. Nothing about the output-stage structure had to change.

### ex2 (C_comp 1.7 pF)

The IBIS-implied and silicon full-swing maps agree to ±0.03 for g ≥ 0.5
(0.17/0.18 at 0.6, 0.41/0.38 at 0.7, 0.72/0.73 at 0.8, 0.91/0.91 at 0.9).

| build (real gate in) | d975 | d895 | d858 | d830 | d810 | lag (ps) |
|---|---:|---:|---:|---:|---:|---|
| IBIS-implied maps | −3.3 | −4.7 | −5.8 | −5.4 | −5.5 | 18 … 24 |
| silicon map, full swing | +1.2 | +1.1 | +1.0 | −1.3 | −4.7 | 1 … 26 |

### io_buf (declared C_comp, n2 → GUP and n3 → GDN replayed separately)

| build | d2354 pk % | d2090 pk % | lag d2354 / d2090 (ps) |
|---|---:|---:|---|
| shipped | +2.1 | +1.6 | 63 / 67 |
| real gates in, IBIS-implied maps | +1.9 | +1.4 | **38 / 37** |

Only the two shallowest widths run (§7). On those the peak was already right and
the real gates halve the lag. io_buf's stressed defects are the pedestal and
the +1.8 ns bump (`../residual_depth_rule_2026-09-09/`), which the peak metric
does not see; the linear-stage result of §2 already says what its gate should
be, so the replay adds little beyond confirming the lag is predriver timing.

## 6. What this says, in bucket-and-pour language

The buffer is two things in series. **The predriver** decides how far and for
how long the gate opens. **The output stage** turns "how open the gate is" into
pad current through one fixed curve per side, Ku(g) and Kd(g), and the IBIS
I-V tables plus C_comp do the rest. Under a short pulse the gate only half
opens, and the pad follows the curve — that is all the stressed behaviour is,
on all three buffers.

* Our model already has this shape (gate node → static map → IBIS equation).
  What it gets wrong is (a) *the gate trajectory* — a T-line delay plus one RC
  cannot reproduce a three-stage current-limited chain (ex2) or a 2.6 ns ramp
  (io_buf) — and (b), on fast-gate buffers, *the map itself*, because the map is
  built from the IBIS tables' Ku(t) paired with whatever gate the model had at
  full swing, and the tables' Ku(t) sits late against a 50 ps gate.
* The IBIS file cannot supply either: it has no gate, and its V-T tables pin
  Ku(t) only at full swing. Native fails for the same reason with no gate at
  all (its Ku is a clock).
* What the transistor tells us to build, per predriver type:
  io_buf — a linear filter whose step responses are the measured ones;
  ex2 — current-limited stages (slew-limited until near the rail), the
  cascade N = 5–6 was the linear approximation of this;
  inv_chain — a near-linear fast chain, but the map must be the silicon
  Ku-vs-gate curve, not the IBIS-implied one.

## 7. Method notes and open items

* HSPICE tr0 files carry the adaptive time points only (~130–250 per run):
  dense where the waveform moves, nanoseconds apart on plateaus. Settled levels
  must be read by interpolation, not by a median over a window (a bug found and
  fixed here). Header names wrap at 80 columns; `predriver_stage_probe.parse_tr0`
  glues the fragments, spicelab's parser silently misaligns the columns.
* ngspice stalls (timestep → 10⁻²³ s, no abort) on the io_buf replay at the
  three deeper widths (d1853, d1666, and by extension d1505) about +220 ps after
  the reversal, with the pull-down replayed or not, and on the inv_chain
  stressed-event map at 15.6 ns. Not cured by: 3 ps smoothing of the replayed gate, a 20 ps lead and
  0.005 deadband on the map selectors, clipping the gate inside (0.001, 0.999),
  trapezoidal integration, non-zero package L/R, a deadband on the residual-rate
  comparators, removing the residual terms and the two-state flag. Left open;
  io_buf is scored on the two widths that run.
