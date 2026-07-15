# Transistor Pad Recovery Timing Audit

This audit uses cached HSPICE `.tr0` files only. It asks whether the short-high pad recovery in the transistor-level `io_buf.sp` reference has a native-IBIS-like delayed hold, or whether it returns much sooner.

Definitions:

- `pad peak/turnaround`: first post-reverse pad maximum, where the short-high pulse stops rising and starts returning low.
- `pad 50% return`: first falling crossing halfway from that post-reverse pad peak back to the tail/final voltage.
- `native Kd 50% recovery`: native HSPICE IBIS coefficient recovery from Kd minimum to final, included only as coefficient-model context.

## Result

| Case | Native Kd hold50 ns | Native pad 50% return ns | Transistor pad 50% return ns | Transistor minus native Kd ps | Classification |
|---|---:|---:|---:|---:|---|
| short_pulse_500ps_high | 1.8514 | 2.0962 | 0.1584 | -1693.0 | TRANSISTOR_PAD_RECOVERS_MUCH_SOONER_THAN_NATIVE_KD_HOLD |
| short_pulse_1ns_high | 2.0571 | 0.5972 | 0.1761 | -1881.0 | TRANSISTOR_PAD_RECOVERS_MUCH_SOONER_THAN_NATIVE_KD_HOLD |
| short_pulse_2ns_high | 2.3293 | 0.6944 | 0.2635 | -2065.7 | TRANSISTOR_PAD_RECOVERS_MUCH_SOONER_THAN_NATIVE_KD_HOLD |

## Interpretation

- The transistor pad does **not** show the same approximately 2 ns native-IBIS Kd hold in the cleanly comparable 1 ns and 2 ns short-high cases. Its post-reverse pad return is much earlier.
- The 500 ps transistor case is only weakly comparable because the post-reverse pulse is small/inverted; the plot makes this visible instead of hiding it in one number.
- This does not prove the transistor netlist is the sole truth, because the long-pulse native-IBIS-vs-transistor pad gap remains large. It does say the native-IBIS Kd hold should be treated as a playback-model behavior unless we can reconcile the transistor/reference setup.
- Product implication stays conservative: ship/report the directional+residual model as the best current experimental candidate, keep Kd recovery variants diagnostic, and do not implement the failed simple command-age law.

## Outputs

- `pad_recovery_timing.csv`
- `plots/pad_recovery_timing_vs_width.png`
- `plots/<case>_pad_recovery_timing.png`
