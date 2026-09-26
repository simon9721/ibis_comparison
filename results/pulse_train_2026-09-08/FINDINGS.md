# Does the timing error accumulate over a pulse train?

*2026-09-08*

Every stressed case in this project is one pulse from a settled state. If the
defect is state carry-over, a train where the pad never settles should show the
error growing pulse by pulse. Eight pulses at 50% duty, three base buffers,
transistor / native / ours, one stressed width each (the ~57–71% depth cases)
and a 5 ns control train. Per pulse: best-fit lag of each model onto the
transistor over that pulse's window, and the peak error.

Figure: `pulse_train.png`. Data: `per_pulse.csv`.

---

## 1. It does not accumulate. It re-settles.

| | pulse 1 | pulse 2 | pulse 3 | pulses 4–8 |
|---|---|---|---|---|
| io_buf ours, lag | +55 ps | +88 | +91 | **+90 flat** |
| io_buf ours, peak err | +15 mV | +2 | −2 | −2 |
| inv_chain ours, lag | +22 | +27 | +29 | **+32 flat** |
| ex2 ours, lag | −42 | +152 | +129 | **+125 flat** |
| ex2 ours, peak err | +250 mV | −67 | −100 | **−107 flat** |

On every buffer the error moves from its single-pulse value to a **new plateau
within 3–4 pulses** and then stays there. Nothing grows without bound. The
"accumulating" shift seen in single-pulse records is the within-event behaviour
(`bump-is-the-timing-marker`, `timing-shift-splits-in-two`), not a run-to-run
drift.

Controls (5 ns, 50% duty) are flat to the picosecond on all three buffers:
io_buf +32 / +34 ps, inv_chain +7 / +12, ex2 −10 / −8 (native / ours).

## 2. The transistor itself carries state across pulses — and the sign of our error flips

The reference's own peak changes along the train because at 50% duty the pad
does not return to zero before the next pulse:

| | pulse 1 | pulse 2 | pulse 3+ |
|---|---:|---:|---:|
| io_buf transistor peak | 0.847 V | 0.861 | 0.864 |
| ex2 transistor peak | **1.085** | 1.406 | 1.444 |
| inv_chain transistor peak | (0.002 — see caveat) | 1.028 | 1.304 |

On ex2 the device nearly reaches full swing from the second pulse on. Our model
does the same, but from a different starting error: **+250 mV too tall on pulse 1,
then −107 mV too low from pulse 3**. The single-pulse "ours is 71% too tall"
defect (`cross_device_stress_2026-09-08`) reverses sign the moment pulses repeat.
A correction fitted to the isolated pulse would make a train worse. Native shows
the identical pattern (+247 → −114).

## 3. io_buf native breaks on a stressed train

| io_buf stressed | pulse 1 | 2 | 3 | 4 | 5–8 |
|---|---:|---:|---:|---:|---:|
| native lag | −10 ps | −199 | −127 | −309 | **−327 (bound)** |
| native peak err | −109 mV | +517 | +674 | +748 | **+750** |
| ours lag | +55 | +88 | +91 | +91 | +90 |
| ours peak err | +15 | +2 | −2 | −3 | −2 |

Native's pad goes to essentially full swing (0.864 + 0.750 ≈ 1.6 V against the
transistor's 0.864) from the second pulse and never truncates again. Its
single-waveform-per-edge replay appears unable to re-enter a transition it has
not finished. Ours is stable to within 3 mV and 90 ps. This is the one place in
the study where ours is not just better than native but native is unusable.

It did not happen on inv_chain or ex2, where native tracks ours within 10–20 ps
throughout — so it is an io_buf-specific interaction (the slow 1.13 ns gate and
the 1.8 ns pull-down turn-on against a 1.8 ns period), not a general native
failure on trains.

## What this settles

* **The pedestal and the peak error are per-event quantities**, set by the state
  at the start of each event. They do not compound. A train changes the starting
  state and therefore the error's plateau — including its sign — but the plateau
  is reached in 3–4 pulses.
* Validation on isolated pulses overstates the stressed-peak defect for repetitive
  traffic and understates a different one (ours too low by ~7% on ex2 trains).
  Both need to be in the test set.
* Native's collapse on the io_buf train is a hard failure worth its own report to
  whoever owns that model path.

## Caveats

* One width per buffer, one duty cycle. The sign flip on ex2 is measured at 858 ps
  / 50% only.
* inv_chain's output lags its input by ~270 ps against a 222 ps pulse window, so
  per-pulse attribution is off by one pulse there (its "pulse 1" peak reads
  0.002 V). The plateau conclusion is unaffected; the per-pulse numbers are not
  to be read literally for inv_chain.
* Ours = `InputDrivenTwoStateGateDelayCommandFull` (the shipped build), no
  corrections applied.
