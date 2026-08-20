# Ku/Kd taken from the transistor during an interrupted pulse

The transistor is ground truth but exposes only a pad voltage, so a recovery law
could not be graded against it directly. Ku/Kd are not measured quantities,
though -- they are derived. pybis obtains them by driving the buffer through two
fixture loads and solving two equations for two unknowns at every time point.
Nothing in that procedure requires the buffer to be an IBIS model, so the same
solve applied to the transistor gives the Ku/Kd trajectory silicon actually
follows.

That matters because the recovery target was otherwise going to be native IBIS,
and native IBIS is wrong here in a specific and misleading way.

Extraction: [scripts/extract_silicon_kukd.py](../../scripts/extract_silicon_kukd.py)
Summary: [recovery_vs_silicon.csv](./recovery_vs_silicon.csv)
Per-case traces: [waveforms/](./waveforms) — figures in [plots/](./plots)

The I-V tables still come from the IBIS file. They describe the DC device
characteristic, which is not in question; only the switching coefficients over
time are. Both derive from the same transistor netlist via s2ibispy, so they are
mutually consistent.

## 1. Native IBIS is not a safe recovery target

On `io_buf` short-low, native IBIS Ku steps vertically from `0.03` to exactly
`1.000` at the reverse edge and stays flat. That is not fast recovery; it is the
IBIS engine abandoning the transition and clamping to the settled rail. Silicon
instead recovers smoothly over about 2.5 ns, and the gate-state model follows
that curve.

Post-reversal Ku error against silicon, time-weighted:

| case | native IBIS | gate-state model |
| ---- | ----------: | ---------------: |
| `io_buf` short-low 90% | 0.2808 | **0.0944** |
| `io_buf` short-low 70% | 0.3234 | **0.1073** |
| `io_buf` short-low 50% | 0.2927 | **0.1420** |
| `inv_chain` short-high 70% | 0.0540 | **0.0071** |
| `inv_chain` short-high 50% | 0.0506 | **0.0005** |

Fitting a recovery law to native IBIS would have taught the model to reproduce
that clamp. The worst model error against silicon across all 17 cases is
`0.2620`; the worst native-IBIS error is `0.3234`.

Where the model is genuinely weaker than native IBIS against silicon, it is by a
much smaller margin than the native-referenced numbers implied: `ex2` short-low
is `0.25-0.26` against silicon, not the `0.35-0.53` it scores against native
IBIS.

## 2. Recovery time does not scale with how far the device travelled

The standing hypothesis from earlier work was that a device only partly turned
off returns faster than one fully off, and that the fixed complete-edge delay
and tau are therefore the wrong law. This dataset does not support it.

`io_buf` is the only buffer here whose interrupted coefficient genuinely turned
off, so it is the only one that can test the question. Across a nearly twofold
range of interruption depth, silicon's recovery time is constant to within 3%:

| case | depth at reversal | silicon 63% recovery | model | model late by |
| ---- | ----------------: | -------------------: | ----: | ------------: |
| `io_buf` short-low 50% | 0.358 | 2066 ps | 2233 ps | 167 ps |
| `io_buf` short-low 70% | 0.612 | 2000 ps | 2166 ps | 167 ps |
| `io_buf` short-low 90% | 0.659 | 2031 ps | 2131 ps | 100 ps |
| `io_buf` short-high 50% | 0.910 | 1798 ps | 2132 ps | 334 ps |
| `io_buf` short-high 70% | 0.912 | 1851 ps | 2163 ps | 312 ps |
| `io_buf` short-high 90% | 0.919 | 1851 ps | 2148 ps | 298 ps |

Depth varies from `0.358` to `0.919`; silicon recovery stays between `1798` and
`2066 ps`. A fixed delay plus a fixed time constant is therefore the right
*structure*. The model's error is a roughly constant `100-334 ps` lag, which is
a calibration offset rather than a missing mechanism.

The earlier state-dependent finding was measured against HSPICE native IBIS, on
the slow model, using Kd 50% return. It may well describe native IBIS
faithfully. It does not appear to describe the buffer.

### What this data cannot settle

`inv_chain` and `ex2` cases have interruption depth of essentially zero -- their
pulses are so short the interrupted coefficient never moves -- so they cannot
test depth dependence at all. Confirming the result on those buffers needs a
sweep that deliberately targets intermediate depths, which the current
native-anchored axis does not produce for them.

## 3. Measurement note: use time-weighted error

These waveforms sit on HSPICE's adaptive time grid, which concentrates samples
wherever the circuit moves: on one `inv_chain` case, 127 of 283 samples fall
inside a 95 ps window of a 17 ns record. Averaging over samples weights by
sample density rather than by time, inflating any figure dominated by a brief
excursion.

The same case, both ways:

| | sample-weighted | time-weighted |
| --- | ---: | ---: |
| native IBIS vs silicon, Ku | 0.4995 | 0.0506 |
| model vs silicon, Ku | 0.0049 | 0.0005 |

Roughly a tenfold difference. Within a single case all flows share one grid, so
relative rankings are unaffected, but absolute values and any comparison across
cases are. This report integrates over time. The sweep runners still average
over samples and would need the same correction before their absolute figures
are quoted.

## Reproducing

```powershell
py -3.14 scripts/extract_silicon_kukd.py
```

Two new HSPICE fixture runs per case; every other reference is reused.
