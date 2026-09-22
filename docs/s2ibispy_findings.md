# s2ibispy: what we found, and what to do about it

Item 3 of `0902_plan.md`, closed 2026-09-02. This is the summary; the evidence
is in the two result folders named at the bottom.

---

## The short version

1. **The conversion is deterministic.** Same recipe, same output, byte for
   byte — across runs and across five weeks.
2. **The "instability" was a timeout race**, now fixed upstream.
3. **Two recipe parameters shape the model, and neither had ever been chosen.**
4. **There is now a procedure** that measures a buffer and picks both.
5. **Two of three buffers need no change.** Only inv_chain would move, and
   nothing has been adopted.

---

## 1. Determinism

The same config run twice back to back, and again five weeks after the archived
original, produced byte-identical IBIS — 563,940 bytes, 8,424 lines, zero
differing lines. s2ibispy is not a source of run-to-run variation.

## 2. The instability was a race, not randomness

The same recipe produced three different outcomes on three attempts: a valid
file, an invalid file rejected by ibischk, and a hard error. The cause was a
**60 s per-job SPICE timeout** firing on ~5 s of work because the machine was
busy. A timed-out job does not abort the conversion — the caller logs it and
continues, so the model is still written with a curve missing, and the failure
surfaces minutes later as something that looks nothing like its cause.

Fixed upstream (commit `a7b0ead` in the s2ibispy repo): timeout raised to 300 s
and made overridable via `S2IBISPY_SPICE_TIMEOUT`, and the ramp extraction now
refuses to emit `dV <= 0` rather than leaving it for ibischk.

**Still true and worth knowing:** a failed job logs and continues. Raising the
ceiling makes it far less likely to fire, but a partial model can still be
written. **Never accept an `.ibs` from a run whose exit code is not 0.**

## 3. The two parameters

**`tr` / `tf`** — the characterization input edge. Swept over four decades on
inv_chain, accuracy improves monotonically with no plateau: 323 mV pad RMSE at
1 ns down to 7 mV at 1 ps. The error is mostly a timing shift, and the shift is
a fixed fraction of the edge:

> **shift ≈ 0.70 × tr**

Characterize at 50 ps and you build in about 35 ps of lateness. Subtract that
expectation before blaming a model for a timing error.

**`sim_time`** — the capture window, and the one nobody had noticed. The V-T
table is **1000 uniformly spaced points across `sim_time`** (1000 is the IBIS
≥ 4.0 ceiling), so:

> **V-T sampling = sim_time / 1000**

`sim_time` must be long enough to capture the buffer settling and short enough
that 1000 points resolve the edge. inv_chain settles in 0.5 ns and was
capturing for 6 ns — **92% of its resolution spent describing a flat line**, and
its 18 ps output edge described by 3 points.

The two are coupled through that sampling, which is why tuning `tr` alone
leaves the resolution wherever the inherited window happened to put it.

## 4. The procedure

```
py -3.14 scripts/select_s2ibispy_parameters.py --config <recipe.yaml>
```

Needs only the recipe — component, driver model, netlist directory, supply and
fixture resistance are parsed from it. Pass 1 converts once to *observe* the
buffer. Pass 2 sets `sim_time` from the measured settling and sweeps `tr`,
gating each candidate on:

| gate | catches |
|---|---|
| exit code 0 | lost SPICE job, or ibischk errors |
| max abs Ku, Kd ≤ 1.25 | corrupted coefficient extraction |
| ≥ 5 V-T samples across the edge | grid cannot resolve the transition |
| HSPICE native IBIS runs | model loads but will not simulate |
| ngspice pybis subcircuit converges | stalls rather than solving |

## 5. Results, and what to adopt

| buffer | selector picks | vs today | verdict |
|---|---|---|---|
| io_buf | 6.48 ns / 50 ps | **same** | settled, no change |
| ex2 | nothing passes | — | **leave as-is** |
| inv_chain | 0.62 ns / 1 ps | differs | 3 → 29 edge samples, 11.04 → 4.12 mV |

**io_buf is the result that validates the approach.** The selector chose 50 ps
by a static coefficient check in seconds — the same answer the August work
reached by watching ngspice stall for 240 s. The numbers corroborate
independently: August recorded max abs Ku of 1.178 at 50 ps and 1.655 at 20 ps;
this run measured 1.180 and 1.714.

**Nothing has been adopted.** The study still points at the shipped models.
Switching inv_chain now would make its results incomparable across the boundary
mid-study; better to adopt when we regenerate anyway.

---

## What is still soft

- **The 1.25 coefficient limit is uncalibrated.** io_buf's good model is 1.178,
  its known-bad 20 ps model is 1.655 — decisive there. But ex2's *shipped* model
  is 1.244, so the gate slices through where that buffer has always lived, and
  every ex2 candidate was rejected at 1.28–1.34.
- **The settling margin should probably not be one constant.** It was wrong in
  both directions: 2.0 would have handed io_buf a window *coarser* than it
  already had; 1.25 truncated ex2 and made its extraction worse (1.244 → 1.299
  at the same edge rate, window alone changed).
- **ex2's max abs Ku sits at ~1.24 at every edge rate and every window.** A
  coefficient that should cap at 1.0 doing that regardless of settings is
  structural, not a tuning artifact. Unexplained.

**Standing rule:** run the selector on every new buffer, then *read the
numbers* rather than trusting the pass/fail. The verdict is authoritative on a
clearly-bad model and advisory on a borderline one.

---

## Evidence

- `results/archive/2026-09/s2ibispy_edge_rate_sweep_2026-09-02/` — the four-decade `tr` sweep,
  the 0.70 × tr law, determinism, the timeout diagnosis
- `results/s2ibispy_parameter_selection_*_2026-09-02/` — the selector on all
  three buffers; `FINDINGS.md` in the io_buf folder covers all three
- `scripts/sweep_s2ibispy_edge_rate.py`, `scripts/select_s2ibispy_parameters.py`
