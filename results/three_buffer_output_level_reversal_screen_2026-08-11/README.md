# Three-Buffer True Output-Level Reversal Screen

A passing event must reverse direction after reaching 5%-95% of the loaded output swing and must not complete the original full swing.

| Buffer | Selected UI | Data rate | Shared stress direction | Native partial directions | Transistor partial directions | Gate |
|---|---:|---:|---|---:|---:|---|
| io_buf | 1750 ps | 0.571 Gb/s | short_high | 1/2 | 1/2 | BOTH_REFERENCES_ONE_DIRECTION |
| inv_chain | 100 ps | 10.000 Gb/s | short_high | 2/2 | 1/2 | BOTH_REFERENCES_ONE_DIRECTION |
| ex2 | 750 ps | 1.333 Gb/s | short_high | 1/2 | 2/2 | BOTH_REFERENCES_ONE_DIRECTION |

- `screening_metrics.csv`: pad-at-command and final output-excursion evidence for every width.
- `selected_ui.csv`: per-buffer UI selected for the follow-on PRBS study.
- `plots/`: output excursion versus pulse width for native IBIS and transistor references.
