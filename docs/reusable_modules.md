# Where the canonical definitions live

*2026-09-04*

This study now has ~250 scripts. The failure mode is not writing a bad script —
it is writing a *second* definition of something that already had one, and having
the two drift. This page is the map: before writing a new script, check whether
one of these already owns what you need.

## The incident that prompted this

The variant stress sweep needed pulse widths at which the transistor reaches
90/80/70/60/50% of its full loaded swing. That was written from scratch, and got
two things wrong that the existing implementation had right:

* **The full-swing reference was the widest *stressed* width** — but that pulse is
  itself truncated, reaching only 90.8% of the settled level on `inv_weak`, 94.2%
  on `ex2_base`, 96.9% on `inv_base8`. Every depth came out 3–9% optimistic; a
  case labelled 50% was really near 45%.
* **Width selection was interpolation, not bisection** — which cannot reach below
  the narrowest width already simulated, so on three variants the 50% and 70%
  targets collapsed onto one duplicate case and the shallow end went uncovered.

Both were already solved in
`scripts/archive/run_three_buffer_loaded_swing_stress_sweep.py`, which is still
authoritative: the *active* stress matrix reads the `selection.csv` it produced.
It is in `archive/` because it has been run, not because it is superseded.

**Being in `scripts/archive/` does not mean a module is dead.** Check what it
owns before assuming.

## The map

| Concern | Owner | Notes |
|---|---|---|
| Running a simulator, parsing output, building stimuli | `scripts/spicelab.py` | `run_spice`, `hspice`, `ngspice`, `pwl`/`pulse`/`clock`, `signal`/`trace`/`time_ns`/`load_waveform`, `parse_hspice_tr0`/`parse_ngspice_raw` |
| Threshold crossing | `spicelab.cross` | direction-aware, interpolated, NaN when it never crosses |
| Which native V-T tables exist, and at what fixture | `spicelab.vt_fixtures` | needed to read any `ramp_rwf=1` result |
| Finding the repo root | `scripts/lib/paths.py` → `repo_root()` | by marker, not `parents[N]` |
| **The stress axis** — targets, tolerance, iteration cap, the settled control pulse | `scripts/archive/run_three_buffer_loaded_swing_stress_sweep.py` | `TARGETS=(0.9…0.5)`, `TARGET_TOLERANCE=0.01 V`, `MAX_SEARCH_ITERATIONS=10`, `control_case()` = 10 ns, `LOAD=(50 Ω, 2 pF)`, `anchor="transistor"` |
| Silicon Ku/Kd from two fixtures | `scripts/extract_silicon_kukd.py` → `solve_silicon_kukd`, `FixtureWaveform`, `R_FIXTURE`, `CORNER` | mirrors `pybis2spice.solve_k_params_output`; only the waveform source differs |
| Buffer/​case registries and transistor decks | `scripts/run_three_buffer_realistic_pulse_campaign.py` | `Device`, `Profile`, `PulseCase`, `DEVICES`, `transistor_deck`, `copy_transistor_inputs`, `fmt` |
| Which pybis builds exist, and their subckt names | `scripts/run_stress_method_matrix.py` → `METHODS` | `gate_state` → `…DirectionalDualResidualFull`, `delay_cmd` → `…DelayCommandFull`, `legacy` → plain `InputDriven` |
| Per-case figure conventions and palette | `scripts/archive/plot_stress_matrix_methods.py` | `SILICON`, `NATIVE`, `METHOD_COLORS`; keep new figures readable beside the existing 496 |
| The IBIS model itself | `tools/pybis2spice/` | `DataModel`, `solve_k_params_output`, `generating_current_data`, `subcircuit.generate_spice_model` |

## Anchors are a choice, and must be stated

The stress sweep takes `anchor="transistor"` (default) or `anchor="native"`. This
is not cosmetic. **The transistor is the anchor for stress depth**, because native
IBIS mis-swings on exactly the buffers under test — dead on ex2, over-swinging on
inv_chain — so anchoring on it would define the stress axis with a broken ruler.
Any script that sets a depth target states which anchor it used.

## Known duplication still outstanding

Measured across active (non-archived) scripts:

| Duplicated thing | Active copies | Status |
|---|---|---|
| `def cross(...)` | 10, in **8 incompatible forms** | canonical version now in `spicelab.cross`; private copies not yet migrated |
| `SILICON`/`NATIVE`/`METHOD_COLORS` | 4 | should import from the plot module |
| `ramp_rwf=2` literal | 13 | it is the documented default, so correct — but see [native_vt_waveform_modes.md](native_vt_waveform_modes.md) before trusting a native result |
| tr0/raw parsing | 2 | should use `spicelab` |

The `cross` count is the one that matters: eight incompatible contracts for the
same operation, where a rising-only copy silently returns NaN on a falling edge —
reported as "no event" rather than "wrong function". Migrate opportunistically
when touching a script; do not mass-edit untested.

Eleven active scripts already import `spicelab`, so the shared path works; it just
is not the default habit yet.

## Checklist before writing a new script

1. Does `spicelab` already run/parse/measure this?
2. Is there a registry (`DEVICES`, `METHODS`) rather than a literal to hardcode?
3. If it defines a *target* — depth, width, threshold — does an existing sweep
   already define it, and what does it anchor on?
4. If it plots, does it match the existing palette and conventions?
5. If it reimplements something, say why in the docstring. A second definition
   with a stated reason is fine; a silent one is how these drift.
