# Shared modules: how to use them

*2026-09-04*

[reusable_modules.md](reusable_modules.md) is the policy — *what owns what*, and
what went wrong when something was rewritten instead of imported. This is the
usage reference: what each shared module actually gives you.

All examples assume the standard preamble, which puts the shared code on the path:

```python
ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
```

`matplotlib` and `numpy` are vendored in `.codex_deps/presentation/python`, not
installed system-wide. A script that omits that path fails at `import matplotlib`.

---

## `spicelab` — run a simulator, get numbers back

The read side. Roughly: launch a simulator, find its output, parse it, pull a
named signal out.

| Function | Does |
|---|---|
| `hspice(run_dir, deck="run.sp", timeout_s=...)` | run HSPICE in a directory, return the `.tr0` path or `None` |
| `ngspice(run_dir, deck="run.sp", timeout_s=...)` | same for ngspice, returns the `.raw` |
| `run_spice(cmd, cwd, log_path, timeout_s)` | the generic launcher underneath both |
| `parse_hspice_tr0(path)` / `parse_ngspice_raw(path)` | to a `{name: array}` dict |
| `time_ns(raw)` | the time axis, in nanoseconds |
| `signal(raw, *names)` | first matching signal; raises listing what *is* there |
| `trace(raw, substring)` | fuzzy match, for ngspice's inconsistent naming |
| `load_waveform(path, node)` | parse and pull in one call |
| `pwl(points)`, `pulse(...)`, `clock(...)` | stimulus source text |
| `cross(t, y, level, rising=, after=)` | interpolated threshold crossing, `NaN` if never |
| `vt_fixtures(ibis)` | each `[Rising/Falling Waveform]`'s `V_fixture`, in file order |
| `default_hspice()`, `default_ngspice()` | resolved simulator paths |

```python
import spicelab as sl

tr0 = sl.hspice(run_dir, timeout_s=900)
r   = sl.parse_hspice_tr0(tr0)
t, v = sl.time_ns(r), sl.signal(r, "v(pad)")
t50 = sl.cross(t, v, 0.5 * v.max(), after=5.0)
```

Two worth knowing:

* **`cross`** existed in ten scripts in eight incompatible forms — some
  direction-aware, some rising-only. A rising-only copy returns `NaN` on a falling
  edge, which reads as "no event" rather than "wrong function". Use this one.
* **`vt_fixtures`** is needed to interpret any `ramp_rwf=1` result, because table
  order differs per buffer: `inv_chain` is (1.8, 0.0) while `io_buf` and `ex2` are
  (0.0, 3.3).

## `decks` — write the deck text

The write side.

| Function | Does |
|---|---|
| `hspice_header(title, options=, temp_c=, comment=)` | comment line, `.title`, `.option`, `.temp` — **in that order** |
| `ngspice_header(reltol=, abstol=, vntol=, gmin=, method=)` | `.options` for a pybis run |
| `supply(node, volts, name=)` | a DC source |
| `load(node, r_ohm, c_pf)` | the study load (50 Ω ∥ 2 pF) |
| `fixture(node, v_fixture, r_fixture=50)` | an IBIS-style fixture, deliberately no shunt C |
| `native_ibis(ibis_file=, model=, supply_v=, mode=, enable=, probe_state=)` | the B-element and its reference supplies |
| `tran(step_ns, stop_ns, probe=)` | `.probe`, `.tran`, `.end` |
| `PybisSubckt.parse(path)` | a generated `driver.sub`: `.name`, `.pins`, `.enable_level(v)`, `.nodes()`, `.instance()` |

```python
import decks as dk

deck = (dk.hspice_header("stressed native")
        + f"Vin in_dig 0 {sl.pulse(0.0, 1.8, [5.0, 5.104], stop_ns=22.0)}\n"
        + dk.native_ibis(ibis_file="input.ibs", model="driver2",
                         supply_v=1.8, mode=2, buffer_type=2)
        + dk.load("pad", 50.0, 2.0)
        + dk.tran(0.002, 22.0, probe="V(pad)"))
```

Three traps it removes:

* **`.option post=2` as the first deck line is swallowed as the title**, so no
  `.tr0` is written and the run looks like the simulator doing nothing. This was
  the root cause of several "no output" failures. `hspice_header` fixes the order.
* **Driving `EN` to the wrong rail silently disables the buffer** — the pad never
  moves, which reads as a model defect. It produced a false finding on the
  open-drain bench. `PybisSubckt.enable_level` reads the polarity out of the
  generated subcircuit (`NENABLE ... V(EN,VSS) <` is active-low, `>` active-high)
  rather than trusting a flag.
* **`mode` is `ramp_rwf`: how *many* V-T tables, not which one.** 2 is the
  documented default and silently produces a dead pad on ex2 — see
  [native_vt_waveform_modes.md](native_vt_waveform_modes.md).

```python
sub = dk.PybisSubckt.parse(d / "driver.sub")
deck = (dk.ngspice_header()
        + ".include driver.sub\n"
        + dk.supply("VCC", 3.3, name="Vdd")
        + dk.supply("EN", sub.enable_level(3.3), name="Ven")
        + sub.instance("X1", {"OUT": "OUT"})
        + dk.load("OUT", 50.0, 2.0))
```

**Migration caveat:** `decks` formats numbers with `%g`, so `50.0` → `50`. That is
identical to SPICE but *not byte-identical*, so converting an existing script
invalidates its deck-text run cache and forces re-simulation. Convert when writing
something new, or when results are being regenerated anyway.

## `figures` — one palette, and editor recipes

```python
import figures as fg

fg.SILICON, fg.NATIVE, fg.NATIVE1, fg.METHOD_COLORS
fg.ORDER          # {source: (colour, linewidth, zorder)}, silicon heaviest, on top
fg.recipe_for_case(csv_path, "ku")   # a figure-editor recipe for one field
fg.case_title(case_dir, "pad")
```

The palette is *re-exported*, not copied, from
`scripts/archive/plot_stress_matrix_methods.py`, which set the conventions the
study's 496 per-case figures already follow. Importing `figures` gives active code
an entry point that is not an archived path, without creating a second definition.

## The figure editor — restyle without re-running anything

`tools/figure_editor/` is a CSV-backed Matplotlib editor. Style lives in a JSON
recipe beside the data; the same recipe opens in a GUI or renders headlessly.

```
scripts\launch_figure_editor.cmd <recipe>.json        # GUI
py -3.14 tools/figure_editor/figure_editor.py <recipe>.json --render out.svg
```

Editable: plotted columns, label, colour, width, style, marker, alpha, draw order,
title and axis labels, font family and sizes, axis scales and limits, grid, legend
position and columns, canvas size, background, DPI, transparency.

Generate recipes for a whole tree:

```
py -3.14 scripts/make_figure_recipes.py                        # default tree
py -3.14 scripts/make_figure_recipes.py --root results/foo --render svg
py -3.14 scripts/make_figure_recipes.py --glob 'waveforms/*.csv' --force
```

One recipe per field (pad, Ku, Kd) is written beside each per-case CSV, already
carrying the palette and draw order. Recipes are cheap deterministic text
referencing the CSV by relative path, so regenerating is always safe.

**Why this matters:** before, restyling a generated figure meant editing a
plotting script and re-running the sweep — sometimes hours of simulation to change
a colour. Now it is a GUI edit and a headless re-render.

**Scope:** the editor handles one axes and one CSV per recipe by design.
Multi-panel figures stay script-generated; export each panel separately when it
needs manual styling.

## `lib/paths` — find the repo root

```python
from lib.paths import repo_root
ROOT = repo_root()      # by marker (scripts/, results/, .git), not parents[N]
```

`parents[N]` breaks the moment a script moves between `scripts/` and
`scripts/archive/`, which has happened.

## Writing a per-case CSV that all of this understands

The conventions the recipe generator and the figure code both assume:

* one row per timestep, a `time_ns` column
* one column per `<source>_<field>`, where *source* is `silicon`, `native`,
  `native_rwf1`, `gate_state`, `delay_cmd`, `legacy` and *field* is `pad`, `ku`,
  `kd`
* every model resampled onto the transistor's time axis, so columns are
  directly comparable row-by-row
* optionally `silicon_cond`, the two-fixture solve's conditioning — a Ku/Kd that
  came from a near-singular solve is not a statement about the buffer

Write one of these and per-case figures, recipes and vector exports all follow
without further work.
