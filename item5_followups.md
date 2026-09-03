# Item 5 follow-ups (deferred 2026-09-03)

Done this session: `scripts/spicelab.py` (shared SPICE plumbing), `.gitignore`
extended for HSPICE intermediates, and 3,305 pure-junk files untracked
(`.st0/.ic0/.pa0/.lis`). Tracked count 44,073 -> 40,768.

Deferred, by decision, to return to the pybis lag/gap investigation:

## 1. Untrack the remaining .tr0 waveforms (~1,014 files, ~60 MB)
Cannot blanket-untrack: 75 scripts reference `.tr0`, and some read *committed*
ones as golden references (e.g. `extract_silicon_kukd.py` reads
`edge_1ps_base_50r_2pf_hspice_transistor.tr0`). Needs a per-directory pass:
keep the .tr0 that scripts read, untrack the rest. Same for a review of tracked
`.sp` (26,783) and `.png` (6,224) -- most are regenerable, some are source.

## 2. Nested project structure
229 scripts in a flat `scripts/`, ~11 root markdown files, data dirs at root.
High risk: scripts cross-import (`sys.path.insert(0,"scripts"); import run_...`)
and carry hardcoded relative paths, so moving them breaks imports and results
references. Do incrementally with verification, not wholesale.

## 3. Adopt spicelab.py in existing scripts
New/edited scripts should import from `spicelab` instead of re-rolling `run()`,
`pwl()`, and trace lookups. Migrate opportunistically when a script is touched
for another reason; a mass rewrite is not worth the risk.
