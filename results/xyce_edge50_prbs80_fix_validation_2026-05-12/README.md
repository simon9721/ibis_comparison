# Xyce Edge50 PRBS80 Fix Validation

Validation of promising PRBS62 fixes on the original 80-bit coarse RLGC stress deck.

| Variant | Completed | End ns | Return | Timeout | Wall s | Last NX ns | Note |
|---|---:|---:|---:|---:|---:|---:|---|
| gear2_nl50 | True | 160.000 | 0 | False | 19.43 | 1.880 | solver-only fix: Gear order 2, nlmax 50 |
| edge_delay20p | False | 158.370 | timeout | True | 180.01 | 0.240 | model-parameter fix: internal edge delay 20 ps |
| gear2_edge_delay20p | False | 108.280 | timeout | True | 180.02 | 0.180 | combined solver plus model-parameter fix |
| gear1_nl8 | True | 160.000 | 0 | False | 20.44 | 1.880 | minimal solver fix: Gear order 1 with original nlmax 8 |

## Recommendation

Use `.options timeint method=gear maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1` for Xyce pybis PRBS/RLGC stress decks. This is a simulator setup fix, not a pybis model edit.

## Key Files

- `plots/prbs80_gear_fix_122ns_window.png`: baseline trap timeout vs Gear pass around the original 122 ns stall.
- `plots/prbs80_gear_fix_full_rx_overlay.png`: full receiver waveform through 160 ns.
- `gear_fix_difference_metrics.csv`: pre-timeout baseline-vs-Gear and Gear1-vs-Gear2 difference metrics.
