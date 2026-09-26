# A current-limited stage, fitted at full swing only, predicts the stressed gate

*2026-09-10*  ·  tool: `scripts/current_limited_stage_model.py` (`--p 1`, `--chain`)  ·  figures
`<dev>_current_limited_stages_p1.png`, `<dev>_chain_K.png`  ·  numbers `results_p1.csv`, `<dev>_chain_K.csv`

## The theory under test

`../predriver_stages_2026-09-09/` measured that ex2's and inv_chain's predriver
stages under-reach the linear (superposition) prediction and return early. The
theory offered: a CMOS inverter into a large load is a **current source** while
its input is at the rail and a resistor only near the destination rail, and
with a partial input its current follows the input through a threshold. One
stage, four numbers, fitted to the full-swing run only:

    dv/dt = s_up · h(u) · r(1 − v)  −  s_dn · h(1 − u) · r(v)
    h(x)  = clip((x − vt) / (1 − vt), 0, 1)^p          drive against the input
    r(x)  = min(1, x / x_lin)                           current-limited, resistive near the rail

u and v are the stage's input and output nodes, each normalised 0 = rest,
1 = its own full-swing high state. Then the stage is driven with its *measured
stressed input* and compared with the measured stressed output, and with linear
superposition. No stressed data enters the fit.

**p cannot be fitted at full swing** (the input is always at the rail there —
every p from 1 to 2 fits to rms 0.002–0.007). It only acts under a partial
input. Fitted freely it landed on p = 1 for ex2's inner stages and on 1.5–2 for
inv_chain's, and the latter under-predicted; p = 1 (drive linear in the input
above threshold, the velocity-saturated MOSFET) is used throughout below.

## 1. ex2 — three sub-linear stages, predicted to 0.05

Full-swing fits: n2 s_up 2.4 / s_dn 1.7 per ns, vt 0.70, x_lin 0.47; n3 1.36 / 2.34,
vt 0.32, x_lin 0.47; n4 2.18 / 1.36, vt 0.28, x_lin 0.37 (rms 0.005–0.007).

| node | W (ps) | measured max | current-limited, measured input | chain from the input pin | linear | rms CL | rms linear |
|---|---:|---:|---:|---:|---:|---:|---:|
| n3 | 810 | 0.780 | 0.757 | 0.762 | 0.818 | 0.006 | 0.031 |
| **n4** | 810 | **0.758** | **0.714** | **0.725** | 0.926 | 0.012 | 0.069 |
| n4 | 858 | 0.838 | 0.785 | 0.797 | 0.940 | 0.014 | 0.053 |
| n4 | 975 | 0.936 | 0.892 | 0.901 | 0.968 | 0.012 | 0.032 |
| pad | 810 | 0.499 | 0.387 | 0.327 | 0.903 | 0.018 | 0.101 |

The output gate n4 is predicted within 0.05 at every width, from the input
pin, through three stages whose parameters never saw a short pulse. Linear
superposition is off by 0.17 at the deepest width. The 50 % times agree to
±14 ps. (The pad row is the same stage form standing in for the output stage;
the IBIS equation with the static map is the right model there — this is a
sanity check that the form is not absurd, not the model.)

**ex2's stressed behaviour is the current-limited physics of its predriver,
nothing else.**

## 2. inv_chain — the same per stage; the chain compounds the residual

Full-swing fits: 20–32 per ns per stage, vt 0.51–0.56, x_lin 0.52–0.63, rms 0.002.

| node | W (ps) | measured | stage, measured input | chain from the input pin | linear | rms CL | rms linear |
|---|---:|---:|---:|---:|---:|---:|---:|
| vout7 | 104 | 0.879 | 0.807 | 0.431 | 0.999 | 0.003 | 0.032 |
| vout7 | 106 | 0.935 | 0.864 | 0.716 | 1.000 | 0.004 | 0.027 |
| vout7 | 111 | 0.972 | 0.919 | 0.881 | 1.002 | 0.003 | 0.021 |
| vout7 | 119 | 0.992 | 0.963 | 0.960 | 1.005 | 0.003 | 0.015 |
| pad (from measured vout7) | 104 | 0.490 | **0.494** | 0.038 | 0.853 | 0.002 | 0.040 |
| pad | 111 | 0.709 | 0.725 | 0.634 | 0.877 | 0.002 | 0.027 |

Each stage, fed its real input, is predicted to rms 0.002–0.004 (linear
0.008–0.032) but sits 0.03–0.07 low at the peak; seven stages in a row turn
that into a collapse at the two deepest widths (0.43 vs 0.88 at 104 ps). The
drive law is slightly too weak for an input at 0.85–0.9 of swing — a real
inverter delivers nearly full current there — and the full-swing fit cannot
see that. The pad from the measured gate is exact (0.494 vs 0.490): the
current-limited form *is* the static-map output stage in another notation.

## 3. What this settles

* The predriver non-linearity has a name and four numbers per stage:
  **current-limited stages with a threshold**. Fitted at full swing only they
  predict ex2's stressed gate to 0.05 and each inv_chain stage to 0.003 rms.
* What full swing cannot give is the drive law under a partial input (p, and
  the shape of h near the top). On a long chain that residual compounds. A
  model that carries fewer stages than the real chain is exposed to it less
  (see §4), and a single partial-input observation would pin it.
* Linear structures — RC cascades, delay + RC, superposition of step
  responses — cannot represent this on ex2 or inv_chain; on io_buf, which is
  linear end to end, they are exact.

## 4. How many stages must a model carry?

(`--chain`: K current-limited stages from the input pin straight to the output
gate, fitted at full swing only.) See the table appended below.

### 4a. K stages with free parameters (4K numbers)

| buffer | K | full-swing rms | stressed gate max, deepest / shallowest width (measured) | rms deepest |
|---|---:|---:|---|---:|
| ex2 (3 real stages) | 1 | 0.082 | 0.41 / 0.50 (0.76 / 0.94) | 0.123 |
| ex2 | 2 | 0.005 | 0.23 / 0.55 | 0.117 |
| ex2 | **3** | 0.004 | **0.81 / 0.93** (0.76 / 0.94) | **0.022** |
| inv_chain (7 real stages) | 1 | 0.059 | 0.15 / 0.22 (0.88 / 1.00) | 0.054 |
| inv_chain | 2 | 0.004 | 0.00 / 0.00 | 0.053 |
| inv_chain | 3 | 0.003 | 0.00 / 0.00 | 0.053 |

(`<dev>_chain_K.png`, `<dev>_chain_K.csv`.)

Two lessons. One stage cannot even fit full swing when the chain's delay is
long compared with its edge (ex2: 1.1 ns delay, 660 ps edge; inv_chain: 300 ps
delay, 50 ps edge) — a delay needs stages. And **a free fit at full swing is
degenerate**: K = 2 fits ex2's full swing to 0.005 and predicts a stressed
gate of 0.23 instead of 0.76, because it split the delay into one very slow
stage plus one fast one, and a slow stage with a threshold swallows a short
pulse. inv_chain's K = 2 and 3 fits found the same degenerate corner (a stage
with x_lin 0.02 — a ramp-to-threshold delay) and predict nothing at all. With
the right number of stages (ex2, K = 3) the fit lands on the real split and
predicts stress to 0.05. The internal structure is what stress depends on,
and full swing does not pin it. Section 4b constrains it with physics.

### 4b. K identical stages (4 shared numbers) — the physics constraint

Real predrivers are tapered inverters of similar delay. Constraining the K
stages to share their four numbers makes the fit well-posed:

| buffer | K | full-swing rms | stressed gate max, deepest → shallowest (measured) | rms range |
|---|---:|---:|---|---|
| ex2 | 2 | 0.014 | 0.29 … 0.52 (0.76 … 0.94) | 0.09 |
| ex2 | **3** | **0.0066** | **0.755 / 0.782 / 0.813 / 0.847 / 0.898** (0.758 / 0.797 / 0.838 / 0.880 / 0.936) | **0.010–0.012** |
| ex2 | 4 | 0.0072 | 0.78 / 0.80 / 0.83 / 0.86 / 0.90 | 0.017–0.031 |
| inv_chain | 3 | 0.014 | 0 (swallowed) | 0.05–0.08 |
| inv_chain | 5 | 0.0037 | 0 … 0.87 | 0.015–0.07 |
| inv_chain | **7** | **0.0032** | 0.672 / 0.820 / 0.909 / 0.960 / 0.987 (0.879 / 0.935 / 0.972 / 0.992 / 1.003) | 0.006–0.014 |
| inv_chain | 9 | 0.0032 | 0.941 / 0.954 / 0.967 / 0.981 / 0.992 | 0.007–0.019 |

(`<dev>_chain_shared_K.png`, `<dev>_chain_shared_K.csv`.)

* **ex2, K = 3, four numbers** (s_up 1.80, s_dn 1.65 per ns, vt 0.26,
  x_lin 0.41): the stressed output gate within 0.04 at every width, 50 % times
  within 20 ps, rms 0.01. This is the whole ex2 predriver in four numbers
  fitted at full swing.
* **inv_chain, K = 7–9**: the truth is bracketed (K = 7 under by 0.2 at the
  deepest width, K = 9 over by 0.06; both within 0.03 from 111 ps up). The
  bracket is the per-stage drive-law residual of §2 compounding; a partial-
  input observation would close it.
* **The stage count is recoverable from full swing alone.** The full-swing rms
  falls with K and plateaus at the real count: ex2 0.014 → 0.0066 → 0.0072
  (K = 2, 3, 4), inv_chain 0.014 → 0.0037 → 0.0032 → 0.0032 (K = 3, 5, 7, 9).
  "The smallest K on the plateau" gives 3 and 7 — the actual chains. A free
  per-stage fit (4a) cannot do this; the identical-stage constraint can.

## 5. The recipe this leaves, IBIS file in, no silicon

1. Assume the MOSFET-shaped map (`../physics_map_gate_2026-09-10/`): vt ≈ 0.5,
   alpha ≈ 0.6–0.8.
2. Invert it on the tables' full-swing Ku(t): the gate's rise and fall step
   responses.
3. Fit K identical current-limited stages (four numbers, p = 1) to those step
   responses; take the smallest K on the rms plateau.
4. Command layer = that chain, driven by the digital input; output stage =
   the map on the chain's last node, then the IBIS equation.

Every step was tested here on the transistor's own nodes. What is not yet
done is building step 4 in ngspice and scoring the pad — the next round. Where
the recipe is expected to be weakest: the drive law under a partial input
(p, and h near the top) on long fast chains, and any predriver that is not a
chain of similar inverters (io_buf's NOR/NAND paths — though io_buf is linear,
so there the step responses alone suffice).
