# Vector-Fit Audit Share Pack

Source study: `results/sparam_vector_fit_campaign_v2_smoke2_2026-06-18`

This folder packages the audited scikit-rf vector-fit cases with the exact models, HSPICE decks, ngspice decks, raw outputs, and one-side-per-figure overlays.

## Counts

- `FAIL`: `2` cases
- `PASS`: `1` cases

## Folder Layout

- `audit_pass/`: cases whose HSPICE audit passed.
- `audit_warn/`: cases with usable but caveated HSPICE agreement, usually fast-edge RX timing/shape sensitivity.
- `audit_fail/`: cases where HSPICE-vs-ngspice mismatch is large enough to reject the vector-fit model for that case.
- `index.csv`: machine-readable index of copied files and metrics.

The class names are audit outcomes, not value judgments about the original Touchstone channel.
