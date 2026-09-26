# Prototyping the pad-indexed coefficient: four attempts, and what they show

*2026-09-04*

`native_waveform_count_2026-09-04` established that the stress pedestal is our
single time-indexed coefficient trajectory: forcing native onto one V-T waveform
gives it the same +75 ps error we have. This prototypes the fix.

Measured on io_buf short high 1792 ps, against the **transistor's own** Ku and Kd
from the two-fixture solve, over the outward leg. `best_lag` with the residual
after alignment, so a large residual flags a shape change rather than a delay.

| build | Ku lag | Ku rms | Kd lag | Kd rms |
|---|---:|---:|---:|---:|
| shipped — gate state, time-indexed | +80 | 0.02 | +191 | 0.05 |
| **native, two V-T tables** *(the target)* | **+15** | 0.02 | **+67** | 0.03 |
| 1. re-indexed by instantaneous pad voltage | +165 | 0.08 | −300 | **4.42** |
| 2. pure table replay, no gate state | +117 | 0.02 | +163 | 0.04 |
| 3. replay entered at the pad's voltage | −159 | 0.12 | −113 | 0.04 |
| **4. replay entered at the matching state** | **−43** | 0.04 | **+1** | 0.03 |

**Attempt 4 works.** Kd goes from +191 ps to **+1 ps** against the transistor —
better than native. Ku halves, +80 to −43. Residuals stay at 0.03–0.04, so the
shapes are preserved rather than traded away.

---

## What the manual actually says

The mechanism is documented, and it is narrower than "indexed by pad voltage"
(`primesim_continuum_elements.pdf`, ramp_rwf section):

> The PrimeSim Continuum solution selects two proper VT waveforms in a sampling
> method **according to the initial voltages of VT waveforms and V(out) before a
> buffer's transition**. […] Assuming at a current time point, the buffer is in
> low state (PU off, PD on) with **V(out)=0.1v**. If input is a rising edge […] it
> selects the two rising waveforms with initial voltages of 0v and 0.2v.

So it is an **entry condition**, evaluated once when a transition begins — not a
continuous index. That immediately explains attempt 1: re-indexing at every
instant destroys the trajectory's shape, which is why its Kd residual is 4.42,
i.e. the curve is no longer the same curve. Ku is simply not single-valued in the
pad voltage — on the way out the pad passes 0.87 V having just *risen* there,
while the falling table's entry at 0.87 V was recorded on a pad *descending* from
1.73 V. Same voltage, different state.

## Attempt 3 is the right shape of fix, mis-calibrated

Implementing the manual's rule directly: at the reversal the pad is at 0.668 V,
which is **0.274 ns into the recorded falling transition**, so play the trajectory
from there rather than from its start.

That moves the coefficient from **+117 ps late (entry at 0) to −159 ps early**.
It crosses the target. The entry-condition idea is therefore the right correction
in kind and direction; it is over-applied.

**Why it over-shoots.** The recorded waveform's pad voltage is the pad *into the
characterisation fixture* (50 Ω to a rail). Our bench is 50 Ω + 2 pF to ground. At
the same internal switching state the two pads sit at different voltages, so
matching them raw advances the entry too far. Native does not have this problem in
the same way: it holds both waveforms and the actual load, so it can place the
entry against the load it is actually driving.

Interpolating between the two brackets puts the right entry at roughly 0.12 ns
rather than 0.274 — but arriving at that by interpolation would be fitting the
answer, not deriving it, so it is not done here.

## Attempt 4: enter at the matching *state*, not the matching voltage

Attempt 3 matched the pad voltage against the recorded waveform's pad voltage,
and over-advanced because the recording is the pad *into the characterisation
fixture* while our bench has a different load — the same internal state shows up
at a different voltage.

Matching on the **coefficient** instead is load-independent. At the reversal the
model's Ku is 0.478; the falling trajectory passes through 0.478 at **0.159 ns**
in, so enter there. (The pad-voltage rule said 0.274 ns — that is the
over-advance, measured.)

Physically it is the obvious statement: **we never got fully on, so we should not
have to turn fully off.** Start the turn-off from where we actually are.

## Where this leaves the fix

Reading the shipped subcircuit shows where this belongs, and it is more surgical
than expected. The coefficient is built in two parts:

```
BKUGATE_ON   KUGATE_ON  0 V = pwl(min(max(V(GUP),0),1), ...)   map: gate state -> Ku
BKUGATE_BASE KUGATE_BASE 0 V = (V(GUPTARGET) >= V(GUP)) ? V(KUGATE_ON) : V(KUGATE_OFF)
BKURES_R     KURES_R    0 V = pwl(min(max(V(HNX),0),6.0), ...)  residual, indexed by HNX
```

The **map** is already indexed by the gate state, so it handles a partial entry
correctly on its own — which is why the shipped model beats pure table replay
(+80 against +117). The **residual correction is indexed by `HNX`, the elapsed
time since the last input edge**, and that is the piece that assumes the
transition began from settled.

So the change is: index the residual by trajectory *position* rather than by the
clock. And it needs no latch and no per-edge reset — invert the recorded gate
trajectory once, offline, to get an equivalent-elapsed-time as a static function
of the gate state, and use that in place of `V(HNX)`:

```
HNX_eff = pwl(V(GUP), <inverse of the recorded GUP(t)>)
```

On a complete transition `HNX_eff` reproduces `HNX` exactly and nothing changes.
On a truncated one it enters partway, which is attempt 4's rule expressed without
any state to hold.

**Not yet built.** The rule is validated offline; the netlist change is the next
step.

## What is now ruled out for good

* The command layer's fitted transport delays and gate-state time constants
  (`delay_pedestal_test.py`) — scaled to 5% of nominal, most of the pedestal
  survives, and both responses are non-monotonic.
* A continuous pad-voltage index for the coefficient (attempt 1).
* Removing the gate state in favour of raw table replay (attempt 2) — worse on Ku
  than what ships, so the gate state is doing real work.

## Caveats

* One device, one case. Attempts 2 and 3 are offline reconstructions from the
  shipped solve, not SPICE runs, so they show what the coefficient would do, not
  what the pad would do once it feeds back through the output stage.
* `solve_k_params_output` returns its time column in **seconds** while every
  waveform in this study is in ns. The first version of attempt 2 interpolated ns
  against seconds and returned a saturated square wave; the numbers above are
  after that fix.
