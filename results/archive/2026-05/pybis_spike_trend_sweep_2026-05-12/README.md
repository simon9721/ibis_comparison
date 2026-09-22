# Pybis Spike Trend Sweep

Pattern family: `0000 + 1*pre_high + 0*low_gap + 1*post_high + 0000`.

Main sweep uses the same stressed channel as the corrected PRBS run:
2 ns UI, 30 cm coarse10 RLGC, loss x5.

Outputs:

- `spike_trend_summary.csv`: per-pattern metrics.
- `ngspice_validation.csv`: corrected ngspice pybis validation on selected patterns.
- `plots/fixed_channel_spike_history_heatmap.png`: history dependence.
- `plots/channel_spike_strength_heatmap.png`: length/loss dependence.
