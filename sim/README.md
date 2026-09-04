# sim/

Simulator working directories and their outputs — the per-tool trees that
accumulated during the ngspice/Xyce/HSPICE comparison work.

| directory | what it holds |
|---|---|
| `hspice/` | HSPICE runs, S-parameter and native-IBIS experiments (~494 MB, the bulk of it) |
| `ngspice_pybis/`, `xyce_pybis/` | pybis subcircuits and runs under each engine |
| `ngspice_refspice/`, `xyce_refspice/` | the reference-SPICE counterparts |
| `plots/` | figures from those studies |
| `clean_ibis_vs_pybis_matched_pkg/` | the matched-package comparison and its timing-offset analysis |

These are outputs rather than inputs, and most are only referenced by archived
scripts. They are kept because several carry their own README and analysis that
is not reproduced elsewhere.
