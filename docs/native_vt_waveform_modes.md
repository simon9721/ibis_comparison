# Native IBIS has two V-T playback modes, and they disagree

*2026-09-03*

## The short version

HSPICE's B-element does not simply "play the V-T table". Its `ramp_rwf` /
`ramp_fwf` keywords choose **how much** V-T data it uses, and the choice changes
the answer enough to have produced a false finding in this study.

Per the PrimeSim Continuum *Elements* manual, ch 4:

| value | meaning |
|---|---|
| `0` | use `[Ramp]` data |
| `1` | use **one** waveform — the first of that kind in the file |
| `2` | use **two** waveforms — the first two. **This is the default.** |

Thirty-two scripts here pass `ramp_rwf=2 ramp_fwf=2`. That is the documented
default and the two-fixture solve IBIS intends, so it is a defensible choice — but
it is not a neutral one.

## What it broke

The variant stress sweep reported that native IBIS **does not respond at all** on
ex2: the pad never leaves 0.03 V on a 1.05 ns pulse that the transistor takes to
1.47 V. That was read as native being an unreliable yardstick under stress.

It is not a stress effect. Re-running the same four cases with `ramp_rwf=1`:

| pulse width | transistor | native `=2` (default) | native `=1` |
|---|---|---|---|
| 700 ps | 0.1596 V | 0.0322 V | 0.0967 V |
| 820 ps | 0.8415 V | 0.0314 V | 0.5591 V |
| 900 ps | 1.2545 V | 0.0322 V | 1.2997 V |
| 1050 ps | 1.4682 V | 0.0308 V | 1.4357 V |

With one waveform native tracks the transistor. With two it is dead — and HSPICE
prints **no IBIS warning** either way. So the claim "native does not respond on
ex2" is retracted as a statement about IBIS: it is a failure of HSPICE's
two-fixture V-T solve on our generated ex2 tables.

Note the asymmetry that makes `=1` flattering here: it plays back the *first*
table, and the table order differs per buffer —

    inv_chain  (V_fixture 1.8, 0.0)     io_buf  (0.0, 3.3)     ex2  (0.0, 3.3)

Every bench in this study loads the pad with 50 Ω to ground, so on io_buf and ex2
the `=1` waveform is the load-matched one and on inv_chain it is not. A `=1` run
is therefore a best case, not a fair general model.

## io_buf is not affected

io_buf is the study's primary buffer and native is the bar every pybis number is
quoted against, so this had to be measured rather than assumed
(`scripts/native_vt_table_selection.py`):

| case | transistor | native `=1` | native `=2` |
|---|---|---|---|
| full swing | 1.5883 V, — | 1.5995 V, +13.0 ps | 1.6280 V, +13.5 ps |
| 1300 ps | 0.2565 V | 0.1668 V, +15.4 ps | 0.1435 V, +30.0 ps |
| 1150 ps | 0.1503 V | 0.0844 V, −3.1 ps | 0.0798 V, +14.2 ps |

The two modes agree qualitatively. At full swing the mode costs 28 mV of
excursion and nothing measurable in timing. **No io_buf conclusion changes.**

Worth separating from the mode question: under stress io_buf native under-responds
by ~40% *in both modes* (0.14–0.17 V against the transistor's 0.26 V at 1300 ps).
That is a real property of native, not an artifact.

## Why ex2 and not inv_chain — still open

`ramp_rwf=2` makes HSPICE solve for Ku/Kd from two fixtures. That is the same
solve s2ibispy performs, and its selector already flags ex2 for producing
out-of-range coefficients:

| variant | selector | native `=2` |
|---|---|---|
| ex2_base | rejected, max\|Ku\| 1.283–1.343 | dead |
| ex2_nomiller | rejected, 1.299–1.341 | dead |
| ex2_skewp | rejected, 1.589–1.714 | dead below 1250 ps |
| ex2_weak | rejected, 1.779–1.829 | dead below 1100 ps |
| ex2_slowpre | **passed** | dead below 1650 ps |
| inv_chain ×4 | all passed | tracks |

Four of five ex2 variants fail both the gate and native's solve, and all four
inv_chain variants pass both. But **ex2_slowpre passes the gate and still fails
native**, so `max|Ku| > 1.25` is not sufficient.

### Ill-conditioning: proposed, measured, ruled out

The obvious mechanism was that the 2×2 system

    M(t) = [[I_pu(V_A), I_pd(V_A)], [I_pu(V_B), I_pd(V_B)]]

goes near-singular on ex2 — the two fixtures failing to separate the operating
point, so Ku and Kd become the difference of two nearly identical rows. That would
explain both the dead pad and the inflated coefficients at once.

It is wrong. `scripts/two_fixture_conditioning.py` measures cond(M) across the
recorded transition:

| buffer | fixtures | median cond | max | samples > 100 |
|---|---|---|---|---|
| ex2_base | 0 / 3.3 V | 2.5 | 3.1 | 0% |
| ex2_weak | 0 / 3.3 V | 1.9 | 2.2 | 0% |
| inv_base8 | 1.8 / 0 V | 5.2 | 5.4 | 0% |
| io_buf | 0 / 3.3 V | 2.7 | 3.1 | 0% |

Every buffer is well-conditioned, and ex2 is conditioned *better* than inv_chain,
which does not fail. **No mechanism is established for either ex2's dead native
pad or its out-of-range Ku.** Both remain open, and the two are not yet known to
share a cause.

## A related trap that turned out to be benign

The same manual section says that if `rm_dly_rwf` / `rm_dly_fwf` are not set,
HSPICE behaves "equivalent to `rm_dly_fwf=default`" — i.e. it *strips the initial
delay* from the V-T waveforms. If that were happening, every native-vs-transistor
timing number here would be biased by the buffer's own delay.

It is not happening. io_buf's rising V_fixture=0 table has t50 = 1.753 ns, and
native's measured input-to-pad delay is 1.896 ns against the transistor's
1.883 ns. The delay is carried, not stripped. **Timing comparisons are sound.**

## What to do

* `scripts/spicelab.py` gains `vt_fixtures(ibis)`, which reports each waveform
  table's `[V_fixture]` in file order, so a `=1` result can be read knowing which
  fixture it came from.
* `scripts/variant_stress_depth_sweep.py` now runs **both** modes and reports
  both columns. Reporting one would either slander native or hide a real failure.
* Keep `=2` as the headline number — it is what IBIS intends — but never quote an
  ex2 native figure without saying which mode produced it.
* When a native result looks like a non-response, check the mode before concluding
  anything about IBIS or about pybis.
