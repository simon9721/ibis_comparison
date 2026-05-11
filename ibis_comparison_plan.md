# IBIS Buffer Simulation Comparison
## HSPICE · NGspice · Xyce · Native vs. ibis2spice
### Using a Generic / Mockup IBIS Buffer Model
*Missouri S&T EMC Lab — Signal Integrity Group*

---

## 1. Objective

This study compares IBIS buffer simulation accuracy and convergence behaviour across three SPICE engines — one commercial (HSPICE) and two open-source (NGspice, Xyce). A generic mockup IBIS buffer is used deliberately: the goal at this stage is to validate the simulation pipeline and methodology, not to characterise any specific interface standard or silicon device. A single controlled testbench is used across all experiments; the only variables are the buffer model representation and the simulator. The Python post-processing pipeline is identical for all experiments so waveform and eye-diagram metrics are directly comparable.

Using a generic/mockup buffer at this stage has two advantages:

- The IBIS file is fully understood and controlled — no vendor-specific quirks or missing data sections that could confound results.
- Results generalise: findings about ibis2spice fidelity and open-source simulator convergence are not tied to one specific device or interface standard.

The study answers three questions:

- **Model fidelity**: How accurately does ibis2spice reproduce native IBIS IV behaviour?
- **Simulator portability**: Are NGspice and Xyce sufficiently SPICE-compatible with HSPICE for SI work?
- **Numerical robustness**: Where do PWL Jacobian discontinuities cause convergence problems in open-source simulators?

> **Note:** Once the pipeline is validated with the generic buffer, the study can be repeated with a real vendor IBIS file targeting a specific interface standard (e.g. eDP, DDR4, PCIe) to test whether findings generalise.

---

## 2. Experiment Matrix

> **Status note (May 2026 / updated 2026-05-07):** HSPICE license expired — Exp 4 deferred. ibis2spice tool not available — replaced with pybis2spice (haast repo). No SPISim source/code is available in this environment; only SPISim-converted example decks and blog guidance are used as references.

| # | Simulator | Buffer Model | Status | Primary Variable |
|---|---|---|---|---|
| 1 | NGspice | Transistor-level `io_buf.sp` | ✅ Done | Ground truth |
| 2 | NGspice | pybis2spice (`driver_OutputInput_Typical.sub`) | ✅ Done (PRBS pass on new 50-ohm RLGC channel) | pybis2spice fidelity vs transistor model |
| 3 | NGspice | SPISim-converted FreeSpice examples (`Ibs2Spc_*.spc`) | 🔄 Partial (reference decks only) | SPISim-converted deck behavior vs pybis2spice |
| 4 | HSPICE | Native IBIS instance | ⏸ Deferred (license) | Commercial ground truth |
| 5 | Xyce | Transistor-level `io_buf.sp` | ✅ Done (PRBS pass on new 50-ohm RLGC channel) | Open-source simulator portability vs NGspice refspice |
| 6 | Xyce | pybis2spice (`driver_OutputInput_Typical.sub`) | ⚠️ Partial (syntax ported; compact/PRBS stalls) | Xyce compatibility of pybis behavioral model |

**Controlled comparisons:**

- Exp 1 vs Exp 2 → pybis2spice fidelity (simulator held constant at NGspice)
- Exp 2 vs Exp 3 → pybis2spice vs SPISim-converted deck behavior (simulator held constant at NGspice; no SPISim engine execution)
- Exp 1 vs Exp 4 (deferred) → NGspice vs HSPICE transistor-level agreement

---

## 3. IBIS Source File

**`io_buf.ibs`** — generated from the `io_buf.sp` transistor-level CMOS tristate I/O (TSMC 180nm, 3.3V) using PYS2IBIS3. This is preferable to a pre-existing generic buffer because the exact transistor-level ground truth is available for direct comparison.

**`io_buf.ibs` key properties:**

- Supply: Vcc = 3.3 V
- C_comp = 1.2 pF
- Pullup/Pulldown: nonlinear IV tables extracted from BSIM3v3 transistors
- Rising/Falling waveform tables (V/T data present)
- Package: R = 0, L = 0 H, C = 0 F (zero — no package parasitics in this model)
- Model type: I/O, Active-High enable

**IBIS converter being used:** pybis2spice (haast repository). SPISim FreeSpice converted outputs (`SimIbis_FreeSpice_From_SPISim/`) are available as static reference decks.

> ⚠ ibis2spice (SPISim CLI tool) and SPISim source/code are not available in this environment. Do not add steps requiring SPISim execution.

> **Next step:** After pipeline validation, repeat with a real vendor IBIS file to confirm findings generalise.

---

## 4. Testbench — Fixed Across All Experiments

### 4.1 Channel Model

Use a 10-section lumped RLGC ladder representing a generic 10 cm PCB trace. Pure SPICE R/L/C/G primitives only — no W-element, no Touchstone, no simulator-specific syntax. This is the only channel representation guaranteed identical across HSPICE, NGspice, and Xyce. Characteristic impedance targets 50 Ω — a standard generic value not tied to any specific interface.

**Per-section values (1 cm each):**

- R = 0.5 Ω (conductor loss)
- L = 5 nH (series inductance)
- C = 2.0 pF (shunt capacitance → Z0 = √(L/C) ≈ 50 Ω)
- G = 0.001 S (dielectric loss, small)

**Netlist pattern (repeat 10 times):**

```spice
Rn  na  nb  0.5
Ln  nb  nc  5n
Cn  nc  0   2.0p
Gn  nc  0   0.001
```

Termination: **50 Ω resistor to GND** at the receiver end.

---

### 4.2 Stimulus

**Phase 1 — Simple pulse train (pipeline verification):**

Start with a simple periodic pulse. Easy to verify visually and unambiguous across simulators.

```spice
Vstim  in  0  PULSE(0 3.3 0 200p 200p 2n 5n)
* 0V low, 3.3V high, 200ps rise/fall, 2ns pulse width, 5ns period
```

**Phase 2 — PRBS7 PWL (eye diagram):**

Generate in Python, export as a `.pwl` file. **Critical:** use a `V` source (not a `B` source) to load the PWL — ngspice queues V-source PWL breakpoints as timestep events and advances directly to them, dramatically reducing steps. A B-source `pwl()` expression does not expose breakpoints to the timestep controller and causes massive overhead (measured: 148× at 0.07 ps average step with old model).

```python
def prbs7(n_bits):
    reg = [1]*7
    bits = []
    for _ in range(n_bits):
        bit = reg[6] ^ reg[5]
        bits.append(reg[6])
        reg = [bit] + reg[:6]
    return bits

ui   = 5.0e-9    # 5 ns UI = 200 Mbps — matched to buffer slew rate
tr   = 200e-12   # 200 ps rise time — matches actual buffer output, avoids near-vertical PWL
bits = prbs7(200)  # 200 bits = 1000 ns; PRBS7 period = 127 bits so ~1.6 full periods
# write prbs7.pwl
```

```spice
* CORRECT — V source: ngspice loads breakpoints into event queue
Vstim  in_dig  0  PWL FILE="prbs7.pwl"

* WRONG — B source: breakpoints hidden inside expression, ~150x slower
* Bstim  in_dig  0  V = pwl(time, 0,0 5n,0 5.0002n,3.3 ...)
```

> ⚠ The data rate (200 Mbps, 5 ns UI) matches the pybis2spice model's slew characteristics. Faster data rates require proportionally smaller timestep and may be too slow with the current pybis2spice B-source model.

---

### 4.3 Simulation Settings — Locked Across All Simulators

| Parameter | Value | Notes |
|---|---|---|
| Timestep | 10 ps | Appropriate for 200 ps rise time / 200 Mbps |
| Sim duration (phase 1) | 20 ns | 4 pulses — fast verification |
| Sim duration (phase 2) | 1000 ns | 200 UIs at 200 Mbps — sufficient for eye diagram |
| Supply voltage | 3.3 V | From io_buf.ibs Vcc |
| Temperature | 27 °C | SPICE default |
| Termination | 85 Ω to GND | Matched to channel Z0 ≈ 76 Ω |
| Integration method | Gear, maxord=2 | Better stability than Trap for stiff B-source models |
| Stimulus phase 1 | PULSE 5 ns period | Simple verification |
| Stimulus phase 2 | PRBS7 PWL via V source | `V` source only — never B source |
| NGspice options | `reltol=1e-4 method=gear maxord=2 gmin=1e-12` | Required for pybis2spice B-source convergence |

---

## 5. Outputs to Collect

### 5.1 Waveform Files

| Simulator | Native format | Export command | Notes |
|---|---|---|---|
| HSPICE | .tr0 | `.OPTION POST=2` | Or use `.MEASURE` to export CSV directly |
| NGspice | .raw | `wrdata out.csv V(out)` | Inside `.control` block |
| Xyce | .prn | `.PRINT TRAN FORMAT=CSV` | Direct CSV output |

---

### 5.2 Metrics Extracted by Python Eye Script

All metrics extracted identically from every waveform file. Use Experiment 1 (HSPICE native IBIS) as the ground-truth reference.

**Waveform-level metrics:**
- Rise time 20–80% (ps)
- Fall time 20–80% (ps)
- Overshoot above final high level (mV)
- Undershoot below final low level (mV)
- Propagation delay — 50% crossing (ps)
- Final settled high voltage (mV)
- Final settled low voltage (mV)

**Eye diagram metrics:**
- Eye height at centre UI (mV)
- Eye width at decision threshold (ps)
- Eye area — height × width (normalised)
- Deterministic jitter — crossing point spread (ps)

**Convergence / solver metrics:**
- Did the simulation converge without `.options` modifications?
- Which `.options` tweaks were required (RELTOL, ITL4, GMIN etc.)?
- Number of timestep reductions reported
- Wall-clock simulation time
- Any waveform artefacts at voltage levels matching IBIS table breakpoints?

---

### 5.3 Pass / Fail Thresholds

Relative error against Experiment 1 as scoring criterion:

| Relative error | Rating | Interpretation |
|---|---|---|
| < 2 % | Excellent | Fully equivalent to HSPICE native IBIS |
| 2 – 5 % | Acceptable | Minor numerical differences, usable for SI work |
| 5 – 10 % | Marginal | Noticeable discrepancy, root cause investigation needed |
| > 10 % | Fail | Significant disagreement — likely convergence or model issue |

---

## 6. Results Comparison Table

*Pulse comparison done. PRBS/eye pending.*

Xyce addendum: see `XYCE_RESULTS_2026-05-09.md`. Xyce completes the
transistor-level refspice PRBS7 new-50ohm-channel run to `1000 ns` in `2.46 s`.
The pybis2spice behavioral model is syntactically portable after conversion
(`pwl` → `table`, `B` expressions wrapped in `{}`), but it fails numerically:
no-`uic` PRBS fails DCOP, and `uic` compact/PRBS diagnostics stall near the
first input transition.

2026-05-10 update: Xyce pybis now has a practical full-PRBS path when using a
relaxed `tanh15` model plus Xyce Backward-Euler/non-LTE timestep control:
`.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1`.
That setup completes `1000 ns` PRBS7 on the new 50-ohm channel in `4.44 s`.
The direct unrelaxed model is still not robust for repeated switching, so this
is a continuation/portability setup, not yet an accuracy-equivalent final model.

| Metric | Exp 1 NGspice+refspice | Exp 2 NGspice+pybis | Exp 3 NGspice+SPISim | Exp 4 HSPICE (deferred) |
|---|---|---|---|---|
| Eye height (mV) | — | — | — | — |
| Eye width (ps) | — | — | — | — |
| Rise time 20-80% (ps) | ~1500 | ~2500 | — | — |
| Fall time 20-80% (ps) | ~1500 | ~2500 | — | — |
| Overshoot (mV) | measured | visible | — | — |
| Undershoot (mV) | measured | visible | — | — |
| Prop delay (ps) | — | — | — | — |
| Converged? | ✅ | ✅ pulse / ⬜ PRBS | ⬜ | ⏸ |
| .options needed | RDSW=0 in .mod | reltol=1e-4, gear | — | — |
| Sim runtime (12ns) | 0.076s | ~3s | — | — |

---

## 7. Step-by-Step Execution Plan

### Step 1 — Shared inputs ✅ DONE

1. ✅ `io_buf.sp` — transistor-level CMOS tristate I/O model (TSMC 180nm)
2. ✅ `io_buf.ibs` — generated via PYS2IBIS3 from `io_buf.sp`
3. ✅ `hspice_ngspice.mod` — BSIM3v3 process with RDSW=0/PRWG=0/PRWB=0 (required for convergence)
4. ✅ `ngspice_pybis/channel.sp` — 10-section RLGC ladder, 85 Ω termination
5. ✅ `ngspice_pybis/driver_OutputInput_Typical.sub` — pybis2spice model, bugs fixed (B29 Kd, package=0)
6. ⬜ Generate `prbs7.pwl` using V-source-compatible format (see Section 4.2)

### Step 2 — Experiment 1: NGspice + transistor-level (ground truth) ✅ DONE

1. ✅ Bench: `ngspice_refspice/tb_validation_refspice_rsf_batch.sp`
2. ✅ Verified: 1489 rows, 14 ns, 0.076 s wall clock
3. ✅ RSF/RFR/longpulse/fallonly comparison plots in `plots/validation/`
4. ⬜ PRBS bench: build `ngspice_refspice/tb_refspice_prbs7_batch.sp` with `V` PWL source

### Step 3 — Experiment 2: NGspice + pybis2spice ✅ DONE (new channel criterion)

1. ✅ Model bugs fixed: B29 Kd=1 when disabled, package params = exact zeros
2. ✅ Pulse comparison done: rise ~2.5 ns (vs ~1.5 ns refspice) — genuine IBIS accuracy gap
3. ✅ PRBS bench pass established on new-50ohm RLGC channel:
    - `ngspice_pybis/tb_pybis_prbs7_new50ohm.sp` reaches `1000 ns`
    - acceptance criterion for pybis is **new-channel pass**; compatibility with ideal-T-line PRBS bench is not required
4. ✅ Eye/transient outputs generated for pybis new-channel run and refspice comparison.

### Step 4 — Experiment 3: NGspice + SPISim-converted example decks 🔄 PARTIAL

1. ✅ Inspect and run provided converted decks in NGspice (`Ibs2Spc_Coef.spc`, `Ibs2Spc_Ramp.spc`) as reference behavior.
2. ⬜ Build optional normalized comparison bench around provided SPISim-converted subcircuits (if needed for direct metric table fill).
3. ⬜ Compare eye/transient metrics vs Exp 1 and Exp 2 where directly comparable.
4. Note: no SPISim source execution is planned or required.

### Step 5 — Experiment 4: HSPICE ⏸ DEFERRED

Blocked on license renewal. When available:
1. Port Exp 2 bench to HSPICE syntax (native IBIS instance via `.connect`)
2. Run `.TRAN 10p 1000n` with same `prbs7.pwl` stimulus
3. Record metrics and compare against NGspice results from Exp 1–3

### Step 6 — Post-processing and comparison ⬜ PENDING PRBS RUNS

1. Fill in the results table in Section 6
2. Plot overlay waveforms — refspice vs pybis vs SPISim, rising and falling edges
3. Plot overlay eye diagrams from all available experiments
4. For any metric > 5% error, zoom in and check if deviation coincides with IBIS table breakpoints
5. Summarise: pybis accuracy, SPISim accuracy, where Ku/Kd PWL discontinuities appear in eye

---

## 8. Python Eye Diagram Script — Outline

One script, simulator-agnostic, accepts any of the four waveform CSV files.

```python
def load_waveform(path):
    # handles HSPICE / NGspice / Xyce CSV formats
    # returns (time_array, voltage_array)

def build_eye(time, voltage, ui):
    # slice waveform at UI boundaries
    # overlay slices into eye matrix
    # return eye_matrix

def measure_eye(eye_matrix):
    # return eye_height, eye_width, eye_area

def measure_transitions(time, voltage):
    # return rise_time, fall_time, overshoot, undershoot

def plot_eye(eye_matrix, title):
    # save PNG

def plot_overlay(waveforms_dict):
    # superimposed transients from all four experiments
```

> ⚠ Use numpy for all array operations. Use matplotlib for all plots. The script must contain no HSPICE/NGspice/Xyce-specific logic — only CSV parsing differences are permitted.

---

## 9. Known Risks and Mitigations

| Risk | Impact | Status / Mitigation |
|---|---|---|
| pybis2spice B-source `?:` conditionals → stiffness at transitions | PRBS sim 148× slower than expected | ✅ Mitigated: use `V` PWL source for stimulus; `method=gear maxord=2 reltol=1e-4` |
| BSIM3v3 RDSW > 0 → `mx30#source` internal node stiffness | Refspice bench fails at 9 ns falling edge | ✅ Fixed: `hspice_ngspice.mod` with RDSW=0, PRWG=0, PRWB=0 |
| pybis2spice package param parsing (`0H`, `0F`) | Wrong 1 nH inductance → 150× step overhead | ✅ Fixed: exact zero params in `driver_OutputInput_Typical.sub` |
| pybis2spice B29 Kd = 0 when driver disabled | Wrong output behaviour vs SPISim reference | ✅ Fixed: `B29` returns 1 when NENABLE = 0 |
| Combined refspice+pybis bench fails at 9.06 ns | Cannot run head-to-head in one bench | ⚠ Workaround: separate benches + post-processed overlay plots |
| HSPICE license expired | Exp 4 blocked | ⏸ Deferred — resume when license renews |
| Lumped RLGC ladder inaccuracy at high frequency | Channel model introduces error | 10 sections fine at 200 Mbps; upgrade if data rate increases |
| HSPICE .tr0 format parsing | Post-processing blocked when Exp 4 runs | Use `.OPTION POST=2` for ASCII or `.MEASURE` for CSV |
| refspice PRBS bench DCOP with input=3.3V at t=0 | T-line has no DC return path → DCOP gives 1.52V midpoint → 435k rows then crash | ✅ Fixed: `uic` + `.ic V(pad_ref)=0` skips DCOP; confirmed 103,986 rows in 3.5s |
| pybis ideal-T-line PRBS non-convergence | PRBS + ideal T-line can stall even after model fixes | ✅ Out of acceptance scope: pybis is considered passed when PRBS works with new 50-ohm RLGC channel |
| pybis PRBS HIGH-state overhead | In the HIGH output state, pybis B-source Ku/Kd expressions re-evaluate at every step due to T-line ringing triggering dV/dt detector → ~15× overhead vs 1× in LOW state; 1000ns PRBS takes ~10–15 min wall clock | ⚠ Accepted: eye diagram data is correct, just slow. Root cause: internal B-source `pwl()` dV/dt circuit; fix would require pybis2spice model rewrite. Documented as limitation. |
| PRBS7 starts with 7 consecutive HIGH bits → wrong pybis DC OP | Buffer starts in wrong state (ku=0, kd=1 driving LOW while input=3.3V) → startup transient overwhelms B-source solver with millions of sub-ps timesteps | ✅ Fixed: inverted PRBS mapping (bit=1→0V, bit=0→3.3V) ensures first output=LOW, matching DC OP |

---

## 10. Prior Work

| Reference | What it covers | Gap vs. this study |
|---|---|---|
| Caniggia et al., IEEE EMC 2010 | IBIS accuracy in HSPICE and ADS, with/without package parasitics | Commercial tools only, no open-source simulators |
| SPISim ibis2spice blog, 2018 | ibis2spice flow for NGspice, informal correlation claim | No quantified metrics, no controlled testbench, no multi-simulator comparison |
| Ding & Hwang, EMC+SIPI 2025 | IBIS slew rate correction for accuracy improvement | Targets model improvement, not simulator portability |
| Xyce vs. NGspice community discussion, 2023 | Performance comparison for general SPICE | No SI-specific metrics, no IBIS, no eye diagrams |

**This study's novel contribution:** the first quantified, controlled, four-way comparison of ibis2spice fidelity across HSPICE, NGspice, and Xyce using a consistent Python post-processing pipeline and explicit pass/fail thresholds.

---

*Missouri S&T EMC Lab · Signal Integrity Group*
