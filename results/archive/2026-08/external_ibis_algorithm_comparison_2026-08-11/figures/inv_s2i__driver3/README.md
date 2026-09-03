# inv_s2i.ibs / driver3

- Component: `invchain`
- Model type: `Output`
- Supply: `1.8 V`
- Full-swing legacy status/class: `COMPLETED` / `WARN`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | WARN | 41.424747038044856 | 0.0575554674607667 | 0.05990389432554306 |
| short_high | value_match_v2 | COMPLETED | CHECK | 212.2730479305907 | 0.16424187059236262 | 0.1639462534808016 |
| short_high | gate_state_full | COMPLETED | WARN | 47.310634338182936 | 0.0681156915069466 | 0.06140183069043689 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 49.06636194634509 | 0.06903426318396323 | 0.061240119760350493 |
| short_low | legacy | COMPLETED | WARN | 48.740371316831066 | 0.06862670175940876 | 0.0640868308862853 |
| short_low | value_match_v2 | COMPLETED | WARN | 48.808303945565896 | 0.07151468099139253 | 0.06697899715330272 |
| short_low | gate_state_full | COMPLETED | WARN | 46.52581804702178 | 0.06707914938437366 | 0.061380541110133684 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 48.58015504910129 | 0.06784299388511247 | 0.06316091263964328 |
