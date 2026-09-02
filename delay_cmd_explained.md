# delay_cmd, explained

A note to present from. Written 2026-09-02.

---

## The one-sentence version

> The shipped model turns each input edge into a 10 picosecond pulse and
> integrates that pulse onto a capacitor to rebuild the input level.
> `delay_cmd` skips both steps and just delays the level directly, so there is
> no integral to get wrong.

If you only say one thing, say that. Everything below is support.

---

## 1. What the command layer is for

The gate-state model needs one number per device: **should the pullup be on
right now?** Call that number `GUPCMD`. 1 means on, 0 means off. The gate `GUP`
then chases that number through an RC, and `Ku = pwl(GUP)`.

The subtlety is that the answer has to arrive **late**. Real silicon has a
predriver, so the output devices do not respond the instant the input moves.
For io_buf, from the fit:

| | onset delay |
|---|---|
| pullup turns on | 0.9926 ns after the input rises |
| pullup turns off | 0.0677 ns after the input falls |
| pulldown turns on | 1.8313 ns after the input falls |
| pulldown turns off | 0.8502 ns after the input rises |

Four different delays. So the command layer's whole job is: **take the input
level, and produce a delayed copy of it, with a different delay per device.**

That is all it has to do. Keep that sentence in mind, because the shipped
implementation does something much more elaborate.

---

## 2. How the shipped command layer does it

Six steps, straight from the generated netlist.

**Step 1 — the input becomes an ideal step.**

```
B10 NINX 0 V = (V(IN,VSS) > 1.4) ? 1.0 : 0.0
```

A hard comparator. The input ramp is thrown away; `NINX` jumps 0 to 1 instantly.

**Step 2 — the step becomes a 10 ps pulse.** *(this is where it goes wrong)*

```
T2  HNI 0 HN9 0 Z0=50 Td=10p      <- a 10 ps delay line
B13 HN2 0 V = V(HNI,HN9) * 8      <- now, minus 10-ps-ago
```

This is a differentiator. "Now minus 10-ps-ago" is 1.0 for exactly 10 ps after
the step and 0 otherwise. So we get a 10 ps rectangle, one per edge.

**The level is now destroyed.** All that survives is a marker saying "an edge
happened here."

**Step 3 — the pulse is delayed by the fitted turn-on time.**

```
TPUONP  RISEEDGE 0 PUONP  0 Z0=50 Td=0.9926n
TPUOFFP FALLEDGE 0 PUOFFP 0 Z0=50 Td=0.0677n
```

**Step 4 — the pulse is integrated back onto a capacitor.**

```
CGUPCMD    GUPCMD 0 1p ic=0
RGUPCMD    GUPCMD 0 1e15                       <- no DC path
BGUPCMDON  GUPCMD 0 I = -1p * V(PUONP)  / 10p  <- charge up
BGUPCMDOFF GUPCMD 0 I = +1p * V(PUOFFP) / 10p  <- discharge
```

The gain is 1/10 ps. A 10 ps pulse of height 1 has area 10 ps, so it should
move `GUPCMD` by exactly 1.000. **On paper this is exact.**

**Step 5 — clamp, and drive the gate.**

```
BGUPTARGET GUPTARGET 0 V = min(max(V(GUPCMD), 0), 1)
BGUP       GUP 0 I = -1p * (V(GUPTARGET) - V(GUP)) / tau
```

**Step 6 — a patch, because step 4 drifts.** After the input has been stable
for 2.958 ns, gently pull `GUPCMD` back toward the input level with a 1.13 ns
time constant.

---

## 3. Why that breaks

Two things combine.

**First: the command is the model's only memory.** The capacitor has a 1e15 ohm
resistor across it — effectively no DC path. Nothing pulls it back to a rail.
So whatever number sits on that capacitor *is* the model's entire record of
what the input did. Any error in the integral is permanent.

**Second: the thing being integrated is a 10 picosecond rectangle** — the
shortest feature in the whole circuit. ngspice chooses its timesteps based on
everything else that is happening. If a timestep straddles the pulse edge, the
solver integrates a trapezoid instead of a rectangle.

I measured exactly this, varying **only** the maximum timestep:

| max timestep | "on" packet | "off" packet | left stranded |
|---|---|---|---|
| adaptive (as the study runs) | 1.00950 | 0.98242 | **+0.036** |
| 1.0 ps | 1.00736 | 1.02655 | **−0.010** |
| 0.2 ps | 0.99711 | 1.01088 | **−0.005** |
| 0.05 ps | 1.00200 | 0.99854 | **+0.012** |

Every packet should be exactly 1.000. None of them is.

The stranded charge is the *difference* of two packets, so it inherits both
errors — **and its sign flips with the timestep.**

That last point is the one worth landing. It means:

> The residue is not a modelling error with a cause you can fix. It is
> integration error, and it is as likely to be positive as negative.

**One consequence to be ready for:** any tuning fix is a coin flip. A change
that shifts the solver's trajectory can improve the pad without removing a
cause. That is why we now re-run every command-layer change with
`.tran ... 0 0.2p` and check the win survives.

---

## 4. What the user sees, and why some cases looked clean

The stranded charge leaks through the chain:

```
GUPCMD  ->  GUPTARGET  ->  GUP  ->  Ku  ->  pad
```

A small false pullup command holds the pad above zero. On io_buf short-high
that shows as roughly 60 to 85 mV of pad offset for several nanoseconds.

**It is not a DC offset.** The step-6 patch does eventually clean it up — but
it is gated off for 2.958 ns and then decays with a 1.13 ns time constant, so
it is about a 6 ns tail. Our plots end at 10 ns, which is why it looked
permanent.

**And it is on all five targets, not three.** The command is clamped before it
drives the gate:

```
BGUPTARGET GUPTARGET 0 V = min(max(V(GUPCMD), 0), 1)
```

The clamp erases anything negative. We had only been saving the clamped node.

| target | 90% | 80% | 70% | 60% | 50% |
|---|---|---|---|---|---|
| as probed (clamped) | 0.0259 | 0.0000 | 0.0000 | 0.0360 | 0.0237 |
| the real node | 0.0259 | **−0.011** | **−0.006** | 0.0360 | 0.0237 |

80% and 70% were never clean. Their errors went negative and the clamp hid
them. The pulldown command is corrupted too, settling between 0.976 and 1.004
against a rail of 1.

---

## 5. What delay_cmd does instead

Delete steps 2 and 4.

`NINX` is **already** the level: 1 when the input is high, 0 when it is low.
Nothing needs to reconstruct it. So the rule becomes:

> The pullup command is 1 if the input has been high for at least
> `pu_on_delay`, and 0 if it has been low for at least `pu_off_delay`.

Same timing, same behaviour, but:

- **no differentiation** — the level is never destroyed
- **no integration** — nothing to accumulate error into
- **exactly 0 or 1 at the rails by construction**, whatever timesteps ngspice picks
- **no restore patch**, so no 2.958 ns blind window

Measured settled command on io_buf short-high 1792 ps:

| | settled GUPCMD |
|---|---|
| edge-integrating (shipped) | **+0.03603** |
| level command (delay_cmd) | **+0.00000** |

Not "small". Zero, by construction.

**Figure to show:** `results/settled_offset_diagnosis_2026-08-27/explainers/q3_how_the_command_differs.png`

It zooms to picosecond scale on the two instants the command moves. The shipped
trace *ramps* over 10 ps as the solver integrates the pulse and lands at
**1.01844**, then comes down and lands at **0.03603**. The level trace *steps*
to exactly **1.00000** and exactly **0.00000**. Third panel shows the residue
sitting there for 3 ns before the cleanup starts.

---

## 6. The evidence it works

**The offset is removed.** Pad plateau after the reversal, measured before the
pulldown engages so it reads the stranded charge alone, averaged over the two
io_buf short-high cases where the defect is visible:

| | plateau | off the transistor |
|---|---|---|
| HSPICE transistor | 7.5 mV | — |
| HSPICE native IBIS | 6.4 mV | 1.5 mV |
| gate-state, as shipped | 63.9 mV | **56.5 mV** |
| + restore-term fix | 26.5 mV | 27.7 mV |
| **+ delay_cmd** | **3.7 mV** | **3.7 mV** |

**Figure:** `results/settled_offset_diagnosis_2026-08-27/13_offset_removed_by_level_command.png`

**It does not break anything else.** Comparing against the shipped model over
the 29 stress cases where both builds ran, pad RMSE against the transistor:

| scope | shipped | delay_cmd | change |
|---|---|---|---|
| all matched cases | 108.6 mV | **92.2 mV** | −16.4 |
| io_buf short high | 27.3 | 21.2 | −6.1 |
| io_buf short low | 201.4 | 149.7 | **−51.8** |
| inv_chain short high | 29.9 | 19.5 | −10.4 |
| inv_chain short low | 83.6 | 65.7 | −17.9 |
| ex2 short high | 92.5 | 87.5 | −5.0 |
| ex2 short low | 200.6 | 195.6 | −5.0 |

**Every one of the 29 improves.** Sorted by regression, the worst case is
−0.6 mV, which is still an improvement.

**It is also the most robust.** ngspice runs that completed, io_buf short-high:

| | completed |
|---|---|
| delay_cmd | **9 / 10** |
| gate-state (shipped) | 5 / 10 |
| predriver_cmd | 3 / 10 |

**Figures:** 39 per-case figures in
`results/settled_offset_diagnosis_2026-08-27/all_cases/`

---

## 7. The dead zone — be ready for this one

Someone will ask about the gap where neither device is driving. Here is the
honest position, including a correction we made.

io_buf turns its pullup **off** 0.0677 ns after the input falls, and does not
turn the pulldown **on** for 1.8313 ns. That is a **1.764 ns gap** where
neither device is commanded on. Measured in the model: 1.262 ns wide.

**The correction:** we first said `delay_cmd` creates this gap. It does not.
**Both** command layers have it — it is a property of the fitted delays, not of
the command formulation.

**And the gap is real.** Confirmed three independent ways:

1. **The IBIS table** — Kd is 0.0093 at 1.802 ns and 0.1482 at 1.898 ns, so the
   5% crossing lands at about 1.83 ns.
2. **The fitted parameters** — `pd_on_delay` = 1.8313 ns.
3. **The transistor** — silicon's own Kd reaches 50% at edge + 2.05 ns,
   matching the table's 2.048 ns.

It is an io_buf peculiarity:

| buffer | pu_off to pd_on gap |
|---|---|
| inv_chain | 0.030 ns |
| ex2 | 0.315 ns |
| **io_buf** | **1.764 ns** |

io_buf simply has a fast pullup release and a slow pulldown engage. It gets
away with it because the 50 ohm load discharges the pad on its own.

**What differs is what happens inside the gap.** The shipped block holds
+0.036 of stranded charge through it, so the pullup stays weakly on — an
accidental keeper. `delay_cmd` holds exactly 0.000 and lets the node go, which
is the correct behaviour.

Mean pad error against the transistor, measured **inside** the dead zone,
across all nine io_buf widths:

| | mean error |
|---|---|
| edge-integrating (shipped) | 63.85 mV |
| **transport-delay (delay_cmd)** | **33.32 mV** |

`delay_cmd` is twice as accurate exactly where we had claimed it was defective.
The shipped model had been covering a real device feature with a numerical
error.

**Figure:** `results/settled_offset_diagnosis_2026-08-27/05_delay_cmd_dead_zone.png`

---

## 8. What is still wrong with it

Do not oversell this. Two things stand:

**1. One case in ten will not converge.** io_buf short-high at 2484 ps. ngspice
cannot integrate it.

Be careful here: we previously explained this by saying the pad loses its
conductance path during the dead zone. **That explanation is withdrawn** — the
pad has a 50 ohm load to ground throughout and is never floating. The stall is
real and reproducible, but its cause is open.

Worth saying in the same breath: `delay_cmd` still converges on 9 of 10 io_buf
short-high cases, against 5 of 10 for the shipped model. It is the most robust
of the three, not the least.

**2. It splits pulses narrower than the difference between the two delays.**
If the input pulse is shorter than `pd_on_delay − pu_off_delay`, the two
independently delayed levels can produce a command sequence the buffer would
not physically produce.

`predriver_cmd` was the proposed structural answer to this — it carries the
delay in a state a new edge can interrupt, so the devices hand over instead of
both letting go. **But it is not ready:** it fails to converge on 7 of 10
io_buf short-high cases. Good idea, unusable implementation.

---

## 9. Questions you are likely to get

**"Isn't 36 millivolts of command error tiny?"**
It is 3.6% of the command range, and it sits directly on Ku, which multiplies
the pullup current. It shows up as 60 to 85 mV at the pad and holds for about
6 ns. And it is not a bounded error — it is an accumulated one, so a longer
pulse train makes it worse, not better.

**"Why not just fix the integration — smaller timesteps?"**
Look at the timestep table. 0.05 ps still gives +0.012, and the sign flips
between settings. Shrinking the timestep does not converge the error to zero,
it just moves it. And a 0.05 ps maximum timestep on a 22 ns run is not a
practical simulation.

**"Why not just improve the cleanup patch?"**
We tried, and it does about a third of the job — 63.9 mV to 26.5 mV against a
target of 7.5. It cannot do better in principle, because it acts *after* the
charge is stranded and it is deliberately blind for 2.958 ns so it does not
disturb a command still in flight. That blind window is exactly the window
where the pad is wrong.

**"Is this just tuning to the cases you looked at?"**
No. It improves all 29 matched stress cases across three buffers and both pulse
directions, and it was not fitted to any of them — the change removes a
mechanism rather than adjusting a parameter.

**"What about the timing shift?"**
Different defect, still open. The model runs 70 to 100 ps late on the io_buf
falling edge on every case, and native IBIS runs 5 to 26 ps early on the same
cases. `delay_cmd` does not address it. It is the larger of the two errors and
nothing has been tried on it yet.

---

## 10. If you have 60 seconds

1. The command layer's job is to produce a delayed copy of the input level.
2. The shipped one takes a detour: differentiate the level to a 10 ps pulse,
   then integrate that pulse back onto a capacitor with no DC path.
3. That integral is never exact — the residue is 0.036 on the study's
   timesteps, and its sign flips if you change the timestep.
4. The residue is a false pullup command. It holds the pad 60 to 85 mV high for
   about 6 ns.
5. `delay_cmd` deletes the detour and delays the level directly. The command is
   exactly 0 or 1 by construction.
6. Offset gone: 63.9 mV to 3.7 mV, against a transistor at 7.5 mV.
7. It improves all 29 stress cases and is the most robust of the three builds.
8. One case in ten still will not converge, and we do not yet know why.
