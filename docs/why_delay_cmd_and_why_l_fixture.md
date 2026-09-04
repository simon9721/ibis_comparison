# Two mechanisms, traced end to end

*2026-09-04*

Both of these were known as observations — delay_cmd removes the offset, a series
inductor corrupts Ku — with no chain of events behind them. This is the chain, in
each case measured rather than argued.

---

## 1. Why delay_cmd removes the offset, and why it cannot fix the timing

### The chain, node by node

The command layer is a series: `GUPCMD → GUPTARGET → GUP → Ku → I_pu → pad`.
Measured on io_buf's five short-high stress cases, averaged over the tail 1.0–1.7 ns
after the reversal (`results/settled_offset_diagnosis_2026-08-27/command_probe/`):

| case | GUPCMD | GUP | Ku | pad |
|---|---:|---:|---:|---:|
| swing 50%, 1634 ps | **+0.0237** | +0.0237 | +0.0280 | **51.6 mV** |
| swing 60%, 1792 ps | **+0.0360** | +0.0361 | +0.0416 | **76.3 mV** |
| swing 70%, 1989 ps | −0.0056 | +0.0000 | +0.0018 | 4.5 mV |
| swing 80%, 2226 ps | −0.0106 | +0.0000 | +0.0018 | 4.9 mV |
| swing 90%, 2484 ps | **+0.0259** | +0.0259 | +0.0321 | **60.6 mV** |

Read across a row and the chain is one-to-one:

1. **A truncated pulse strands charge on GUPCMD.** It is a capacitor with a 1e15 Ω
   leak, given a fixed packet of charge per input edge. When the reverse edge
   arrives before the on-packet has finished being delivered, the on and off
   packets do not cancel and a residue is left.
2. **GUP copies it exactly** — 0.0237 → 0.0237. The gate state is a first-order
   lag on the command, so a held command becomes a held gate state.
3. **Ku scales it by ~1.18** — 0.0237 → 0.0280.
4. **The pad scales that by ~1850 mV per unit Ku** — 0.0280 → 51.6 mV. A held Ku
   is a held pull-up current, and into 50 Ω that is a held voltage.

There is no DC path anywhere in that chain, so the residue persists for ~6 ns.

### Why it only shows on 90/60/50

Look at the 70% and 80% rows: GUPCMD is **negative**. `GUPTARGET` clamps with
`min(max(x, 0), 1)`, so a negative residue is removed before it reaches GUP —
GUP is 0.0000 and the pad shows 4.5 mV, which is the transistor's own level.

The sign of the stranded charge is set by where the reverse edge lands relative to
the packet, so it flips from case to case. **The clamp silently rescues half of
them.** That is why the defect looked intermittent, and why tuning the packet size
appeared to work on some cases and not others.

### What delay_cmd changes

One line of the generated subcircuit:

```
gate_state   CGUPCMD GUPCMD 0 {gate_c} ic=0            a capacitor
             RGUPCMD GUPCMD 0 1e15                     across 1e15 ohm
             BGUPCMDON I = -{gate_c}*V(PUONP)/edge_delay    a packet per edge
delay_cmd    BGUPCMD GUPCMD 0 V = V(PUCMDLVL)          driven by the input level
```

delay_cmd makes the command a **function of the present input level** instead of
an integral of past edges. After the reversal the input is back where it started,
so the command is back where it started — exactly, not asymptotically. Measured on
the tail: gate_state **−0.144**, delay_cmd **+0.00000**. Nothing enters step 1, so
nothing propagates down the chain.

### Why the timing is untouched

Because the edge timing is set by a different part of the same chain. Measured on
one truncated pulse, 50% rise of each node in both builds:

| node | gate_state | delay_cmd | difference |
|---|---:|---:|---:|
| GUPCMD | 5.9980 ns | 5.9935 ns | −4.5 ps |
| GUP | 6.5030 | 6.4948 | −8.2 ps |
| Ku | 6.7157 | 6.7020 | −13.6 ps |
| pad | 6.7376 | 6.7302 | −7.5 ps |

Single digits to ~14 ps, against a model-to-transistor shift of 27–46 ps. The
transition is governed by the gate lag τ and the Ku(t) map, and delay_cmd changes
**neither** — it changes only how the command that drives them is generated. So:

> delay_cmd changes *what is left behind*, not *how fast the edge moves*.

The offset is a level held after the event; the timing shift is a property of the
trajectory during it. They are different parts of the chain, which is why fixing
one leaves the other exactly where it was — and why delay_cmd improved timing on
**0 of 19** stress cases.

---

## 2. Why a series inductor in the fixture corrupts Ku

### The solve has a term that is not the device

At every instant the two-fixture solve balances

```
Ku·I_pu(V) + Kd·I_pd(V)  =  i_clamps(V) + i_fixture − C_comp·dV/dt
```

The left side is the devices. The right side includes **`C_comp·dV/dt`**, which is
displacement current through the die capacitance and depends only on how fast the
pad is moving. Anything that makes the pad move faster inflates that term, and the
solve has nowhere to put it except into Ku and Kd.

### A series inductor makes the pad move faster, twice

Measured on io_buf short-high 70%, against the R-only baseline
(`scripts/build_deck_figures.py` reuses these runs):

| fixture | \|dV/dt\| p95 | cond(M) p95 | \|Ku error\| p95 | worst \|Ku error\| |
|---|---:|---:|---:|---:|
| baseline, R only | 2.3 V/ns | 2.3 | 0.0000 | 0.000 |
| C_fix 2 pF | 1.9 | 2.3 | 0.0347 | 0.204 |
| L_fix 0.5 nH | 2.3 | 2.3 | 0.0075 | **5.512** |
| L_fix 2 nH | 2.1 | 2.3 | 0.0284 | **7.875** |
| L 2 nH + C 2 pF | **9.5** | 2.3 | **0.2551** | 5.223 |

Two distinct failure modes:

* **L alone — a transient spike.** Typical error is small (p95 0.0075–0.028) but
  the worst case is enormous. The inductor opposes the sudden current reversal, so
  at the reversal the pad gets a voltage spike: local `|dV/dt|` reaches **17.5 V/ns**
  against a 2.3 V/ns baseline. The worst Ku error lands at **+61 ps after the
  reverse edge** — exactly there.
* **L + C — sustained ringing.** The inductor and the capacitance form a tank, and
  the pad rings for nanoseconds. `|dV/dt|` p95 is **4× the baseline**, so the error
  is not a spike but a sustained 0.26.

Within a case, the error tracks the slew: `corr(|dV/dt|, |Ku error|)` is **+0.43**
for L alone and **+0.62** for L+C.

### It is not an ill-conditioned solve

`cond(M)` is **2.3 in every fixture**, including the worst ones. The 2×2 system is
perfectly well behaved. The problem is the forcing term, not the matrix:

> Right after the reversal both devices are nearly off, so `Ku·I_pu + Kd·I_pd` is
> small. At that same instant the inductor is driving a large `C_comp·dV/dt` onto
> the right-hand side. Balancing a large number against a small coefficient forces
> Ku and Kd to extreme values — 7.9 at the worst point.

### The practical rule

Characterise into a resistive fixture. A shunt capacitor is tolerable (it *slows*
the pad, p95 dV/dt 1.9 V/ns, and costs 0.01–0.03 in Ku). **Series inductance is
not**, because it injects displacement current the solve must charge to the
devices — and the damage is worst exactly at the reversal, which is the moment the
stress cases are about.
