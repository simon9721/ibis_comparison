# What the book tells us

An explainer of the ideas we took from Leventhal & Green, *Semiconductor
Modeling: For Simulating Signal, Power, and Electromagnetic Integrity*
(Springer, 2006) — written so it can be read without the book to hand.

Terse notes with chapter pointers live in `book_study_notes.md`. This document
explains the concepts and what each one changed for us.

---

## 1. How an IBIS model actually drives a pin

Worth stating first, because several later ideas only make sense against it.

An IBIS model is not a circuit. It is a set of measured tables:

- **I-V tables** — `[Pullup]`, `[Pulldown]`, `[POWER Clamp]`, `[GND Clamp]`.
  How much current the pin sources or sinks at a given voltage, in each fixed
  state.
- **V-T tables** — `[Rising Waveform]`, `[Falling Waveform]`. The voltage at the
  pin against time during an actual transition, recorded into a stated test
  fixture.
- **C_comp** — the die capacitance seen at the pin.

The book's Appendix E gives the canonical way a simulator uses these:

> "An IBIS output driver sends a voltage wave, provided by the model file's
> [Ramp] or V-T data lookup tables, down a network to an IBIS input receiver...
> The reflections at each IBIS Input/Output are calculated with the use of the
> model file's I-V data lookup tables."

So in the canonical architecture: **the V-T tables drive the wave, and the I-V
tables handle reflections.**

That is worth holding onto, because pybis does something different. It
reconstructs the wave from the I-V tables scaled by a time-varying coefficient
`Ku(t)`, derived from the V-T data. Both are defensible; they are simply not the
same architecture. When we measured a stubborn few-picosecond difference between
pybis and HSPICE's native IBIS that survived every other explanation, this
architectural difference is the remaining candidate.

---

## 2. Ku and Kd — the switching coefficients

IBIS describes a transition as the pullup and pulldown devices being scaled up
and down over time:

    I_pin(t)  =  Ku(t) · I_pullup(V)  +  Kd(t) · I_pulldown(V)
                 + clamps(V)  +  C_comp · dV/dt

`Ku` and `Kd` run from 0 (device off) to 1 (fully on). They are not in the IBIS
file — they are *solved for*. The V-T tables are recorded into **two different
fixtures**, which gives two equations at each instant, and those are solved for
the two unknowns `Ku` and `Kd`.

Two consequences we ran into:

- **`Ku` above 1 is not automatically an error.** It means the solve needed more
  than the full pullup to balance the equation at that instant. That happens when
  the displacement current `C_comp · dV/dt` is large compared with what the device
  can source. On ex2 (C_comp 5 pF, driven fast) the displacement current is about
  82 mA against a ~51 mA drive, so `max|Ku|` sits near 1.3 legitimately. inv_chain,
  with C_comp of 0.468 pF, sits at 1.03. A fixed cap on `max|Ku|` therefore
  penalises buffers for having large, realistic die capacitance.
- **The two fixtures must not be degenerate.** An open-drain has no pullup, so
  the "rising waveform into a fixture that pulls to ground" is flat and carries no
  information — the solve has nothing to work with. This is why our open-drain
  conversion needed the pull-up fixture alone.

---

## 3. C_comp, and the double-counting trap

This is the one the book is most emphatic about (§11.8.1):

> "It is important to know that **the effect of Ccomp on dV/dt or V-T is already
> included in the dV/dt and V-T data.** Wrong answers will be calculated if a
> simulator uses the Ccomp data as an additional load on the output and adjusts
> the initial ramp rate accordingly. **This will be double-counting the effect of
> Ccomp.** On the receiver side, the problem of double-counting Ccomp's effect
> does not arise."

The reasoning is simple once stated. The V-T waveform was measured *at the pin of
a real die*, so the die capacitance was physically present and already shaped that
waveform. If a simulator replays that waveform **and** hangs C_comp on the output
as an extra load, the die capacitance is applied twice and the edge comes out too
slow.

§11.8.2 gives the test:

> "Varying C_comp is supposed to have **no effect on driver rise and fall**...
> One way to test this is to reduce Ccomp to nearly zero and then raise it to a
> very large value, say 50 pF... **If the buffer rise time changes as C_comp is
> varied, then C_comp may be getting double counted.**"

### Why this did *not* apply to pybis — and how I got it wrong

I ran that test, found pybis's edge does move with C_comp, and reported that pybis
double-counts it. **That was wrong**, and it is worth understanding why, because
the mistake is instructive.

The book's rule targets a simulator that uses the V-T data *directly as the
driving waveform*. pybis does not. It **back-solves `Ku` with the C_comp
displacement current explicitly subtracted out** (`solve_k_params_output`:
`i1 = ... - i_c_comp`). So pybis's `Ku` is C_comp-free by construction, and the
explicit C_comp in its netlist is the *required other half* of that decomposition.
Under that scheme the edge is *supposed* to move with C_comp.

Applying a rule outside the implementation it describes produced a confident,
wrong conclusion. The fix was to use a test that does not depend on the
implementation at all — which is the next section.

---

## 4. Golden waveforms — the most useful idea we took

### What a golden waveform is

An IBIS file's V-T tables are not just parameters. They are **a recorded waveform
plus the exact fixture that produced it** — `R_fixture`, `V_fixture`. That makes
them a self-contained test: put the model into that same fixture, simulate, and
the result should reproduce the table.

The book (§17.14):

> "When provided in an IBIS model, the V-T waveform tables can be reproduced to
> verify the accuracy of the simulator... Since the load conditions that produced
> the tables should be provided, the simulator should be able to reproduce those
> waveforms using the specified loads. **The simulator is verified if the IBIS
> waveforms and the simulator waveforms agree.**"

And §16.5.1 states the requirement plainly: *the test circuit's load should match
the load specified in the V-T table being verified.*

### Why it is powerful

Every other comparison we had been running involved at least two things that could
be wrong at once — our model, the reference model, the simulator, the bench. A
golden-waveform test involves **only the model and its own data**. No transistor,
no native IBIS, no second simulator. If the model cannot reproduce the waveform it
was built from, in the fixture it was built in, that is unambiguous.

### What it settled for us

Running it on all three buffers, with nominal C_comp against C_comp = 0:

| buffer | C_comp | FOM (nominal) | FOM (C_comp = 0) |
|---|---:|---:|---:|
| inv_chain | 0.468 pF | 0.09 – 0.41% | 0.60 – 0.74% |
| io_buf | 1.2 pF | 0.05 – 0.17% | 0.19 – 0.55% |
| ex2 | 5.0 pF | 0.03 – 0.28% | 0.82 – 1.16% |

Nominal wins on **all twelve tables**, and the margin *grows with the die
capacitance* — removing C_comp costs ex2 (5 pF) a −124 to −178 ps correction
against inv_chain's −4 to −6 ps. If C_comp were double-counted, removing it would
*help*, and help most where it is largest. Exactly the opposite happens.

So pybis handles C_comp correctly, and the earlier conclusion was overturned by a
test that could not be argued with.

### The caveat the book adds

A golden-waveform test verifies the **simulator**, not the **model**. Reproducing
your own tables says your playback machinery is right; it says nothing about
whether those tables describe the real silicon. For that you still need
correlation against SPICE or measurement — which is what our transistor
comparisons do.

---

## 5. Figure of Merit — why you align before you score

The book describes waveform comparison as a two-phase operation:

> "Waveform comparison usually has two phases. **First, the waveform is shifted**,
> and then a visual comparison or Figure of Merit calculation is made... the
> shifted and unshifted waveforms will have a poor FOM unless the two waveforms
> are aligned in time."

The IBIS Accuracy Handbook's curve-overlay metric:

    FOM(%) = 100% × Σ |X_golden − X_DUT| / (Δx × N)

### Why this matters more than it sounds

A raw RMSE between two waveforms conflates **when** the edge happened with **what
shape** it had. On a fast edge that is not a small effect — it is usually the
dominant one.

We measured this directly. pybis against native IBIS on one buffer:

- raw RMSE: **17.3 mV**
- after shifting pybis by −9 ps: **2.3 mV**

**87% of the "error" was a time shift.** And the worst-case 93 mV gap turned out
to be exactly `4.9 ps × 18.5 mV/ps` — the lag multiplied by the slew rate. Two
numbers we had been treating as separate defects ("the lag" and "the gap") were
one fact viewed two ways.

### The practical rule

Report **two numbers, never one**: the time shift, and the post-alignment FOM. A
single unaligned RMSE tells you something is wrong without telling you whether it
is timing or shape, and it inflates picoseconds into millivolts.

---

## 6. The I-V verification identity

§16.5.1 gives the DC check a validator applies to any IBIS model:

    I_up    = [Pullup]   + [POWER Clamp] + [GND Clamp]
    I_dn    = [Pulldown] + [POWER Clamp] + [GND Clamp]
    I_recvr =              [POWER Clamp] + [GND Clamp]

The clamps are always in the picture; the driver tables add to them. This is why
clamp extraction has to isolate the clamps from the drivers — if driver current
leaks into a clamp table, it gets counted twice and the model's implied DC
operating point disagrees with its own waveforms.

That is exactly what happened to our open-drain conversion: a spurious 51 mA in
`[GND Clamp]` at +3.3 V, which is the pulldown current mis-attributed, because an
enable-less open-drain has no state in which its sole driver is off. The validator
summed pulldown + clamp, computed a released-high level of 0.75 V against the
waveform's 3.30 V, and rejected the model. Fixing the extraction dropped the clamp
current to 0.8 nA.

A real ground clamp is an ESD diode: it conducts **below 0 V**, not at +3.3 V.
That is the sanity check to apply by eye.

---

## 7. V-T data versus a simple ramp

IBIS allows a driver to be described either by full V-T tables or by a `[Ramp]`
— just a dV/dt. The book (§11.11) explains the cost of the shortcut: a ramp
assumes the edge is a straight line from rail to rail, then turns a sharp corner.
Real edges round off near the rails.

> "The effect of sharp corner V-T curves versus round corner V-T curves is to
> inject more high-frequency edge-rate related energy into the simulations than is
> sometimes warranted. This can result in overly conservative designs and problems
> in correlating simulated to measured results."

So a ramp-only model tends to make a design look worse than it is, and makes
measurement correlation harder. Use V-T where it exists.

---

## 8. Smaller points that changed how we work

- **Corner semantics** (§13.3): `min` is low-current transistors, `max` is
  high-current. And *"it is possible for an I/O to have its fastest edge rate at
  some other statistical corner"* — fastest edge is not automatically `max`.
- **Die temperature** (§13.3): characterisation is typically at ~50 °C die, not
  27 °C ambient. Our work runs at 27 °C throughout — self-consistent, but not the
  convention.
- **Column order** (§11.10.1): IBIS files are typ-min-max left to right, while
  data books are min-typ-max. A documented source of translation errors.
- **Line length** (§12.10): lines over 80 ASCII characters are on the IBIS
  common-errors checklist.
- **Clean waveforms are a prerequisite** (§8.9): *"serious ringing and
  non-monotonicities tend to invalidate simulations because they are hard to
  interpret, repeat, reproduce and verify with bench measurements."* Relevant to
  us, since pybis shows ringing through the Ku transition.
- **C_comp is not an independent knob** (§11.8.1): *"in a real device, C_comp will
  be interdependent with slew rate... making the area of a driver larger increases
  the current drive capability. This also increases Ccomp."* So editing C_comp in a
  file is a what-if, not a physical variant.

---

## 9. What we changed because of the book

1. **Adopted the golden-waveform test** as the standing model health check. It is
   self-contained, cheap, and it overturned a wrong conclusion we had already
   written down.
2. **Switched to shift + post-alignment FOM** instead of raw RMSE, after finding
   87% of one headline error was a time shift.
3. **Stopped treating `max|Ku| > 1` as corruption.** It is a real signature of a
   large die capacitance driven fast, which makes our fixed 1.25 cap wrong in
   principle — it currently rejects ex2's own reference model.
4. **Confirmed a clamp-extraction fix** against the book's I-V identity rather
   than against our own intuition.

## 10. And one thing the book cost us

The C_comp diagnostic in §11.8.2 is stated generally but is implementation
specific. Applying it to pybis — which decomposes C_comp differently — produced a
confident wrong answer that stood until the golden-waveform test overturned it.

The lesson is not that the book is unreliable. It is that a diagnostic carries the
assumptions of the architecture it was written for, and those assumptions need
checking before the diagnostic is trusted. **A test that depends on no
implementation at all, like the golden waveform, is worth more than a clever one
that depends on the wrong one.**
