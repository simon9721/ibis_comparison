# Status — 2026-09-03

Pick-up notes. What is running, what is established, what is open, and which of
my earlier claims turned out wrong.

---

## Running right now

| job | state |
|---|---|
| `ex2 nomiller` characterization | **running** — the decisive Miller-feedthrough test |
| `ex2 weak` characterization | running (partial results already in, see below) |

Logs in the session scratchpad: `ex2_weak_select.log`, `ex2_nomiller_select.log`.
Re-run with `scripts/select_s2ibispy_parameters.py --config <variant>/configs/<x>.yaml
--out <variant>/selection`.

---

## The big open thread: what inflates max|Ku| — and it is probably physical

ex2 variants, all seven edge rates each:

| variant | what changed | max\|Ku\| | max\|Kd\| |
|---|---|---:|---:|
| `slowpre` | predriver halved | **1.04 – 1.06** | 1.03 |
| `base` | nothing (control) | 1.28 – 1.34 | 1.11 – 1.13 |
| `skewp` | output PMOS halved | 1.59 – 1.71 | 1.24 – 1.31 |
| `weak` | both output devices halved | **1.82 – 1.83** | **1.48 – 1.49** |
| `nomiller` | n4→out caps removed | *running* | *running* |

**Hypothesis (well supported, not yet proven):** max|Ku| inflation is
**gate-to-drain (Miller) feedthrough** that the two-fixture Ku/Kd solve cannot
attribute to either device, so it lands in the coefficients.

    max|K|  ~  (Miller feedthrough current)  /  (device drive current)
             =  C_n4→out * dV_n4/dt          /  I_pu(V)

Every variant fits:

- **`slowpre`** weakens the *predriver* → smaller `dV_n4/dt` → smaller numerator →
  Ku collapses to 1.05, exactly inv_chain's clean level.
- **`weak`** weakens *both output devices* → smaller denominator → **both** Ku and
  Kd inflate (1.83 / 1.49).
- **`skewp`** weakens *only the PMOS* → Ku inflates much more than Kd
  (1.71 / 1.31), the asymmetric signature already seen on inv_chain.
- **Structural check:** ex2 carries **20.5 fF** of explicit n4→out coupling
  (cx3 + cx5 + cx8). inv_chain has **zero** explicit caps — and inv_chain's
  max|Ku| is 1.03–1.06.

`nomiller` (those three caps removed, nothing else) is the clincher. If Ku falls
to ~1.05 the mechanism is proven.

**Why this matters beyond ex2:** it means a high max|Ku| can be a *real signature
of realistic parasitics*, not a corrupted extraction — which makes the selector's
absolute 1.25 cap wrong in principle, not merely mis-tuned.

### The 1.25 cap needs replacing

It currently **rejects the control**: `base` lands 1.283–1.343 and ex2's *shipped*
model is already 1.244. Healthy baselines differ per silicon (inv_chain 1.03,
ex2 1.28, io_buf 1.18), so no absolute number can work.

What the gate is actually for is catching a *corrupted* candidate — io_buf at
20 ps hitting 1.66 while its siblings sit at 1.18. That is an **outlier among
siblings**, a relative judgement. Replace the absolute cap with a within-buffer
comparison (robust z-score / ratio against the median of the seven edge rates),
keeping an absolute value only as a far backstop.

---

## Defect B — localized, mechanism not yet proven

Defect B: the gate-state model's falling 50% crossing runs **69–99 ps late**
against the transistor on io_buf's five stress cases (truncated pulses,
90/80/70/60/50% width), where native IBIS is **5–26 ps early**.

**Full-swing measurement (new), io_buf, falling 50% vs transistor:**

| build | vs transistor | incremental cost |
|---|---:|---|
| native IBIS (HSPICE B-element) | +34.6 ps | the IBIS format itself |
| pybis InputDriven (stock pybis) | +38.4 ps | +3.8 ps for pybis's reconstruction |
| pybis gate-state (our build) | +43.5 ps | +5.1 ps for the command layer |

Stable across three solver settings, so it is the model's, not the solver's.

**Conclusion:** on a clean edge our command layer costs only ~5 ps, and the gap
to native is ~9 ps. Under stress that gap becomes ~75–125 ps. **Defect B is the
command layer's response to a truncated pulse**, not its fitted delays — those are
ns-scale and a systematic error in them would show on full swing too. It does not.

**Suspected mechanism, untested:** `GUPCMD` is an open-loop integrator (capacitor
across 1e15 Ω) charged by a fixed packet per input edge. A truncated pulse
delivers a partial packet and nothing pulls it back. That is the known cause of
the *offset* defect; the timing shift is plausibly the same residue delaying the
next transition. **The two defects were treated as unrelated and may be one.**

**The next experiment, and it is cheap:** `delay_cmd` is level-driven, so it
returns the command to exactly zero and strands nothing. If the mechanism is
shared, delay_cmd should fix the timing too. Its **amplitude** was measured
(RMSE 108.6 → 92.2 mV, best in the study); its **timing was never measured**.
Measure the falling-edge shift for delay_cmd vs edge-integrating gate-state on
the five stress cases:

- shift collapses → mechanism confirmed and the fix already exists
- shift persists → the two defects are genuinely separate

**Also worth carrying:** native itself moves 40–60 ps between full swing (+34.6)
and stress (−5…−26). Part of defect B's headline size is the reference improving
while we worsen, so **model-vs-native** is the framing that isolates our machinery.

---

## Settled this session

- **pybis handles C_comp correctly.** Golden-waveform test: nominal C_comp beats
  C_comp=0 on all 12 tables across three buffers, and the margin *scales with the
  die capacitance* (base8 0.468 pF → −4/−6 ps penalty; io_buf 1.2 pF → −42/−52 ps;
  ex2 5.0 pF → −124/−178 ps). If it were double-counted, removing it would help
  most where it is largest; the opposite happens.
- **The SPICE engine is not a confounder.** Same pybis model in ngspice vs HSPICE
  (via `scripts/pybis_subckt_to_hspice.py`): −0.5 ps rising, −0.0 ps falling.
  Provided ngspice is run converged.
- **pybis reproduces its own golden waveforms** to FOM 0.03–0.41% on all three
  buffers, with a universal +4 to +8 ps shift.
- **The residual few-ps lag is architectural.** Appendix E: canonical IBIS drives
  a voltage wave from the V-T tables and uses I-V for reflections; pybis
  reconstructs the wave from I-V × Ku(t).
- **s2ibispy clamp extraction fixed upstream** (`c780715`) for enable-less
  open-drain — clamp current at +3.3 V went 51 mA → 0.8 nA. Push-pull models
  re-convert bit-identical.
- **Reporting should be shift + post-alignment FOM**, not raw RMSE. Raw RMSE
  turns picoseconds into millivolts: pybis-vs-native is 17.3 mV as-is, 2.3 mV
  after a −9 ps shift. The "93 mV gap" was just 4.9 ps × 18.5 mV/ps slew.

## Rules learned the hard way

- **Any bench for the InputDriven/gate-state model must begin with a real edge,
  never a held level.** It initialises pulldown-on and establishes state only on a
  detected edge. This produced two false findings (the open-drain bench, and a
  phantom falling-edge defect).
- **Converge ngspice before drawing conclusions.** A 1 ps step was an aliasing
  outlier that doubled the apparent lag and inflated a whole validation sweep.
- **The gate-state build has a convergence floor** — it aborts at `reltol=1e-5`
  with a 0.5 ps step (fails exactly at the falling edge, emits one timepoint)
  while three looser settings agree to 0.2 ps. Do not assume one solver setting
  suits both builds.

## Claims of mine that turned out wrong

- ~~"pybis over-applies C_comp"~~ — wrong; the golden-waveform test reversed it.
  I had applied the book's 11.8.2 sensitivity test outside its scope: it targets
  simulators that use V-T data *directly* and also hang C_comp on the output.
  pybis back-solves Ku with the C_comp current removed, so its edge is *supposed*
  to move with C_comp.
- ~~"C_comp scaling is the fix"~~ — no basis; it was an arithmetic midpoint fitted
  to one load.
- ~~"defect B is not in the model"~~ — overclaimed from a test on a different
  build, stimulus and reference.
- ~~"ex2 does not admit parameterized variants"~~ — wrong; every device carries an
  explicit `w=`.
- ~~"no single C_comp matches across loads, so a redesign is needed"~~ — that came
  from the unconverged 1 ps data.

---

## Backlog

1. **delay_cmd timing on the stress cases** — the decisive defect-B experiment above.
2. **Replace the 1.25 cap** with a within-buffer outlier test.
3. **FOM re-scoring of the back catalogue** — the stress matrix and the 39 per-case
   figures use raw unaligned RMSE; conclusions about which build is better may move.
4. **ex2 variant comparison runs** — transistor vs native vs pybis, once the
   characterization gate is sorted.
5. **Item 5 restructure** — `.tr0` untracking and directory nesting (`item5_followups.md`).
6. **io_buf falling V=0 golden spike** — 280 mV localized, unlike its other tables.
7. `run_three_buffer_prbs_phase1.py:307` uses the wrong model card for io_buf.
8. More of the book: Appendix I (IBIS quality checklist) and ch 12's common-errors
   table could become automated checks on what s2ibispy emits.

## Where things live

- `book_study_notes.md` — Leventhal & Green study notes
- `s2ibispy_findings.md`, `delay_cmd_explained.md`, `item5_followups.md`
- `results/golden_waveform_*_2026-09-03/` — golden-waveform tests (3 buffers)
- `results/defect_b_full_swing_2026-09-03/` — the defect-B probe
- `results/pybis_engine_model_decoupling_2026-09-03/` — the engine/model 2×2
- `results/ex2_variants_2026-09-03/`, `results/inv_chain_variants_2026-09-02/`
- `scripts/spicelab.py` — shared SPICE plumbing (runner, stimulus, trace lookup)
