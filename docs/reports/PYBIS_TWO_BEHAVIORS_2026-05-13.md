# Pybis Two-Behavior Summary

Date: 2026-05-13

Workspace: `C:\Users\simom\Desktop\IBIS_Comparison`

Source experiment bundle:

- `results/pybis_spike_trend_sweep_2026-05-12/`

This note documents the two repeatable pybis behaviors found in the targeted
stressed-channel sweep.  Both behaviors are visible in transient simulation
data.  They are not eye-diagram plotting artifacts.

## Short Version

| Behavior | Simple name | Main trigger | Main symptom | Current interpretation |
|---|---|---|---|---|
| 1 | Positive rise precursor spike | Previous high pulse, exactly 1 UI low gap, then a new rising edge | Receiver jumps high in pybis while pybis source-side `tx_out` is still near low | Channel memory/reflection timing interacts with pybis edge-state behavior |
| 2 | Negative 2 UI high-run fall-window mismatch | Exactly 2 UI high run before the next falling input edge | In the receiver window after that input fall, pybis is much lower than refspice, then catches up | Run-length/settling mismatch, not a positive overshoot |

The important practical point is that these two behaviors are different.  The
first is a positive receiver excursion after a new rise.  The second is a
negative pybis-vs-refspice mismatch after a 2 UI high burst.

## Common Test Context

The targeted sweep used short patterns of this form:

```text
0000 + 1*pre_high + 0*low_gap + 1*post_high + 0000
```

Main fixed-channel setup:

- UI: 2 ns
- Input transition time: 200 ps
- Channel: 30 cm coarse10 RLGC
- Loss scale: 5
- Termination: 50 ohm to ground
- Reference comparison: Xyce pybis vs Xyce transistor-level `io_buf.sp`
- Simulator cross-check: corrected ngspice pybis vs Xyce pybis

The scripts used for this study are:

- `scripts/run_pybis_spike_trend_sweep.py`
- `scripts/run_ngspice_pybis_spike_validation.py`

## Behavior 1: Positive Rise Precursor Spike

### Trigger Pattern

This behavior appears when the target rising edge follows exactly one UI of low
state after a previous high pulse:

```text
... 1...1  0  1...
          ^  ^
          |  target rising edge
          exactly 1 UI low gap
```

In sweep variables, the condition is:

- `low_gap = 1 UI`
- `pre_high >= 1 UI`
- `post_high` does not materially affect the early spike

The following high-run length does not matter much because the measurement
window is immediately after the target rise, before later bits can influence
the receiver.

### Observable Waveform Signature

The receiver voltage in the pybis run jumps high early, but the pybis
source-side waveform has not yet made a corresponding high transition.

Strongest fixed-channel example:

- Case family: `hist_h1_g1_p*`
- Pybis receiver `V(n10b)` peak in rise window: about `1.53 V`
- Refspice receiver `V(n10b)` peak in same window: about `0.91 V`
- Pybis source-side `V(tx_out)` max in same window: about `0.11 V`

That last point is important: this is not simply the new source high
propagating normally through the channel.  The receiver event occurs while the
pybis source-side node is still near low.

### Strength vs Low Gap

For the fixed 30 cm/loss5 stressed channel:

| Low gap before target rise | Cases | Min max `|pybis-ref|` | Mean max `|pybis-ref|` | Max max `|pybis-ref|` |
|---|---:|---:|---:|---:|
| 1 UI | 16 | 1.204 V | 1.296 V | 1.519 V |
| 2 UI | 16 | 0.109 V | 0.137 V | 0.163 V |
| 3 UI | 16 | 0.050 V | 0.058 V | 0.074 V |
| 4 UI | 16 | 0.048 V | 0.054 V | 0.063 V |

This is the clearest trend in the sweep.  One UI of low gap is the large-spike
condition.  Two UI or more mostly removes it.

### Strength vs Channel

For the strongest local history pattern, `1 UI high / 1 UI low / 3 UI high`:

| Channel length | Loss x1 | Loss x3 | Loss x5 |
|---:|---:|---:|---:|
| 10 cm | 0.193 V | 0.180 V | 0.168 V |
| 20 cm | 1.451 V | 1.417 V | 1.384 V |
| 30 cm | 1.630 V | 1.573 V | 1.519 V |

Length is the dominant control.  The 10 cm channel does not show the same
positive spike.  The 20 cm and 30 cm channels do.  Higher loss dampens the
spike slightly, but does not remove it once the channel timing lines up with
the one-UI gap.

### Simulator Status

This behavior is present in both corrected pybis simulator flows:

- Xyce pybis shows the spike.
- Corrected ngspice pybis shows the same trend.
- Across all 64 fixed-channel histories, corrected ngspice pybis vs Xyce pybis
  has mean max rise-window difference `45.9 mV`, worst `136.4 mV`.

The pybis-vs-refspice spike is much larger than the ngspice-vs-Xyce pybis
difference, so this is not primarily a simulator mismatch.

### Current Interpretation

The best current explanation is:

1. The previous high pulse leaves energy in the channel.
2. Exactly one UI of low gap is not enough time for that energy to settle away.
3. The channel delay/reflection timing places that stored energy at the receiver
   just after the next target rising edge.
4. The pybis driver's internal edge-state behavior does not match the
   transistor-level reference in this situation.
5. The result is a positive receiver precursor spike before the pybis source
   waveform has made a normal high transition.

This is why longer channels are worse and why waiting two or more UIs before
the next rise mostly removes the effect.

## Behavior 2: Negative 2 UI High-Run Fall-Window Mismatch

### Trigger Pattern

This behavior appears when the high run before the next falling input edge is
exactly 2 UI long:

```text
... 0...0  1  1  0...
              ^  ^
              |  target falling input edge
              exactly 2 UI high run before fall
```

In sweep variables, the condition is:

- `post_high = 2 UI`
- `pre_high` and `low_gap` are less important than `post_high`

The metric is measured in the receiver window after the target falling input
edge.  Because the channel is delayed and dispersive, this window is not
necessarily a clean receiver fall.  It is the receiver response window tied to
that input fall time.

### Observable Waveform Signature

In the affected window, pybis receiver voltage is much lower than refspice,
then it catches up later.

This is the opposite sign from the positive rise spike:

- Rise spike: `pybis - refspice` is strongly positive.
- 2 UI high-run fall-window mismatch: `pybis - refspice` is strongly negative.

So this should not be described as another overshoot.  It is better described
as an under-response, phase/settling mismatch, or missing delayed high energy
in the pybis receiver waveform.

### Strength vs High Run Length

For the fixed 30 cm/loss5 stressed channel:

| High run before target fall | Cases | Min max `|pybis-ref|` | Mean max `|pybis-ref|` | Max max `|pybis-ref|` |
|---|---:|---:|---:|---:|
| 1 UI | 16 | 0.234 V | 0.278 V | 0.335 V |
| 2 UI | 16 | 0.707 V | 0.739 V | 0.766 V |
| 3 UI | 16 | 0.055 V | 0.075 V | 0.108 V |
| 4 UI | 16 | 0.055 V | 0.062 V | 0.071 V |

The 2 UI high run is the clear worst case.  A 3 UI or 4 UI high run settles
back near the small-error regime.

### Simulator Status

Corrected ngspice pybis and Xyce pybis agree well for this behavior too:

- All 64 corrected ngspice fixed-channel cases completed.
- Mean max ngspice-vs-Xyce fall-window difference: `25.2 mV`
- Worst max ngspice-vs-Xyce fall-window difference: `57.9 mV`

The pybis-vs-refspice fall-window mismatch is around `0.7-0.77 V`, much larger
than the ngspice-vs-Xyce pybis difference.  So this also appears to be a shared
pybis-model behavior, not primarily a simulator artifact.

### Current Interpretation

The best current explanation is:

1. A 2 UI high burst puts the channel and driver state into a transitional
   state that is not fully like a short isolated pulse and not fully like a
   settled long high.
2. In the receiver window after the next input fall, refspice still shows a
   large delayed high response.
3. Pybis is lower in that same window, then catches up later.
4. The result is a strong negative `pybis - refspice` error.

This looks like a run-length-sensitive settling mismatch.  It is not the same
mechanism as the positive rise precursor spike, even though both are exposed by
the same stressed channel.

## How To Avoid Mixing The Two Up

| Question | Positive rise precursor spike | Negative 2 UI high-run mismatch |
|---|---|---|
| Which edge window? | After target rising input edge | After target falling input edge |
| Main bit-history trigger | Exactly 1 UI low gap before rise | Exactly 2 UI high run before fall |
| Error sign | Pybis above refspice | Pybis below refspice |
| Typical fixed-channel size | Up to about 1.52 V | Up to about 0.77 V |
| Strong channel dependence? | Yes, length/timing is critical | Seen clearly in same stressed channel; channel sweep not yet as broad |
| Best short name | Rise precursor spike | 2 UI high-run fall-window mismatch |

## Implication For Eye Diagrams

The eye tool should continue to fold the actual transient data physically.  It
should not compensate either behavior to make the eye look nicer.

These behaviors mean the transient waveform itself contains strong
history-dependent distortion:

- Behavior 1 can create large positive excursions around rising-edge windows.
- Behavior 2 can create missing/late high-level energy after a 2 UI burst.

If the eye looks strange because these events are present in the transient data,
the correct conclusion is that the model/setup produced a strange transient
response, not that the eye tool should hide it.

## Key Evidence Files

- `results/pybis_spike_trend_sweep_2026-05-12/spike_trend_summary.csv`
- `results/pybis_spike_trend_sweep_2026-05-12/ngspice_validation_fixed_channel_full.csv`
- `results/pybis_spike_trend_sweep_2026-05-12/plots/fixed_channel_spike_history_heatmap.png`
- `results/pybis_spike_trend_sweep_2026-05-12/plots/channel_spike_strength_heatmap.png`
- `results/pybis_spike_trend_sweep_2026-05-12/plots/representative_rise_spike_cases.png`
- `results/pybis_spike_trend_sweep_2026-05-12/plots/representative_fall_run_length_cases.png`
- `results/pybis_spike_trend_sweep_2026-05-12/plots/ngspice_xyce_pybis_fixed_channel_agreement_heatmap.png`
