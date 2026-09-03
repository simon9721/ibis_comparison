# results/archive/

Study directories from earlier work, bucketed by month. Archived because nothing
active refers to them.

## How the split was made

A directory stayed in `results/` if any of these held:

- an active script or a root document names it as a literal path (59)
- another results `FINDINGS.md` / `README.md` refers to it (51)
- it is an underscore/cache directory (17)
- it is from this month (3)
- it matches `s2ibispy_parameter_selection_*`, which the selector builds
  dynamically and so cannot be checked by literal search (3)

Everything else moved here: 135 of 268.

| bucket | dirs |
|---|---:|
| 2026-05 | 15 |
| 2026-06 | 55 |
| 2026-07 | 12 |
| 2026-08 | 51 |
| undated | 2 |

## Verification

Every literal `results/` path named by the 44 active scripts and the root docs
was re-resolved after the move. All 59 real ones still resolve. Four names did
not, and all four are benign: three are *stems* my extractor truncated
(`golden_waveform_`, `s2ibispy_parameter_selection_`, `stress_method_matrix`),
which have 3, 3 and 1 live directories respectively; the fourth,
`edge_family_stress_crossflow_coarse10_80b_2026-05-11`, has never existed in the
working tree or in git history — it is a stale output path inside
`run_edge_family_stress_crossflow.py`.

Nothing was deleted. Moving a directory back up one level restores it unchanged.
