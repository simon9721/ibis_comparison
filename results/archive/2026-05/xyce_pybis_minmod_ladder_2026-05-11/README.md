# Xyce pybis Minimum-Modification Ladder

This folder consolidates the current Xyce pybis modification ladder for
the 50 ohm RLGC benches. Candidates are ordered from closest to the
direct converted model to the current practical full-PRBS workaround.

## Key Takeaways

- Direct tanh200 on the repeated RLGC pulse train: fail/stop 33.9 ns.
- `tanh92` reaches the deterministic RLGC benches, but has no accepted full-PRBS pass.
- `edge50_flat4p2` passes 200 ns PRBS but stops on the 1000 ns run.
- `edge15_flat4p2` is the current full 1000 ns PRBS/RLGC pass.
- Broad all-`tanh15` also passes full PRBS, but with larger waveform error.

## Files

- `xyce_pybis_minmod_ladder_summary.csv`: consolidated table
- `xyce_pybis_minmod_ladder_matrix.png`: pass/fail matrix

Run missing points later with:

```powershell
python scripts\run_xyce_pybis_minmod_ladder.py --run-missing
```
