# The timing shift accumulates on the way *out* — on two devices of three

*2026-09-04*

Every timing number in this study so far is **one crossing per case**, almost
always the 50% point. That cannot distinguish a model which is uniformly N ps
late from one which starts aligned and falls progressively further behind. This
measures the shift as a function of position through the event instead.

Method: crossing times at 10%, 15% … 90% of the **transistor's own** excursion,
model minus transistor, taken separately on the way *into* the event and on the
way *out* of it. A flat ladder is a fixed offset; a sloped one is accumulation.
Three devices, both directions, plus an unstressed full-swing control where one
exists — the control is what separates "our model does this" from "IBIS does
this".

`scripts/timing_shift_accumulation.py`, `ladder_output.txt`,
`ladder_summary.csv`, `timing_shift_ladder.png`.

---

## 1. The accumulation is on the way out, and it is device-dependent

Change across the outward ladder, in time order, ps:

| device / direction | control (full swing) | stressed range |
|---|---|---|
| io_buf short_high | native **+67**, cmd_clean **+69** | native +87…+113, cmd_clean +77…+96 |
| ex2 short_high | native **+93**, cmd_clean **+103** | native +54…+92, cmd_clean +67…+103 |
| inv_chain short_high | native **+1**, cmd_clean **+2** | native −2…−4, cmd_clean −1…+8 |
| inv_chain short_low | *(no control)* | native −4…−5, cmd_clean −2…−4 |

**io_buf and ex2 accumulate. inv_chain does not** — its ladder is flat to within
8 ps everywhere, stressed or not.

On the way *into* the event nothing accumulates on any device: io_buf's inward
ladder is flat or shrinking (+41 → +28 ps on the 1792 case), inv_chain's is flat
to 5 ps, ex2's is flat to 40 ps.

## 2. Where a control exists, native accumulates by the same amount

This is the load-bearing result.

* io_buf, full swing, no stress at all: native **+67 ps**, cmd_clean **+69 ps** —
  and they agree to 2–3 ps at *every* rung of the ladder.
* inv_chain, full swing: native **+1 ps**, cmd_clean **+2 ps**.
* ex2, full swing: native **+93 ps**, cmd_clean **+103 ps**.

Two independent IBIS implementations reading the same file drift away from the
transistor by the same amount, in the same direction, on a clean transition. The
accumulating component is therefore a property of the IBIS representation or of
the characterisation — not of pybis's output stage, and not of the command layer.

## 3. The stress pedestal is io_buf-specific, and it is signed

Distance between cmd_clean and native on the outward ladder:

| device | control | stressed |
|---|---:|---|
| io_buf short_high | +2 to +4 ps | **+83 to +99 ps (ours later)** |
| inv_chain short_high | +3 to +4 ps | **−31 to −41 ps (ours earlier)** |
| ex2 short_high | −9 to −20 ps | −12 to −23 ps (ours earlier) |

At full swing we are indistinguishable from native on io_buf and inv_chain, and
within 20 ps on ex2 — where, unlike io_buf, stress adds nothing on top. Under stress a gap opens — but it is **positive on io_buf and negative
on the other two**. There is no universal "our model is late under stress"; that
was an io_buf generalisation, the same way the amplitude "law" was.

## 4. A candidate mechanism, and it is cheap to test

Accumulation at full swing against the buffer's declared C_comp:

| device | declared C_comp | outward accumulation, full swing |
|---|---:|---:|
| inv_chain | 0.468 pF | **+1 / +2 ps** |
| io_buf | 1.2 pF | **+67 / +69 ps** |
| ex2 | 5.0 pF | **+93 / +103 ps** |

*(native / cmd_clean)* — monotonic in C_comp across all three, with the two
implementations within 2–10 ps of each other on every device.

**Confirmed causal, not merely correlated.** See
`../ccomp_accumulation_2026-09-04/`: holding the buffer fixed and changing only
the explicit C_comp reproduces the whole range in both directions — io_buf goes
+69 → +13 → −9 → −30 ps as C_comp is scaled 1.2 → 0.6 → 0.3 → 0 pF, and base8
goes +2 → +12 → +70 ps as it is scaled up to io_buf's and ex2's declared values.

The mechanism would be physical: C_comp is installed as a fixed **linear**
capacitor, while real die capacitance is bias-dependent. The way out of the event
is where the pad spends longest at intermediate voltages, which is exactly where a
constant cap and a junction cap diverge most. See the deck README on the declared
value never having been checked against the netlist.

## What could not be measured

**io_buf short_low and ex2 short_low** are not measurable with a crossing-time
metric. The model over-dips heavily there (pybis 1.116 V against the transistor's
0.697 V at 163 ps) and its recovery rings, so a level is crossed several times and
"the crossing" is not a well-defined feature. The script rejects a case when the
model's excursion differs from the transistor's by more than 30%, when the
crossing sequence is non-monotonic, or when the fitted shift exceeds the
reference's own transition span — but io_buf short_low defeats all three and its
outward numbers (~+900 ps) should be **disregarded**, not read as a large shift.
This is the same trap `native_stress_law` documented: on short_low the pad rises
to a plateau, dips, and recovers, and any metric has to be checked against the raw
trace before it is trusted.

## Caveats

* The controls are single benches, not families.
* ex2's control was built for this study
  (`scripts/ex2_full_swing_control.py`); its pulse falls at 11 ns, not the 15 ns
  the other two use, which the ladder has to be told or it measures the settled
  tail as a transition.
* ex2's usable stressed cases are 3 of 5; the two narrowest fail the excursion
  test.
* inv_chain short_high has only 2 of 5 cases with native usable — below about
  111 ps native's excursion diverges by more than 30%.
