# Status-Bucket HSPICE-ngspice Overlays

This is the simpler plot set: one signal per figure, with separate RX-side and TX-side overlays.

The cases are not split into simple good/bad because timing WARN is not automatically bad. Instead, folders describe what the audit actually says.

Source study: `C:\Users\sh3qm\code\ibis_comparison\results\sparam_rx_trust_v2_2026-06-11`

## Buckets

- `01_full_pass`: `5` cases. Overall HSPICE audit PASS: RX shape, RX timing, and TX/reflection checks pass.
- `02_rx_shape_pass_timing_warn`: `71` cases. RX shape matches HSPICE, but timing is WARN/ambiguous. Useful RX-shape evidence, not timing-certified.
- `03_rx_shape_pass_other_warn`: `0` cases. RX shape passes and timing is not the blocker, but another audit item prevents full PASS.
- `04_rx_shape_fail`: `4` cases. RX voltage-shape mismatch against HSPICE.
- `05_other_warn_or_fail`: `0` cases. Other WARN/FAIL cases that do not fit the main buckets.

Each bucket contains:

- `rx_side/`: one RX/output overlay per case
- `tx_side/`: one TX/input overlay per case

Plot scale policy:

- Small RX waveforms are plotted in mV with 1 mV major y-axis increments and at least a 4 mV span.
- Larger RX/TX waveforms are plotted in V with coarse rounded y-axis increments, usually 0.2 V.
- This avoids making sub-mV differences look visually huge.

See `index.csv` for metrics and exact figure filenames.
