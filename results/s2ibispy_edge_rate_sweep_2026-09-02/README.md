# s2ibispy: what is fixed, and what has to be chosen per buffer

Item 3 of `0902_plan.md` — remove the uncertainty from the SPICE-to-IBIS
conversion, so that when silicon and IBIS disagree on a new buffer we know we
are looking at the buffer.

## 1. The conversion is deterministic

The same config, run twice back to back, and run again five weeks after the
archived original:

| | bytes | lines | differing lines |
|---|---:|---:|---:|
| run 1 vs run 2 | 563,940 | 8,424 | **0** |
| run 1 vs the 2026-07-27 archive | 563,940 | 8,424 | **0** |

Byte for byte identical. **s2ibispy is not a source of run-to-run variation**,
so every difference measured below is attributable to the recipe alone, and a
sweep is a one-time cost per buffer.

Reproduce (`inv_chain`, fast 5 ps recipe):

```bash
export PYTHONPATH="C:/Users/sh3qm/code/s2ibispy/src;C:/Users/sh3qm/code/ibis_comparison/.codex_deps/s2ibispy/python"
export PATH="/c/synopsys/Hspice_T-2022.06/WIN64:$PATH"
cd results/inv_chain_s2ibispy_slow_fast_2026-07-27/inputs
py -3.14 -m s2ibispy ../configs/inv_chain_fast_5ps.yaml --outdir <dir> \
   --spice-type hspice --iterate 0 --cleanup 0 \
   --ibischk C:/Users/sh3qm/code/s2ibispy/resources/ibischk/ibischk7.exe
```

Two things about that invocation are easy to get wrong and both fail
confusingly. `PYTHONPATH` needs **two** entries — the tool source and the
vendored dependencies under `.codex_deps` — or it dies on `import yaml`. And it
must run **from the `inputs/` directory**, because the generated HSPICE decks
reference the transistor library by bare filename.

## 2. The historical instability, and where it stands

The July README documented the real failure: s2ibispy had a fixed 60 s per-job
timeout, HSPICE's first Windows launch can spend close to a minute in the OS
loader, and when that raced **the conversion continued** and emitted a
structurally valid `.ibs` with a missing typical pullup table. A silently wrong
file is worse than a crash.

The current source has hardened this in three places:

- a separate `HSPICE_COLD_START_TIMEOUT_SECONDS = 180` for the first launch,
  with the normal 60 s after it completes;
- an explicit guard — *"Never let a failed run be mistaken for success because
  an output from a previous run exists"*;
- per-job failures accumulate into a return code that `run_all` propagates and
  `cli.main` checks, plus an `ibischk` gate that returns 20 on any critical
  error.

All eight conversions in this sweep exited **0**.

**Operating rule: never accept an `.ibs` from a run whose exit code is not 0.**
Nothing downstream currently enforces that; it is a convention, and it would be
better as a validator.

## 3. Accuracy against the characterization edge

`tr = tf` is the free parameter. Swept over four decades on `inv_chain`, each
model scored on the July sanity bench — HSPICE native IBIS, 1 ps input edges at
5 and 15 ns, direct 50 ohm || 2 pF load, against the cached transistor run.

| tr = tf | pad RMSE vs transistor | rise 50% | shift | shift / tr |
|---:|---:|---:|---:|---:|
| 1 ns | 323.63 mV | 5.9197 ns | 600.8 ps | 0.60 |
| 500 ps | 229.37 mV | 5.6367 ns | 317.8 ps | 0.64 |
| 200 ps | 139.36 mV | 5.4563 ns | 137.4 ps | 0.69 |
| 100 ps | 87.45 mV | 5.3893 ns | 70.4 ps | 0.70 |
| 50 ps | 50.26 mV | 5.3550 ns | 36.1 ps | 0.72 |
| 20 ps | 24.18 mV | 5.3344 ns | 15.4 ps | 0.77 |
| 5 ps | 11.04 mV | 5.3245 ns | 5.5 ps | 1.10 |
| 1 ps | 6.98 mV | 5.3211 ns | 2.2 ps | 2.17 |

Transistor reference: rise 50% 5.3189 ns, fall 50% 15.3063 ns, peak 1.4308 V.

Two things to take from this.

**There is no plateau.** Accuracy improves monotonically across four decades,
323 mV down to 7 mV. Nothing suggests a point where a faster edge stops paying.
So on the accuracy axis alone the answer is always "as fast as possible".

**The error is mostly a timing shift, and the shift is a fixed fraction of the
characterization edge** — about **0.70 × tr** from 1 ns down to 20 ps, flattening
onto a ~2 ps floor below that, which is the bench's own resolution. That is a
usable predictor: characterizing at `tr` builds in roughly `0.7 tr` of lateness.

## 4. Usability is a separate axis, and it binds first

The sweep above scores the generated IBIS **under HSPICE**. Whether *pybis* can
consume the same file is an independent question, and `io_buf` shows the two
can disagree sharply.

From `results/io_buf_fast_edge_regen_2026-08-19/README.md`: a 5 ps edge put
io_buf's entire 3.3 V swing inside one 6 ps V-T sample, so the
`C_comp * dV/dt` term reached ~660 mA against a fixture current near 23 mA and
corrupted the endpoints, the onset delays and the gate-state maps. 20 ps was
clean enough to fit but stalled ngspice for 240 s on a study stimulus. 50 ps was
forced — **by convergence, not by accuracy**.

Running the same check across this sweep, `inv_chain` shows none of it:

| edge | max abs Ku | max abs Kd | verdict |
|---:|---:|---:|---|
| 1 ns … 1 ps | 1.012 | 1.029 – 1.031 | usable at every rate |

So the corruption is **buffer-specific**. io_buf breaks at 5 ps; inv_chain is
clean at 1 ps.

And io_buf's own sweep shows something inv_chain does not: a large skew floor
that no edge rate removes.

| edge | vs transistor | rise 50% skew |
|---:|---:|---:|
| 5 ps | 71.1 mV | +216 ps |
| 50 ps | 76.8 mV | +227 ps |
| 200 ps | 107.9 mV | +238 ps |

On inv_chain the shift falls to 2 ps as the edge sharpens. On io_buf it never
goes below ~216 ps. **That residual is not the characterization edge**, and it
is worth its own investigation — it is a candidate contributor to the
unexplained falling-edge lateness (defect B).

## 5. The procedure

There is no universal edge rate. Both gates are buffer-specific, and the
usability gate binds before the accuracy gate.

For every new buffer, before any silicon-vs-IBIS comparison:

1. Sweep `tr = tf` across at least 200 ps → 5 ps.
2. **Gate A, usability** — reject any model whose extracted `max abs Ku` or
   `max abs Kd` exceeds ~1.25, and any model that stalls ngspice on the study
   stimuli.
3. **Gate B, accuracy** — among the survivors, take the fastest edge.
4. Record the choice and the rejected candidates, as
   `io_buf_fast_edge_regen_2026-08-19` does.

Expect roughly `0.7 x tr` of built-in lateness at whatever edge is chosen, and
subtract that expectation before attributing a timing error to the model.

## Files

- `edge_rate_sweep.csv` — the table in section 3
- `plots/edge_rate_sweep.png` — RMSE and shift against edge rate, log axes
- `<tag>/inv_chain_<tag>.ibs` — the eight generated models
- `<tag>/inv_chain_<tag>.yaml` — the eight recipes, differing only in `tr`/`tf`
- `<tag>/sanity/` — the HSPICE bench for each

Generated by `scripts/sweep_s2ibispy_edge_rate.py`.
