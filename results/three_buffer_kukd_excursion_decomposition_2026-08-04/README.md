# Three-Buffer Ku/Kd Excursion Decomposition

This report uses cached CSV/raw data only. No HSPICE or ngspice simulation was run.

## Findings

1. **Some excursion is native behavior.** HSPICE native-IBIS `Ku/Kd` can leave `[0,1]`, especially for the fast `io_buf` file. These coefficients are fitted current multipliers, not literal transistor gate voltages.
2. **The severity is model dependent.** `inv_chain` stays close to `[0,1]`; `ex2` is moderate; fast `io_buf` is extreme. The old slow `io_buf` IBIS remains close to the nominal interval, so the problem is not universal to pybis.
3. **The hybrid adds an extra artifact.** In `io_buf short_high_1ns`, the largest one-step Kd change is `-0.969` at `6.037 ns`. At that instant, hybrid Kd is `-1.210`, while native IBIS is `0.483` and the full gate-state flow is `-0.210`.
4. **Why it happens.** The directional base map contributes `-0.423` and the signed rate residual contributes `-0.786`. They are keyed by different progress variables during retrigger, then summed. The hybrid switch exposes that inconsistent sum as a discontinuity.
5. **Practical rule.** Do not clip all Ku/Kd to `[0,1]`; that would erase legitimate native excursions. Instead, compare against the native-IBIS envelope and separately reject generated excursions caused by a large discontinuity or by terms whose progress states are inconsistent.
6. **The native fast-io_buf excursion is not a singular-matrix failure.** The exact 2x2 current solve has condition numbers near 3 at the worst samples. At 6 ps into the fast falling table, `Ku=2.193`, while the modeled capacitive current is `45.7 mA` versus `23.3 mA` fixture current. The sharp `C_comp*dV/dt` contribution changes the required-current vector enough that a `[0,1]` combination of static pullup/pulldown currents cannot balance it.

## Files

- `plots/01_three_buffer_short_high_1ns_ranges.png`
- `plots/02_io_buf_hybrid_kd_excursion_decomposition.png`
- `coefficient_ranges_by_case.csv`
- `io_buf_hybrid_event_samples.csv`
- `io_buf_hybrid_excursion_summary.csv`
- `io_buf_slow_fast_excursion_comparison.csv`
- `solve_conditioning/README.md`
- `solve_conditioning/conditioning_summary.csv`
- `solve_conditioning/solve_conditioning_vs_excursion.png`
