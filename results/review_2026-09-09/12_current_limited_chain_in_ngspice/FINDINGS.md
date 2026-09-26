# The current-limited chain built in ngspice, scored on the pad

*2026-09-10*  ·  tools: `scripts/gate_chain_prototype.py`, `scripts/input_threshold_check.py`  ·  per-build
`<variant>/<build>/chain.png` and `sweep.csv`

The recipe from `../current_limited_stages_2026-09-10/` §5, implemented in the
model: the T-line command and the RC gate are replaced by K identical
current-limited stages (B-source current into a capacitor, four numbers), driven
by a mid-supply comparator on the input pin; GUP is the last stage; GDN = 1 − GUP
(one inverter drives both halves) or a second chain (io_buf); the Ku/Kd maps sit
on the last stage. Builds are named `<gate source>_<maps>`:

* gate source `real` — stages fitted to the transistor's own gate step response
  (what the model could know if it saw the transistor); `ibis` — stages fitted
  so that prior(chain) reproduces the tables' full-swing Ku(t) (file only).
* maps `silicon` — the transistor's Ku/Kd against its gate; `prior` — the
  MOSFET-shaped prior; `ibis` — re-derived from the tables against the new gate.

Peak error (%) and lag (ps) of the stressed pad versus the transistor, per
matrix width; "gate" = the model's / the real gate maximum.

## ex2 (C_comp 1.7 pF, K = 3 from the rms plateau)

| build | d975 | d895 | d858 | d830 | d810 | lag (ps) | gate at d810 | full-swing pad rms |
|---|---:|---:|---:|---:|---:|---|---|---:|
| shipped | +3.7 | +13.3 | +26.4 | +45.8 | +73.7 | 149 … 300 | 0.91 / 0.76 | 15 mV |
| **real gate, silicon maps** | **−2.6** | **−5.1** | **−7.8** | **−9.7** | **−5.4** | **58 … 71** | 0.75 / 0.76 | 27 mV |
| real gate, IBIS-implied maps | −11.0 | −15.6 | −18.4 | −15.6 | −14.9 | 36 … 55 | 0.75 / 0.76 | 15 mV |
| real gate, prior maps ¹ | −8.5 | −8.2 | −4.5 | +1.6 | +11.9 | 70 … 125 | 0.77 / 0.76 | 26 mV |
| **file only: IBIS gate, prior maps, x_lin fixed 0.45** | −9.5 | −15.1 | −18.4 | −22.6 | −27.6 | −60 … +33 | 0.68 / 0.76 | 15 mV |
| file only, same, input comparator at 1.4 V ¹ | −8.0 | −9.6 | −7.8 | −4.5 | +1.7 | 33 … 40 | 0.75 / 0.76 | 17 mV |
| file only, universal prior (0.5, 0.7), x_lin free ¹ | +2.3 | +8.3 | +16.5 | +27.4 | +42.4 | 121 … 243 | 0.84 / 0.76 | 14 mV |
| file only, x_lin free (degenerate fit, x_lin 0.02) ¹ | −48 | −79 | −98 | −98 | −97 | — | 0.49 / 0.76 | 22 mV |

¹ built before the chain input was moved from NINX (1.4 V) to the mid-supply
comparator; on ex2 that is an 8 ps wider pulse at the chain input.

* **The chain reproduces ex2's stressed pad from three identical stages and
  four numbers** fitted at full swing: −3…−10 % where the shipped model is
  +4…+74 %, lag 60–70 ps where it was 150–300. The gate maximum is within 0.04
  at every width.
* **The map matters even on ex2**: the same chain with the IBIS-implied maps
  is −11…−18 %.
* **The file-only route works but is sensitive**: −10…−28 % with the device's
  own prior and the resistive fraction fixed at 0.45; with 8 ps more pulse at
  its input it was −8…+2 %. A free fit of the resistive fraction is degenerate
  (x_lin → 0.02, the pulse swallowed); the universal prior (vt 0.5, alpha 0.7)
  over-drives. In this regime the pad peak moves ~4 % per 0.01 of gate maximum
  and ~5 % per 8 ps of pulse width, so the recipe's inputs must be that precise.

## inv_chain (C_comp 0.6 pF)

| build | d135 | d119 | d111 | d106 | d104 | lag (ps) | gate d111 / d104 |
|---|---:|---:|---:|---:|---:|---|---|
| shipped (input comparator 1.4 V) | −8.0 | −7.6 | −1.8 | +11.0 | +31.1 | −4 … 41 | 0.95/0.97, 0.93/0.88 |
| shipped, comparator at 0.9 V | +1.7 | +8.4 | +18.2 | +36.7 | +65.9 | 16 … 65 | — |
| real gate, silicon maps, K = 7 | +2.3 | +3.8 | −4.7 | −94.6 | −100 | 14 … 20, then collapse | 0.87/0.97, 0.22/0.88 |
| real gate, silicon maps, K = 9 | +2.7 | +8.0 | +16.5 | +26.5 | +51.1 | 21 … 53 | 0.97/0.97, 0.94/0.88 |
| file only, prior maps, K = 7, x_lin free (0.13) | −5.9 | −4.8 | −6.8 | −84.6 | −99.4 | −6 … 7, then collapse | 0.94/0.97, 0.40/0.88 |
| file only, prior maps, K = 7, x_lin 0.45 | −13.4 | −82 | −100 | −100 | −100 | collapse | 0.00/0.97 |

* **A finding about the shipped model first.** The inv_chain IBIS file declares
  Vinl 0.8 V / Vinh 2.0 V on a 1.8 V part, so the converter's digital input
  switches at 1.4 V and every 50 ps-edge pulse reaches the command layer 29 ps
  narrower than the transistor's first inverter sees it. With the comparator at
  mid-supply and nothing else changed, the shipped model's stressed error
  doubles (+31 → +66 % at 104 ps). **Two errors have been cancelling on
  inv_chain**: a pulse cut short at the input and a command layer that
  over-drives. Every inv_chain result in this project carries the first one.
  ex2 (3.3 V, 1.4 vs 1.65 V) moves by 1 %. `input_threshold_check_2026-09-10.txt`.
* **The chain is on a cliff on inv_chain.** Seven or nine identical stages
  reproduce the gate maximum to 0.03 at the widths where they pass the pulse,
  but K = 7 swallows the two deepest widths (the per-stage residual of
  `../current_limited_stages_2026-09-10/` §2 compounding), and K = 9, which
  passes them, returns ~10 ps too slowly and the pad is +17…+51 % there — the
  pad reacts to a few ps of extra gate time at these widths. The truth sits
  between K = 7 and 9, and full swing cannot place it. This is the drive law
  under a partial input, the one thing the full-swing fit cannot see; one
  stressed observation (the width at which the real chain still passes the
  pulse) would pin it.

## io_buf (declared C_comp; two chains: K = 1 for the PMOS gate ramp, K_d = 3 for the NMOS path)

| build | d2354 | d2090 | d1853 | d1666 | d1505 | lag (ps) | gate d1505 |
|---|---:|---:|---:|---:|---:|---|---|
| shipped | +2.1 | +1.6 | −1.8 | −1.3 | −3.5 | 63 … 69 | 0.40 / 0.67 |
| real gates, silicon maps | −5.8 | −8.4 | −11.8 | −18.6 | −23.0 | −19 … −56 | 0.63 / 0.67 |
| real gates, prior maps | −4.7 | −5.2 | −9.0 | −17.3 | −29.2 | −35 … −136 | 0.63 / 0.67 |
| file only, prior maps | −2.4 | −2.8 | −6.7 | −15.8 | −29.4 | −9 … −133 | 0.62 / 0.67 |

The chains put io_buf's gates where the transistor has them (0.63 vs 0.67 at
the deepest width; the shipped RC gate gives 0.40) and the +1.8 ns bump is in
the right place, yet the pad peak is 6–29 % low. Two reasons, both visible in
`io_buf/*/chain.png`: near threshold the map is steep in relative terms, so a
gate 0.04 low is a Ku 25 % low; and io_buf lives in the residual regime, where
the pull-down residual (FRAC, the depth rule of `../residual_depth_rule_2026-09-09/`)
sets the pad after the reversal — that machinery still keys on the old
command nodes and was not re-derived here. io_buf needs the chain *and* the
depth-scaled residual; neither alone.

## Where this leaves the direction

* Proven end to end on ex2: physics prior → chain → pad, file-only, within
  −10…−28 % where the shipped model is +4…+74 %, and within −3…−10 % when the
  gate is known. The structure is right; the residual is sensitivity to the
  prior's top end and to ~10 ps of input timing.
* inv_chain exposes the one quantity full swing cannot give — the drive law
  under a partial input — through a pulse-swallowing cliff inside the stressed
  range. The fix is not more fitting at full swing; it is one stressed
  characterisation point, or a better stage law near the input rail.
* io_buf needs the residual regime re-attached to the chain.
* The Vinh/Vinl threshold on inv_chain is a converter-level defect that has
  been masking half of its stressed error; clamp thresholds to the supply.
