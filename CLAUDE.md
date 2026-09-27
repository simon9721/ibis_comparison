# ibis_comparison

Making IBIS models survive short and stressed pulses. For each buffer, three results are
compared on the same bench:

- **transistor netlist in HSPICE**: the truth;
- **HSPICE native IBIS**: the bar to beat, not the target. Never tune toward it;
- **our model**: `pybis2spice` gate-state / current-limited-chain model in ngspice.

There are 12 buffers: `ex2`, `inv_chain`, `io_buf`, and 9 variants (`ex2_base`,
`ex2_nomiller`, `ex2_skewp`, `ex2_slowpre`, `ex2_weak`, `inv_base8`, `inv_skewp`,
`inv_stage4`, `inv_weak`). The open-drain parts (`opendrain`, `od_slowpre`, `od_weak`) are
a separate line of work.

Focus since 2026-09-18: **track 1**. It builds the model from the IBIS file plus one
stressed pad run, with no internal probing. Track 2 uses a measured Ku-vs-gate map instead,
which needs the transistor's internal nodes.

## Where things are

| need | go to |
|---|---|
| every current study, what it found, which script writes it | `results/INDEX.md` |
| archived studies (zips on OneDrive; the local `results/archive/` may be gone) | `results/ARCHIVE_INDEX.md` |
| which module owns which definition - **check before writing a script** | `docs/reusable_modules.md` (usage: `docs/shared_modules.md`) |
| source netlists, model cards, vendor IBIS (inputs, never generated) | `buffers/README.md` |
| buffer name -> supply and IBIS file | `VARIANTS` in `scripts/gate_ramp_prototype.py` |
| variant IBIS files | `results/{ex2,inv_chain}_variants_*/<variant>/selection/tr1ps/*.ibs` |
| **the track-1 recipe, step by step - what is fitted, selected, assumed, and why** | `docs/track1_recipe.md` |
| the same argument with figures | `docs/track1_explainer.template.html` -> `python scripts/build_track1_explainer.py`. The two must agree: `scripts/check_recipe_agreement.py` |
| the IBIS -> SPICE converter | `tools/pybis2spice/` (model text: `pybis2spice/subcircuit.py`) |
| IBIS file -> chain model `driver.sub`, one command | `scripts/build_chain_model.py` |
| simulator runs, parsing, stimuli, `cross()` | `scripts/spicelab.py`; deck text: `scripts/spice_decks.py` |
| meeting decks | `results/meeting_deck_<date>/` (each has a README naming its builder) |
| the Semiconductor Modeling book as JSON, with citations | `docs/book/` (`citations.md`, `takeaways.md`) |

`scripts/archive/` is **not dead code**. The stress axis and the figure palette live there
and are still authoritative. The root `README.md` describes the May-June layout and is
out of date.

## Environment

- **Python 3.14**, installed per user:
  `C:\Users\sh3qm\AppData\Local\Programs\Python\Python314\python.exe`, with numpy,
  matplotlib, python-pptx and pillow. Deck and book scripts also put
  `.codex_deps/presentation/python` on `sys.path`. Run scripts from the repo root:
  `python scripts/<name>.py`.
- **HSPICE and ngspice paths** come from `scripts/spice_tool_paths.py`; don't hard-code
  them. HSPICE is T-2022.06; ngspice 46 is in `.codex_deps/ngspice-46_64`.
- **Disk:** a sweep of ngspice builds writes tens of GB of `.raw`. Check free space before a
  large run; a full disk killed one on 09-21.

  **Compress raws, never delete them.** They are not scratch output - 65 scripts read them at
  build time, every deck figure builder among them, so deleting a study's raws means re-running
  its whole ngspice campaign before you can redraw a figure.

      py -3.14 scripts/compress_raws.py results/<folder>            # dry run
      py -3.14 scripts/compress_raws.py results/<folder> --apply

  It re-parses each `.gz` and compares it array-by-array against the original before removing
  anything, and stops the run on any mismatch. `eye_diagram.resolve_raw` then falls back to
  `<name>.gz`, so every caller keeps asking for `run.raw` and nothing else changes. Measured
  5.3-13x across the repo on 2026-09-26; all 45 deck and summary figures rebuilt byte-for-byte
  afterwards.
- **Shells:** Git Bash and Windows PowerShell 5.1. Put multi-line Python in a file, not a
  bash heredoc; backslash escapes get mangled.

## Rules that have already cost us

- **io_buf model card:** grade io_buf against `buffers/models/hspice.mod`.
  `hspice_ngspice.mod` is about 12 % strong. A model must be simulated against the card it
  was characterised from (`docs/model_card_rule.md`).
- **HSPICE deck headers:** write them with `spice_decks.hspice_header`. A first line of
  `.option post=2` is swallowed as the title, and no `.tr0` is written.
- **Native IBIS:**
  - `ramp_rwf` decides which V-T tables are used; `spicelab.vt_fixtures` says which exist
    (`docs/native_vt_waveform_modes.md`).
  - On the tr1ps variants, native dies at sampling below 5 ps. Use 5 ps or more.
- **Stress depth** is measured against the transistor's settled swing. Import the archived
  stress-sweep module; don't re-derive it.
- **Duplicate definitions:** a second definition of something that already has an owner
  drifts silently. If you must reimplement, say why in the docstring.

## Adding a study

1. Write `scripts/<topic>.py`. Its docstring states the question and names the output
   folder.
2. Write output to `results/<topic>_<YYYY-MM-DD>/`, with conclusions in `FINDINGS.md`
   (and `PLAN.md` for multi-step work). Keep run logs inside the folder, not at the
   `results/` root.
3. Run `python scripts/make_results_index.py` to update `results/INDEX.md`.
4. Never write into `results/archive/`.
5. Commit it. A study that is not committed does not exist for anyone else.

## Git: leave the tree clean, every time

**Finish each piece of work with `git status` clean.** Not "clean except for the outputs",
not "I will tidy it later" - clean. Check it before you say you are done, and say what the
state is.

- **Commit the script with the results.** A tracked file must never import an untracked one.
  This has already bitten: `scripts/build_0924_deck_figures.py` is committed and imports
  `build_0917_deck_figures`, `build_0918_deck_figures`, `build_explainer_figures`,
  `current_limited_stage_model` and `predriver_stage_probe`, none of which are - so the
  committed deck does not build from a fresh clone. Check with
  `git ls-files --error-unmatch scripts/<module>.py` before relying on an import.
- **Stage by name, never `git add -A` or `git add .`** - not even with a path, because
  `git add -A results/foo/` still sweeps every untracked file beneath it. One commit swept
  115 files under a message describing 11. List the paths you mean.
- **One commit, one subject.** If the staged set does not match the message, split it.
- **Never commit on the user's behalf outside the work you were asked to do.** Untracked
  files that were already there are theirs; ask before adopting them.
- Scratch work belongs in the scratchpad directory, never in the repo. Loose `.md` notes at
  the repo root are not a place to keep anything.
- `results/**/slides/` is gitignored on purpose - rendered slide PNGs are regenerable, the
  `.pptx` and its figures are not.

**PowerPoint:** a deck the user made is never edited in place. Write a versioned copy
(`..._v2.pptx`). An open file in PowerPoint is locked, so a save to the same name fails.
