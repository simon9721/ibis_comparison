# results/archive/

Study directories from earlier work, bucketed by month, in two batches. Every directory
here has a markdown write-up; a README that begins *"Generated 2026-09-21"* was written from
the folder's contents and the script that made it, and says what the folder is, not what it
found.

| bucket | dirs | loose files | batch 1 (09-03) | batch 2 (09-21) |
|---|---:|---:|---:|---:|
| 2026-05 | 35 | | 15 | 20 |
| 2026-06 | 97 | 2 | 55 | 42 + 2 files |
| 2026-07 | 21 | | 12 | 9 |
| 2026-08 | 82 | 20 | 51 | 31 + 20 files |
| 2026-09 | 45 | | | 45 |
| undated | 3 | | 2 | 1 |
| **total** | **283** | **22** | **135** | **148 + 22 files** |

Nothing in either batch was deleted. Moving an entry back to `results/` restores it
unchanged; tracked files were moved with `git mv`.

**Uploaded 2026-09-22** to OneDrive - University of Missouri, folder
`ibis_comparison_results_archive/`, as nine zips: one per bucket, with 2026-08 in four parts.
Together they hold 112,891 files and 12.0 GB zipped (87.7 GB unzipped). Each zip was tested
with `7z t` and its file count matched against the source folders before it was uploaded.
`results/ARCHIVE_INDEX.md`, which stays in the repo, names the zip that holds each entry.

## Batch 2, 2026-09-21

Before the archive went to cloud storage. **`BATCH_2026-09-21.md` lists every entry** with its
size, date, git-tracked file count, a one-line description and the documents that name it.

### How the split was made

An entry stayed in `results/` if any of these held:

- a script written or edited since 09-08 (the gate-state / track 1 / track 2 period: 70
  scripts, 83 with their imports, plus `scripts/deck_0918/`) names it, as a path it reads or
  as a source cited in deck speaker notes;
- it was produced since 09-08;
- it is a cache (`_golden_hspice_cache`), or the run log of a study that stayed.

Everything else moved: 170 entries, 38.7 GB, 36,902 tracked files; 103 entries stayed.

| thread | entries | size |
|---|---:|---:|
| scratch dirs of 08-19/20 (`_level_v2`, `_probe_*` ...) | 17 | 7.0 GB |
| loose files at the `results/` root (run logs, `codex.md`) -> `<month>/loose_files/` | 22 | 19 MB |
| S-parameter / BBS thread (June) | 38 | 5.9 GB |
| early IBIS/pybis phase (May-June) | 21 | 0.1 GB |
| IBIS replay phase (June-July) | 12 | 1.8 GB |
| hybrid / silicon Ku-Kd phase (August) | 15 | 23.1 GB |
| command layer / stress pedestal (09-01 to 09-07) | 45 | 1.8 GB |

Bucket = the month of the date in the name, else of the newest file. One exception:
`2026-09/kukd_fixture_variants_2026-08-28` is the 09-04 re-run of the study batch 1 archived
as `2026-08/kukd_fixture_variants_2026-08-28`; both kept, see the note at the top of its README.

### Verification

- All 170 moved (130 `git mv`, 40 wholly untracked with `mv`); git shows 36,902 renames.
- None of the 83 current scripts names a folder that is no longer in `results/`.
- 138 `results/<name>` paths in 16 documents (root `README.md`, `STATUS.md`, `0902_plan.md`,
  13 under `docs/`, two results write-ups, one memory note) were repointed here; every
  repointed path resolves. Bare folder names in prose and tables were left as they are.
- 61 of the 77 scripts older than 09-08 name an archived folder - mostly the scripts that made
  those studies. Rerun, they fail on a missing input or write a fresh folder in `results/`.
- Gitignored content (HSPICE `.tr0/.lis`, ngspice `.raw`, `*.log`) exists only on disk, not
  in git history; the cloud copy is the only other copy of that part.

## Batch 1, 2026-09-03

Archived because nothing active referred to them.

### How the split was made

A directory stayed in `results/` if any of these held:

- an active script or a root document names it as a literal path (59)
- another results `FINDINGS.md` / `README.md` refers to it (51)
- it is an underscore/cache directory (17)
- it is from this month (3)
- it matches `s2ibispy_parameter_selection_*`, which the selector builds
  dynamically and so cannot be checked by literal search (3)

Everything else moved here: 135 of 268.

### Verification

Every literal `results/` path named by the 44 active scripts and the root docs
was re-resolved after the move. All 59 real ones still resolve. Four names did
not, and all four are benign: three are *stems* my extractor truncated
(`golden_waveform_`, `s2ibispy_parameter_selection_`, `stress_method_matrix`),
which have 3, 3 and 1 live directories respectively; the fourth,
`edge_family_stress_crossflow_coarse10_80b_2026-05-11`, has never existed in the
working tree or in git history — it is a stale output path inside
`run_edge_family_stress_crossflow.py`.
