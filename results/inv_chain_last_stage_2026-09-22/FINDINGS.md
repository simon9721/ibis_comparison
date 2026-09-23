# Would a faster final stage narrow inv_chain's gate? - findings

*2026-09-22, with the fitted version and the verdict added 09-23* · scripts
`inv_chain_last_stage_probe.py`, `gate_chain_prototype.py --fit-last-sdn`

## Why

inv_chain's modelled gate reaches the right height, peaks ~45 ps late and stays up 10-20 ps
too long; that surplus charge was its 26 % pad overshoot. The chain's one discharge knob
(`--dn-ratio`) bought 2-6 points. The final stage is the one that drives the output gate and
sets its fall, so the suspicion was that it should not be identical to the others.

## The probe: scale only the last stage's discharge, no refitting

| last-stage s_dn | worst peak | gate area excess, 135/119/111/106/104 ps | full swing vs transistor |
|---:|---:|---|---:|
| x1 (as built) | 25.8 % | +7 / +15 / +22 / +19 / -6 % | 54.0 mV |
| x1.5 | 21.9 % | -0 / +6 / +12 / +8 / -14 % | 46.2 mV |
| x2 | 19.6 % | -4 / +2 / +7 / +3 / -18 % | 42.5 mV |
| x3 | **16.6 %** | -8 / -3 / +1 / -3 / -22 % | **39.4 mV** |

A faster final stage drives the gate-area excess to about zero and improves the stressed peak
*and* the full swing - not a trade, which is what made the identical-stage constraint look
wrong.

## The fitted version: the fit declines it

`--last-sdn R` / `--fit-last-sdn` make the scale a real parameter (one number, not four), with
`s_dn` and `x_lin` refitted at each candidate so the scale cannot absorb a worse shared fit.
**The fit chose x1**, with a Ku-domain rms of 0.0069 at every candidate: the full-swing Ku(t),
the only file-only target, cannot see what the stressed pad shows. The build reproduces the
baseline exactly (25.8 %, 54.0 mV).

So the last stage's discharge is another parameter the full swing does not pin, and that only
a stressed observation could select - like the stage threshold and the stage count before it.

## And it was not the cause

Step 8 of the stage-count study chooses the curve shape alongside K from the same one pad run
and takes inv_chain from 34.2 % to **5.1 %**, with the gate rolling off across widths as the
transistor's does, and a better full swing (35.8 mV). That is better than this probe's best
(16.6 %) and better than the track-1 build with its measured C_comp and measured shape.

The gate staying up too long was the **symptom of a wrong (map, gate) pairing**, not of a
discharge that is too slow: the IBIS tables pin only the product Ku(t), and with the universal
shape the implied gate was square where the real one rolls off. A faster final stage
compensates for that; the right shape removes it. The numbers above stand as a measurement of
the coupling, not as the fix.
