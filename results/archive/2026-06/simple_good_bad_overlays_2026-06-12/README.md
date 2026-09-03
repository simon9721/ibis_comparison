# Simple Good/Bad HSPICE-ngspice Overlays

Classification rule:

- `good_cases`: overall HSPICE audit class is `PASS`.
- `bad_cases`: overall HSPICE audit class is `WARN` or `FAIL`.
- RX-shape-only status is still recorded in `index.csv`, but folder placement uses the stricter visual/pass-fail audit class.
- Each case has one clean RX-side figure and one clean TX-side figure.

Source study: `C:\Users\sh3qm\code\ibis_comparison\results\sparam_rx_trust_v2_2026-06-11`
Good cases: `5`
Bad cases: `75`

Folders:

- `good_cases/rx_side/`
- `good_cases/tx_side/`
- `bad_cases/rx_side/`
- `bad_cases/tx_side/`

See `index.csv` for metrics and exact figure filenames.
