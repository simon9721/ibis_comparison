# io_buf fast-edge IBIS regenerated at 50 ps

Replacement for the 5 ps fast-edge `io_buf` IBIS used by the three-buffer
studies. The 5 ps model is unusable for the gate-state flow, for reasons that
are a property of the file rather than of any model built from it.

Selected model: [io_buf_fast_50ps.ibs](./source/io_buf_fast_50ps.ibs)
s2ibispy recipe: [io_buf_50ps.yaml](./source/io_buf_50ps.yaml) (`tr`/`tf` = `5.0e-11`)

A 20 ps candidate is retained for reference. It was tried first and rejected --
see "Why 50 ps and not 20 ps" below.

Previous file, retained: `results/io_buf_fast_edge_retest_2026-06-05/source/io_buf.ibs`

## Why the 5 ps file had to be replaced

pybis forms the `C_comp*dV/dt` term with a forward difference. The V-T waveform
is sampled every 6 ps, so a 5 ps characterization edge puts the entire 3.3 V
swing inside one sample interval. The resulting capacitive current is roughly
`1.2 pF * 3.3 V / 6 ps ~ 660 mA` against a fixture current near `23 mA`, and it
lands in the first coefficient sample.

Three separate downstream fits then consume that corrupted sample:

- **Endpoints.** First/last-sample extraction returned `ku_off=0.312`,
  `ku_on=0.302` -- Ku with no identified on/off range at all.
- **Onset delay.** The spike crosses the 5% threshold immediately, collapsing
  all four fitted delays to 1.7-7 ps.
- **Gate-state maps.** The map pairs gate state against raw table values, which
  reach `Ku = 2.19`.

The broken endpoints had been masking the rest: a range of `0.302 - 0.312 ~ 0`
compresses the map so the excursion never shows. Once the endpoints were
repaired the map produced `Ku = 1.70` at runtime and ngspice collapsed at
7.59 ns, writing a 458 MB partial raw.

## Both a new file and code fixes were required

Neither alone is sufficient, and this was tested rather than assumed:

| | 5 ps file | regenerated file |
| --- | --- | --- |
| **old code** | endpoints, delays and maps all corrupt | delays still 15 ps |
| **fixed code** | still stalls (180 s, 115 MB raw) | converges |

The code fixes repair the endpoint and onset estimators, but the gate-state map
takes its values from the table itself, so a table containing a `2.19` excursion
still produces an out-of-range map however it is normalized. The two
`subcircuit.py` fixes -- settled-rail endpoint extraction, and
main-transition-anchored crossing times -- both leave already-clean models
bit-identical, verified against `inv_chain`, `ex2` and slow `io_buf`.

## Choosing the characterization edge

Each candidate was scored two ways: how clean the extracted coefficient table
is, and how well native IBIS still tracks the transistor on a full uninterrupted
edge -- the property a fast edge exists to provide.

| edge | raw `ku_off` | raw `ku_on` | max abs Ku | vs transistor | rise 50% skew |
| ----: | ----: | ----: | ----: | ----: | ----: |
| 5 ps | 0.3116 | 0.3024 | 2.193 | 71.1 mV | +216 ps |
| 20 ps | 0.0965 | 0.8648 | 1.655 | 72.5 mV | +216 ps |
| **50 ps** | **0.0387** | **0.9673** | **1.178** | **76.8 mV** | **+227 ps** |
| 100 ps | 0.0194 | 0.9834 | 1.089 | 85.2 mV | +231 ps |
| 200 ps | 0.0097 | 0.9926 | 1.043 | 107.9 mV | +238 ps |

Table quality improves monotonically with a slower edge; agreement with the
transistor degrades monotonically.

### Why 50 ps and not 20 ps

20 ps was selected first on the strength of the table above -- it is the fastest
edge whose fit is usable, at a cost of only `1.4 mV` and no measurable skew. It
then failed in practice. Its residual `max abs Ku = 1.655` still feeds the
gate-state map, and on the native-anchored `short_high` stimulus at `1988 ps`
ngspice stalled for the full 240 s timeout:

| edge | that stimulus |
| ---: | --- |
| 20 ps | **stall**, 240 s, 88 MB partial raw |
| 50 ps | completes, 8.3 s, 141,240 rows |
| 100 ps | completes, 3.1 s, 54,306 rows |

Convergence, not table cleanliness, is the binding constraint. 50 ps is the
fastest edge that converges on the stimuli this study actually uses, and it
costs `5.7 mV` and `11 ps` of skew relative to the 5 ps file.

## Effect on existing results

`scripts/run_three_buffer_realistic_pulse_campaign.py` points `io_buf`'s
`fast_ibis` at this file. Results generated before 2026-08-19 used the 5 ps
model and are not comparable for `io_buf`. `inv_chain` and `ex2` are unaffected:
neither their IBIS files nor their fitted parameters change.

`scripts/build_two_study_error_decomposition.py` detects and reports any
`io_buf` case still sourced from a pre-regeneration study rather than mixing
them silently.
