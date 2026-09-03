# io_buf vs inv_chain: IBIS Waveform Failure Analysis

This report uses the existing IBIS files and pybis extraction code only. It runs
no HSPICE or ngspice simulations. Its purpose is to explain why the current
two-state gate model works for `inv_chain` but fails for the fast `io_buf` IBIS.

## Bottom Line

The fast `io_buf` failure is **not** caused by an ill-conditioned two-fixture
`Ku/Kd` linear solve. The maximum matrix condition number is only
`3.26`. The failure begins because the raw fast `io_buf` V-T
tables contain an immediate feedthrough/ringing event at the table boundary,
before a clean settled plateau exists.

That boundary event produces non-settled extracted coefficient samples:

- rising `t=0`: `Ku=0.623208`, `Kd=0.573315`
- falling `t=0`: `Ku=-0.390654`, `Kd=0.765360`

The current `gate_state_fit()` then averages those first samples with the valid
opposite-table final samples. It therefore identifies:

- `Ku_off=0.311605`, `Ku_on=0.302410`
- `Kd_off=0.382680`, `Kd_on=0.787069`

Those values do not describe a normalized off/on hidden state. Once that
incorrect identification enters the GUP/GDN fit, the later residual branches
can improve an offline reconstruction numerically but cannot make the runtime
state physically meaningful.

## What the IBIS Waveforms Show

### inv_chain

The slow and fast `inv_chain` waveform fixtures both have a clean pre-edge
interval created by the eight-stage inverter chain. Their extracted coefficient
tables begin and end near the settled states:

- low: `Ku approximately 0`, `Kd approximately 1`
- high: `Ku approximately 1`, `Kd approximately 0`

The two fixtures also remain synchronized: the worst `t50` separation in the
fast model is only `12.0 ps`. This supports a compact
single-progress-state interpretation.

### io_buf

The fast `io_buf` output begins moving within the first few picoseconds. The
first 50 ps contain a capacitive/feedthrough impulse; on the falling waveform,
the fixture voltage drops, rebounds, and only later enters its main transition.
The largest peak `|I_Ccomp| / |I_Rfixture|` ratio is `2.17`.
For both fast io_buf directions, the largest calculated `C_comp*dV/dt` term
occurs at `t=0`.

This follows directly from the extraction implementation. `differentiate()`
uses the forward interval `(V[1]-V[0])/(t[1]-t[0])`, and
`generating_current_data()` subtracts `C_comp*dV/dt` before solving Ku/Kd.
With no pre-edge sample, the first edge/feedthrough interval is assigned to the
first coefficient sample. That is acceptable for table replay, but it means
the first coefficient sample cannot also be assumed to be the settled endpoint.

The two io_buf fixtures also reach their main edges at very different times:
the worst `t50` separation is `1.814 ns`. This does not make the
2x2 solve singular, but it says the two loaded trajectories do not behave like
two synchronized observations of one simple hidden progress variable.
The slow io_buf separation is similarly large (`1.862 ns`), so fixture
desynchronization is a device/topology warning rather than the fast-model
failure by itself. The fast-model-specific evidence is the boundary impulse
and corrupted coefficient endpoints.

The slow `io_buf` model has the same asymmetric device, but its 1 ns excitation
suppresses the boundary impulse enough that the coefficient endpoints remain
valid. Its max endpoint error is only
`0.0062`.

## Why the Transistor Structures Differ

| Device | MOS | capacitors | output gate nodes | structural implication |
|---|---:|---:|---|---|
| io_buf | 30 | 14 | `n2;n3` | separate pullup/pulldown control paths and tri-state logic |
| inv_chain | 16 | 0 | `VOUT7` | tapered inverter chain with a shared final-stage gate node |

`inv_chain` is an eight-stage regenerative inverter chain. The final PMOS and
NMOS share the same final internal gate node. A fast external edge is therefore
isolated and regenerated before reaching the output devices.

`io_buf` is a tri-state I/O buffer. Its output PMOS bank and NMOS bank use
different internal control nodes (`n2` and `n3`) and unequal logic paths. The
netlist also contains explicit parasitic capacitors around those internal/output
nodes. A 5 ps input can therefore produce:

1. direct capacitive/feedthrough motion,
2. separate pullup and pulldown predriver timing,
3. a later main output transition.

One first-order GUP and one first-order GDN can model the slow main behavior,
but not the boundary impulse plus the later multi-path transition as one state
trajectory.

### Electrical context

| Device | Vdd | settled high into 50 ohm | effective pullup R | Ccomp | output Wp/Wn, L |
|---|---:|---:|---:|---:|---:|
| io_buf | 3.3 V | 1.5447 V | 56.82 ohm | 1.200 pF | 210.75/105.75 um, 0.90 um |
| inv_chain | 1.8 V | 1.4308 V | 12.90 ohm | 0.468 pF | 256.00/128.00 um, 0.18 um |

The output widths are similar in absolute size, but `io_buf` uses a much longer
output-device channel (`0.9 um` versus `0.18 um`) and is much weaker in the
shared 50 ohm check (`56.82 ohm` versus `12.90 ohm`). Its `C_comp` is also
larger (`1.2 pF` versus `0.468 pF`). These facts do not alone cause the fit
failure, but they make a fast boundary displacement current more important
relative to the conducting output network. The topology and waveform boundary
remain the decisive evidence.

## Exact Endpoint Evidence

| Model | rise start Ku/Kd | fall start Ku/Kd | max endpoint error | fitted off/on endpoints |
|---|---:|---:|---:|---:|
| io_buf_slow_1ns | 0.0039 / 0.9964 | 0.9977 / 0.0013 | 0.0062 | Ku 0.002/0.996; Kd 0.001/0.999 |
| io_buf_fast_5ps | 0.6232 / 0.5733 | -0.3907 / 0.7654 | 1.3907 | Ku 0.312/0.302; Kd 0.383/0.787 |
| inv_chain_slow_1ns | -0.0000 / 1.0025 | 0.9997 / -0.0000 | 0.0025 | Ku -0.000/1.000; Kd -0.000/1.002 |
| inv_chain_fast_5ps | -0.0000 / 1.0025 | 0.9997 / -0.0000 | 0.0025 | Ku -0.000/1.000; Kd -0.000/1.002 |

The damaging implementation assumption is visible in
`tools/pybis2spice/pybis2spice/subcircuit.py`:

```python
ku_off = mean(kr[0, Ku], kf[-1, Ku])
ku_on  = mean(kr[-1, Ku], kf[0, Ku])
kd_on  = mean(kr[0, Kd], kf[-1, Kd])
kd_off = mean(kr[-1, Kd], kf[0, Kd])
```

That is safe only when the first waveform sample is a settled endpoint. It is
true for both `inv_chain` IBIS files and the slow `io_buf` file; it is false for
the fast `io_buf` file.

## What Is Proven and What Is Inferred

**Proven from the cached data**

- The fast io_buf raw V-T tables contain strong first-sample/first-50-ps motion.
- Its extracted `Ku/Kd` starts are not settled endpoints.
- `gate_state_fit()` directly uses those starts to identify off/on values.
- The 2x2 extraction matrices are numerically well conditioned.
- The inv_chain tables have clean endpoints and synchronized fixture timing.
- The transistor netlists have fundamentally different output-control topology.

**Reasonable mechanism inference**

- io_buf's independent predriver paths and parasitic coupling explain why a
  very fast input creates an early feedthrough component that inv_chain's
  regenerative chain suppresses.
- The large fixture timing separation indicates load-dependent internal
  dynamics/Miller feedback that a two-state fit cannot uniquely identify from
  output V-T data alone.

Internal-node transistor transient probes would be needed to separate the exact
contributions of `n2`, `n3`, Ccomp, and each parasitic capacitor.

## Recommendation

Do **not** patch the fast io_buf result with more residual terms. The current
two-state method should reject this IBIS input using a waveform-quality gate:

- require a measurable settled pre-edge plateau,
- require coefficient endpoint consistency,
- report first-50-ps impulse magnitude,
- report fixture `t50` separation,
- confirm the 2x2 solve is conditioned.

For this file, retain legacy table replay. A principled future extension would
separate a quasi-static gate-state path from an explicit feedthrough/impulse
path, or regenerate the V-T tables with pre-trigger margin before the 5 ps
input edge. Merely changing endpoint averaging would remove one bug but would
not make the single-pole two-state model structurally adequate.

## Figures

- `plots/01_raw_vt_waveforms.png`
- `plots/02_first_100ps_boundary_zoom.png`
- `plots/03_extracted_kukd_tables.png`
- `plots/04_quality_metric_summary.png`
- `plots/05_fast_io_buf_failure_chain.png`

## Numeric Data

- `ibis_waveform_summary.csv`
- `k_endpoint_and_fit_summary.csv`
- `k_solve_diagnostics.csv`
- `transistor_structure_summary.csv`
- `electrical_context.csv`
- `source_manifest.csv`
- `waveform_data/<model>_<direction>.csv`

Every waveform-data CSV contains raw fixture voltages, extracted `Ku/Kd`,
condition number, determinant, fixture current, and Ccomp current on the common
time grid.
