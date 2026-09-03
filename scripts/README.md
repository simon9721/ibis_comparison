# scripts/

    scripts/*.py       43   active: this month's work, plus anything the docs
                            reference, plus everything those transitively import
    scripts/lib/        2   shared plumbing (repo_root; spicelab lives alongside)
    scripts/archive/  195   one-off studies, kept runnable but not maintained

## Why the split

The flat tree had grown to 238 files, which made the live work impossible to
find. The split is measured, not guessed: the active set is the closure of
(a) scripts touched since 2026-09-01, (b) scripts named in the root docs or in
this month's FINDINGS, and (c) everything those import, transitively. Everything
outside that closure is archived.

## Archived scripts still run

Moving a file one level deeper breaks `Path(__file__).resolve().parents[1]`,
which 135 of them used to find the repo root. Those were rewritten to
`parents[2]`. The rewrite was scoped to that exact expression, so the three files
using `parents[1]` on a *data* path were correctly left alone.

Archive-internal imports need no change: Python puts a script's own directory
first on `sys.path`, so an archived script importing another archived script
resolves it. Archive-to-active imports also work, because the shared modules
(`eye_diagram`, `spice_tool_paths`, ...) stayed in `scripts/` and the archived
files still insert `ROOT / "scripts"` on the path.

All 240 files compile.

## Writing something new

Prefer `scripts/lib/`:

    from lib import repo_root        # finds the root by marker, not by depth

`repo_root()` exists because `parents[N]` encodes how deep the caller sits and
silently breaks when a file moves — which is exactly what happened here. Anything
importing it can be relocated freely.

`spicelab` carries the SPICE plumbing: `run_spice`, `hspice`, `ngspice`,
`pulse`/`pwl`/`clock`, and `trace`/`signal`/`load_waveform`.
