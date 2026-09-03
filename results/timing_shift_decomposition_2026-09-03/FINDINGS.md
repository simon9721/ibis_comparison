# The timing shift: how much is stress, and how much was always there

"Defect B" was called stress-specific on the strength of the **native**
comparison — the gate-state build sits ~9 ps from native on a clean full-swing
edge but ~75-125 ps from it under stress. Native has since been shown to be an
unreliable yardstick under stress: on some cases it misses the event entirely,
and its response is device-dependent (tracking on io_buf, saturating on ex2 and
inv_chain).

So the question is re-asked against the **transistor**, which is ground truth and
does not degrade. Measured across the depth family, where `depth85-91` is
essentially a full transition and lower depths are progressively more stressed.
Timing at 50% of each case's own transistor excursion.

## 1. Almost all of the shift is already there at full swing

pybis minus transistor, per device and direction:

| device / direction | most stressed | near-full-swing | change | already present |
|---|---:|---:|---:|---:|
| ex2 short_high | −27.9 ps | −26.4 ps | +1.5 | **95%** |
| ex2 short_low | −56.4 ps | −43.6 ps | +12.8 | **77%** |
| inv_chain short_high | +11.3 ps | +11.6 ps | +0.3 | **103%** |
| inv_chain short_low | −25.4 ps | −25.3 ps | +0.1 | **100%** |
| io_buf short_low | +34.3 ps | +34.8 ps | +0.5 | **101%** |
| io_buf short_high | +28.5 ps | +72.4 ps | +43.9 | 39% |

**On five of six, 77-103% of the shift already exists at near-full swing.**
Stress adds essentially nothing. The shift is a fixed per-device, per-direction
offset that is present on a clean transition and simply carried into the
stressed cases.

That directly contradicts "defect B is stress-specific". It is not — measured
against the transistor it is a full-swing property. The stress-specificity was an
artifact of comparing against native, whose *own* error grows sharply under
stress, widening the model-to-native gap while the model-to-transistor distance
stayed flat.

`io_buf short_high` is the one exception (39%), and it rests on two points.

## 2. The trends — one device-independent, one strongly device-dependent

**Device-independent:** the shift is **flat in stress depth**. Five of six change
by under 13 ps across the whole depth range, four of them by under 2 ps. Whatever
causes it does not care how truncated the pulse is.

**Device-dependent:** the *value* of that constant, including its **sign**:

| device / direction | pybis vs transistor |
|---|---|
| ex2 short_high | **early**, −26 to −28 ps |
| ex2 short_low | **early**, −44 to −56 ps |
| inv_chain short_high | **late**, +11 ps |
| inv_chain short_low | **early**, −25 ps |
| io_buf short_high | **late**, +28 to +72 ps |
| io_buf short_low | **late**, +31 to +35 ps |

The range spans −56 to +72 ps and the sign flips both between devices and between
directions on the same device (inv_chain is late on short_high, early on
short_low). So there is no universal "pybis is late" — that was an io_buf
generalisation. io_buf happens to be the one device that is late in both
directions, and it is the device the defect was characterised on.

Native shows the same device-dependence: −37 ps on ex2 short_high, +4.5 on ex2
short_low, −6.3 on inv_chain short_high, +20.5 on inv_chain short_low, +57 on
io_buf short_low.

## 3. What this changes

- **The timing shift is not a stress defect.** It is a per-device, per-direction
  constant offset visible on clean transitions, which stress does not amplify.
  Chasing it in the command layer's stress handling was chasing the wrong place —
  consistent with `delay_cmd` failing to fix it (0 of 19).
- **It is not uniformly a lag.** Half the device/direction combinations are
  *early*. Any explanation has to produce a signed, device-dependent offset, not a
  systematic delay.
- **The full-swing measurement is the right place to study it**, which is cheaper
  and cleaner than stressed benches, and where the golden-waveform test already
  showed +4 to +8 ps of alignment shift on all three buffers.

## Caveats

- Two points per device/direction in several cells; ex2 short_low and io_buf
  short_low have three.
- `depth91` is near-full but not identical to a true full-swing bench.
- io_buf short_high dissents (39%) and needs more depths before it is dismissed
  or accepted.
- Native's column has gaps where its response was too weak to produce a crossing.

## Files

- `timing_shift_vs_depth.png`
- `scripts/timing_shift_decomposition.py`
