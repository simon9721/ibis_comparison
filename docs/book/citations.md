# The findings against the book

Leventhal & Green, *Semiconductor Modeling: For Simulating Signal, Power, and Electromagnetic Integrity* (Springer 2006), the copy in the repository root. Page references are the printed page (p.) with the PDF page in brackets; the OCR text is in `docs/book/pages.json` and every quote below is checked verbatim against it (OCR spellings kept).

The book never uses the words Ku or Kd, never discusses a pulse shorter than a transition, and contains no predriver equations. What it does contain is the frame: what an IBIS model is defined to be, the assumptions the specification makes about delay and about the V-T tables, the rules for C_comp, Vinh/Vinl and open-drain, the MOSFET law behind the curve, and the verification discipline. Each finding below is placed against that frame, and where the book has nothing, the entry says so.

## Frame

### F0 · What an IBIS model is, and what it leaves out

**Our finding.** Every stressed error on twelve buffers traced to the gate driver (the predriver), which the IBIS file does not describe. The model has a static output stage and, until this work, no internal state between the input pin and the pad.

> "That balance is accomplished by ignoring the internal behavior of drivers and receivers and by modeling just the behavior at the terminals."
> — p.314 [pdf 324], 10.9 Summary

> "IBIS is a behavioral model The behavior at its input and output pins is described, not what happens between input and output pins."
> — p.301 [pdf 311], 10.6 How IBIS Circuit Modeling Methodology Is Used

> "Solving a SPICE circuit requires solving all the internal nodes of the SPICE models. Simulation run times increase as the cube of the number of circuit nodes- and a SPICE model can contain over 50 nodes. The workload of simulating a board using the IBIS model is manageable because IBIS models have only three to six internal nodes."
> — p.263 [pdf 273], 10.1 Introduction

> "The difference is that most of the sub-elements of the IBIS model are visualized only as "black boxes.""
> — p.300 [pdf 310], 10.5 Schematic of a Basic IBIS Model

> "Provides data on behavior at the input and output ports of a device. What the device consists of internally remains a black (opaque) box."
> — p.709 [pdf 711], Glossary

> "Traditional IBIS modeling is designed to ignore any pass-through, input-output modeling of behavior. But complex I/O requires some modeling of the buffer internal behavior. A new balance between simulation speed and I/O internal modeling will have to be devised."
> — p.580 [pdf 585], 20.5 Behavioral Modeling

**Reading.** The book states the design intent we ran into: IBIS describes behaviour at the pins and nothing between them (p.301, p.314), a SPICE buffer has 50+ nodes where IBIS has three to six (p.263), and complex I/O 'requires some modeling of the buffer internal behavior' (p.580). Our predriver chain is that internal modelling.

### F0b · The assumption the whole investigation overturned: the predriver's delay is folded into the output cell

**Our finding.** The V-T tables carry the predriver only as a dead time before the pad moves. Under a short pulse the real predriver is a chain of stages that is interrupted mid-travel; a delay cannot be interrupted, so the model turns fully on at every width.

> "IBIS ignores propagation delay (= flight time) from input to output through an IC device. But the rise and fall times of a buffer (buffer delay) can affect time-of-flight measurements from driver to receiver. An event' occurs that tells the output buffer to turn-on and turn-off. Because of its finite slew rate, the turn-on and turn-off time of a buffer behaves nearly identically with propagation delay. Thus, the term buffer delay."
> — p.354 [pdf 364], 11.14 Other Considerations: Timing and Noise Margin Issues

> "Propagation delay of a buffer is assumed to be entirely due to turn-on and turn-off delay in the output cell itself. Actual flight time from input pin to output pin of a device is assumed to be negligible."
> — p.354 [pdf 364], 11.14 Other Considerations: Timing and Noise Margin Issues

> "In logic terms, a state-variable change."
> — p.354 [pdf 364], 11.14 Other Considerations: Timing and Noise Margin Issues

> "The first several table entries might be some lead-in time caused by some undefined internal buffer delay before the voltage actually starts transitioning."
> — p.123 [pdf 138], 4.5 IBIS Models

> "Any actual device differences in internal buffer delay time between rising and falling edges should appear as differing lead-in times between the rising and the falling waveforms in the tables just as any differences in actual device rise and fall times appear as differing voltage-time entries in the tables."
> — p.123 [pdf 138], 4.5 IBIS Models

> "IBIS assumes that an "event generator" tells the output generator/driver to switch and send its signal down a transmission line to a load/receiver."
> — p.301 [pdf 311], 10.6 How IBIS Circuit Modeling Methodology Is Used

**Reading.** p.354 is the book's explicit statement of the assumption: propagation through the device is 'entirely due to turn-on and turn-off delay in the output cell itself', triggered by an 'event' (a state-variable change). p.123 says the table's lead-in is 'some undefined internal buffer delay'. This is exactly why adding the table delay back cannot reproduce a partial pulse: the book's model has an event and a delay, not a mechanism that can be caught half way.

## Before the rounds

### P1 · Exhibit 1: the timing shift splits into an accumulating part and a stress pedestal

**Our finding.** Native and our model share an outward, accumulating lateness; a fixed pedestal appears only when the pulse is cut short and is ours alone.

> "After the switching event is over, the V-T characteristics of the driver do not enter into circuit behavior until another switch event occurs. The driver spends most of its time in the steady-state condition, where subsequent behavior is determined by its I-V curve."
> — p.301 [pdf 311], 10.6 How IBIS Circuit Modeling Methodology Is Used

> "Propagation delay of a buffer is assumed to be entirely due to turn-on and turn-off delay in the output cell itself. Actual flight time from input pin to output pin of a device is assumed to be negligible."
> — p.354 [pdf 364], 11.14 Other Considerations: Timing and Noise Margin Issues

**Reading.** p.301: once a switching event is over the V-T data 'do not enter into circuit behavior until another switch event occurs'. A table replay therefore has no notion of an interrupted transition, which is the pedestal. The book does not discuss short pulses; it supports the diagnosis by describing the machinery.

### P2 · Exhibit 2: the accumulating part scales with C_comp, and the declared value is not trustworthy

**Our finding.** The outward lateness is the pad capacitor; io_buf closes at 0.3 pF, not the declared 1.2 pF. Later: the whole ex2 family closes at 1.75 to 2.0 pF against a declared 5.0.

> "Information about such correlation is not available in all cases and C_comp is considered an independent variable. This is because C_comp includes bonding pad capacitance, which does not necessarily track fabrication process variations."
> — p.116 [pdf 131], 4.5 IBIS Models

> "Ccomp is one of the most difficult parameters to obtain for an IBIS model. C_comp is the effective loading capacitance for signal reflections at the I/O pad for a driver or receiver. This is greater than the fixed wiring capacitance at the pad, since it also includes junction capacitances."
> — p.405 [pdf 414], 13.3 SPICE-to-IBIS Conversion Methodology

> "Physically, there is capacitance to each DC voltage. This capacitance also varies with voltage, as well as with buffer state (driving high, driving low, or receiving). However, there is only one parameter in the IBIS 3.2 model for this capacitance."
> — p.405 [pdf 414], 13.3 SPICE-to-IBIS Conversion Methodology

> "values, the value of C_comp is sometimes tweaked to get better agreement between the IBIS model and SPICE and bench measurements."
> — p.406 [pdf 415], 13.3 SPICE-to-IBIS Conversion Methodology

> "Since 1 = C*(dV/dt), and C = I/(dV/dt), C_comp is easily found using a voltage ramp. dV is the typical signal swing and dt is the typical transition time. Similarly, values for C comp can be determined for the min and max corner conditions. The current I is not measured instantaneously, but is averaged over a rising and falling ramp. This averages out the voltage dependence of the capacitance just as a signal would see it averaged."
> — p.406 [pdf 415], 13.3 SPICE-to-IBIS Conversion Methodology

> "Sometimes an averaged capacitance is not sufficient (for example, if reflections from a driver or the capacitance varies with driver state, and this is significant in a design). In this case, a table-based IBIS model could be replaced with a SPICE, Verilog-AMS, or VHDL-AMS model."
> — p.406 [pdf 415], 13.3 SPICE-to-IBIS Conversion Methodology

> "The netlist used to generate IBIS model data must also include all of the capacitance loading on the output pad of the buffer. Total pad capacitances of 2-5 pF are not uncommon. Some of this capacitance comes from the transistor and diode capacitances, which are nonnally included in the SPICE models for these devices. Because the output drive transistors are relatively large, their capacitance is usually large."
> — p.398 [pdf 407], 13.2 I/O Buffer Example

**Reading.** The book says C_comp is 'one of the most difficult parameters to obtain', an effective, voltage- and state-dependent quantity that 'is sometimes tweaked' (p.405-406), an 'independent variable' that includes the bond pad (p.116), typically 2-5 pF (p.398). Our loop method is a dynamic version of the I = C dV/dt extraction on p.406; the book's caveat that an averaged capacitance is sometimes not sufficient matches the 1.75 versus 3.0 pF gap between the two solves.

### P3 · Exhibit 3: three dead ends closed (stranded command charge, the gate as a stopwatch, the restore gate)

**Our finding.** None of the three mechanisms inside the command layer explains the pedestal; the residual does.

> "Actually, the ramp rate is limited by all the internal driver linear and non-linear small-signal and large-signal characteristics, including real and effective reactive elements�not just slew-rate rise-time-limited. Internal Miller Capacitance [87] also plays a role. From a simulator point of view, the ramp slew-rate limit is a behavioral model of an internal rise-time-limited component. In any event, something (a state event) switches the output, which then ramps the voltage up depending on this internal drive limit and the loading seen at the driver."
> — p.319 [pdf 329], 11.5 Why We Use the IBIS Model

> "To visuaHze the IBIS driver-switching event, we should think about the IBIS dV/dt data. Figure 11-1 shows a current source charging a capacitor. The voltage is a ramp with a slope of i/C as in: i = C(dV/dt). This C is not identical with Ccomp."
> — p.319 [pdf 329], 11.5 Why We Use the IBIS Model

**Reading.** p.319 is the closest the book comes to a mechanism: 'something (a state event) switches the output, which then ramps'. It names no internal state beyond the event, so nothing in the book predicts or excludes these mechanisms; the passage only confirms that the replay layer is stateless by design.

### P4 · Exhibit 4: the stressed pad and its coefficients; two-fixture solve

**Our finding.** Ku and Kd are solved from the transistor's two fixture runs; both IBIS models cut the pull-up short and turn the pull-down on late under stress.

> "Note: In most cases, two [Rising Waveform] tables and two [Falling Waveform] tables will be necessary for accurate modeling."
> — p.124 [pdf 139], 4.5 IBIS Models

> "Vpad vs. Time (data rising, R_fixture to Vcc) Vpad vs. Time (data falling, R_fixture to Vcc) Vpad vs. Time (data rising, R fixture to GND) Vpad vs. Time (data falling, R_fixture to GND)"
> — p.401 [pdf 410], 13.3 SPICE-to-IBIS Conversion Methodology

> "The behavioral parts of the IBIS model are its I-V data tables (for its dynamic, non-linear impedance behavior) and its V-T data tables (for its dynamic, non-linear switching signal behavior)."
> — p.300 [pdf 310], 10.5 Schematic of a Basic IBIS Model

**Reading.** The book gives the two-fixture requirement (two rising and two falling tables, p.124; the four V-T simulations to Vcc and GND, p.401) without the switching-coefficient algebra. The term Ku/Kd does not appear anywhere in the book; the coefficient view is ours, built on the book's tables.

### P5 · Exhibit 5: coefficients solved within ~90 ps of a reversal are unusable; the Miller bump

**Our finding.** Within 80-90 ps of the reversal the solved Ku/Kd spike, not from ill-conditioning but because both fixtures are not in the same internal state mid-reversal. Every window starts at +90 ps.

> "One also sees a feedforward effect from gate to drain, which is what causes the initial bump sometimes seen in CMOS V-T curves."
> — p.64 [pdf 80], 3.5 How BJT and FET Construction Affect Their Operation

> "The curves also exhibit an initial peak due to forward voltage coupling caused by the capacitance from the FET gates to the output pad (Cds)."
> — p.404 [pdf 413], 13.3 SPICE-to-IBIS Conversion Methodology

> "Actually, the ramp rate is limited by all the internal driver linear and non-linear small-signal and large-signal characteristics, including real and effective reactive elements�not just slew-rate rise-time-limited. Internal Miller Capacitance [87] also plays a role. From a simulator point of view, the ramp slew-rate limit is a behavioral model of an internal rise-time-limited component. In any event, something (a state event) switches the output, which then ramps the voltage up depending on this internal drive limit and the loading seen at the driver."
> — p.319 [pdf 329], 11.5 Why We Use the IBIS Model

**Reading.** The book attributes the 'initial bump sometimes seen in CMOS V-T curves' to gate-to-drain feedforward (p.64) and the 'initial peak' in extracted V-T curves to gate-to-pad capacitance (p.404): the same Miller coupling that puts the transistor's Ku above 1 at the falling edge and spoils the solve at the reversal.

### P6 · Exhibit 6: the pedestal is the Kd residual, calibrated on a complete transition and applied to a truncated one

**Our finding.** The residual term reproduces a full edge and is 2 to 2.5 times too large on a partial one; scaling it by depth removes the pedestal.

> "A waveform table must include the entire waveform; that is, the first entry (or entries) in a voltage column must be the DC voltage of the output before switching and the last entry (or entries) of the column must be the final DC value of the output after switching."
> — p.122 [pdf 137], 4.5 IBIS Models

> "All V-T tables start at Time = 0.0, since there is only one toggle event in a SPICE V-T simulation."
> — p.407 [pdf 416], 13.3 SPICE-to-IBIS Conversion Methodology

> "First, the slowest transition needs to settle before the end of the simulation time."
> — p.402 [pdf 411], 13.3 SPICE-to-IBIS Conversion Methodology

> "The device is allowed to settle to semi- quiescent conditions. Allowing a buffer to reach quiescent conditions is a lot easier to measure, but this can be misleading in modeling dynamic switching behavior."
> — p.276 [pdf 286], 10.2 IBIS Specification

**Reading.** p.122 and p.407: a table 'must include the entire waveform' from one DC level to the other, and there is 'only one toggle event in a SPICE V-T simulation'. Everything the file knows is a complete transition from rest, which is why anything derived from it is calibrated for a complete transition. p.276 warns that quiescent characterisation 'can be misleading in modeling dynamic switching behavior'.

### P7 · Exhibit 7: the +1.8 ns pull-down turn-on bump is a marker the model cannot move

**Our finding.** The transistor's bump arrives earlier the shorter the pulse; ours does not move because it has no gate state to move it.

> "IBIS ignores propagation delay (= flight time) from input to output through an IC device. But the rise and fall times of a buffer (buffer delay) can affect time-of-flight measurements from driver to receiver. An event' occurs that tells the output buffer to turn-on and turn-off. Because of its finite slew rate, the turn-on and turn-off time of a buffer behaves nearly identically with propagation delay. Thus, the term buffer delay."
> — p.354 [pdf 364], 11.14 Other Considerations: Timing and Noise Margin Issues

> "After the switching event is over, the V-T characteristics of the driver do not enter into circuit behavior until another switch event occurs. The driver spends most of its time in the steady-state condition, where subsequent behavior is determined by its I-V curve."
> — p.301 [pdf 311], 10.6 How IBIS Circuit Modeling Methodology Is Used

**Reading.** No passage on this event. The book's turn-on/turn-off as an 'event' with a delay (p.354) is the reason the bump is fixed in our model; the book does not discuss a stress-dependent turn-on.

### P8 · Exhibit 8: pu_off cannot be derived; one parameter, two jobs

**Our finding.** The coefficient error and the amplitude error fall in opposite directions with the delay scale; no value serves both.

> "The ramps described by dV/dt can be a good approximation to the rising and falling edge waveforms, but often they are not."
> — p.278 [pdf 288], 10.2 IBIS Specification

> "Simplifying assumptions are made when the dV/dt of the rising and falling waveforms of a driver are used in simulations. The assumption is made that the waveforms are linear (straight lines) from 0% to 100% of the output swing."
> — p.337 [pdf 347], 11.11 Experiment 4: Using V-T Data Versus a Ramp

> "This is particularly seen in bus drivers that have been designed to avoid such reflections by having soft turnon and turnoff (example GTLP). The behavior of such devices in complex topologies cannot be modeled by simple slew rate information."
> — p.293 [pdf 303], 10.3 Sample IBIS Data File

> "When we simplify the model equations, we give up detail, subtlety, and accuracy."
> — p.590 [pdf 595], 20.6 Developing a Macromodel from the Behavioral Model

**Reading.** The book's recurring point is that a single slew or delay number cannot carry the shape of a transition (p.278, p.337, p.293), and that simplifying a model 'gives up detail, subtlety, and accuracy' (p.590). Our result is the same statement one level up: one delay cannot carry both the timing and the amount of a partial transition.

### P9 · Exhibit 9: the transistor's Ku overshoots at full swing; native's stored trajectory equals our solve

**Our finding.** Ku rises to 1.15-1.2 at the falling edge on both the transistor and native; our two-fixture solve reproduces native's stored St on all four edges.

> "One also sees a feedforward effect from gate to drain, which is what causes the initial bump sometimes seen in CMOS V-T curves."
> — p.64 [pdf 80], 3.5 How BJT and FET Construction Affect Their Operation

> "The curves also exhibit an initial peak due to forward voltage coupling caused by the capacitance from the FET gates to the output pad (Cds)."
> — p.404 [pdf 413], 13.3 SPICE-to-IBIS Conversion Methodology

> "Golden Waveforms are a set of SPICE waveforms simulated using known real world and ideal (standard) test loads. They are useftil in verifying the accuracy of behavioral simulation results against the SPICE model from which the IBIS model parameters originated."
> — p.381 [pdf 390], 12.9 Tools Provided by the IBIS Committee

> "The IBIS Accuracy Handbook uses the absolute error for its "curve overlay metric" FOM (in percent):"
> — p.488 [pdf 494], 16.2 Model Verification Methodology

**Reading.** Miller feedforward (p.64, p.404) is the physics of the overshoot. Comparing our extraction against native's stored trajectory is the book's golden-waveform idea (p.381) applied to coefficients rather than pads; the curve-overlay figure of merit (p.488) is the same kind of comparison.

### P10 · Exhibit 10: twelve buffers, two regimes

**Our finding.** Eleven buffers enter the reversal fully on (native too); io_buf alone is in the residual regime. Full-swing tables fit all twelve equally and say nothing about which regime a buffer is in.

> "Measurement-based behavioral models are only valid"
> — p.608 [pdf 613], 20.7 Developing a SPICE Macromodel from a Physical Model.... 592 20.8 Limitations in Models Due to Simplification

> "close to the bias conditions where the data was measured. Limitations to vaHd measurements are particularly important in semiconductors because they are usually quite non-linear."
> — p.609 [pdf 614], 20.7 Developing a SPICE Macromodel from a Physical Model.... 592 20.8 Limitations in Models Due to Simplification

> "First, behavioral models are usually accurate only over a narrow range close to their measurement conditions."
> — p.613 [pdf 618], 20.9 AMS Modeling Simplified

> "One challenging aspect of deep sub-sub-micron CMOS technology is that driver behavior is becoming sensitive to loading effects seen at the output terminals of the driver."
> — p.651 [pdf 655], 22.6 Advantages of SPICE, S-Parameters, and IBIS

**Reading.** p.608-609 and p.613: measurement-based behavioural models are 'only valid close to the bias conditions where the data was measured' and 'accurate only over a narrow range close to their measurement conditions'. A short pulse is outside the measured condition (a complete transition), which is the regime problem in the book's own terms.

### P11 · Exhibit 11: Ku is a static map of the real gate, and the loop measures C_comp

**Our finding.** Ku against the real gate voltage is single-valued once the solve uses the right C_comp; the C_comp that closes the loop is the pad's effective capacitance (ex2 1.75 pF, declared 5).

> "For: Forward Region, VDS > 0 ID = 0 For: VGS - VTO < 0 ID=(KP/2) *(W/L) *(VGS- VTEf For:0 < VGS - VTO < VDS"
> — p.89 [pdf 105], 3.7 Examples of Computing Electrical Properties from Structure. 71 3.8 Examples of SPICE Models and Parameters

> "In the case of the I-V data lookup tables, when a given voltage is applied across an output, a particular current results. An approximate answer is that the element acts like a dynamic non-linear resistor."
> — p.299 [pdf 309], 10.5 Schematic of a Basic IBIS Model

> "Since 1 = C*(dV/dt), and C = I/(dV/dt), C_comp is easily found using a voltage ramp. dV is the typical signal swing and dt is the typical transition time. Similarly, values for C comp can be determined for the min and max corner conditions. The current I is not measured instantaneously, but is averaged over a rising and falling ramp. This averages out the voltage dependence of the capacitance just as a signal would see it averaged."
> — p.406 [pdf 415], 13.3 SPICE-to-IBIS Conversion Methodology

> "Physically, there is capacitance to each DC voltage. This capacitance also varies with voltage, as well as with buffer state (driving high, driving low, or receiving). However, there is only one parameter in the IBIS 3.2 model for this capacitance."
> — p.405 [pdf 414], 13.3 SPICE-to-IBIS Conversion Methodology

**Reading.** The MOSFET equations (3-23)-(3-26) on p.89 make the drain current a function of gate voltage and drain voltage only, which is the static map. The loop method is the book's C = I/(dV/dt) extraction (p.406) made self-consistent: the value that makes the map single-valued.

### P12 · Exhibit 12: correcting C_comp alone makes ex2 worse (negative result)

**Our finding.** The declared 5 pF was compensating a third of the gate-timing error; the true 1.7 pF exposes it.

> "values, the value of C_comp is sometimes tweaked to get better agreement between the IBIS model and SPICE and bench measurements."
> — p.406 [pdf 415], 13.3 SPICE-to-IBIS Conversion Methodology

> "It is important to know that the effect of Ccomp on dV/dt or V-T is already included in the dV/dt and V-T data. Wrong answers will be calculated if a simulator uses the Ccomp data as an additional load on the output and adjusts the initial ramp rate accordingly. This will be double-counting the effect of Ccomp."
> — p.328 [pdf 338], 11.8 Experiment 2: Ccomp Loading

> "If the buffer rise time changes as C_comp is varied, then C_comp may be getting double counted in the simulation. In that case, we suggest simulating the rise and fall time of the IBIS test fixture with the correct values of Ccomp entered in min-typ-max. Then, we can observer whether the IBIS slew rate and/or V-T curves can be reproduced."
> — p.332 [pdf 342], 11.9 All-Important Zo: Algorithms and Field Solvers

> "But in a real device, C comp will be interdependent with slew rate. So from this manipulation, we can only draw general conclusions."
> — p.331 [pdf 341], 11.8 Experiment 2: Ccomp Loading

**Reading.** p.406 admits C_comp 'is sometimes tweaked to get better agreement'; p.328-332 explain that C_comp sets the ramp rate and is already inside the V-T data, and that changing it must not change the edge if the model is consistent. Our negative result is that consistency check failing: the right C_comp changed the edge, so something else (the gate) was wrong.

### P13 · Exhibit 13: a stressed train, nothing accumulates, but pulse 1 differs from the rest

**Our finding.** Errors re-settle within three pulses; a pulse arriving before the stages have returned to rest behaves differently (the recovery regime).

> "Also, some Signal Integrity tools do not allow buffers to toggle sooner than the end of the V-T table. In those tools, models created using default V-T end times might not toggle properly."
> — p.402 [pdf 411], 13.3 SPICE-to-IBIS Conversion Methodology

> "After the switching event is over, the V-T characteristics of the driver do not enter into circuit behavior until another switch event occurs. The driver spends most of its time in the steady-state condition, where subsequent behavior is determined by its I-V curve."
> — p.301 [pdf 311], 10.6 How IBIS Circuit Modeling Methodology Is Used

> "All V-T tables start at Time = 0.0, since there is only one toggle event in a SPICE V-T simulation."
> — p.407 [pdf 416], 13.3 SPICE-to-IBIS Conversion Methodology

**Reading.** p.402 is the book's only reference to a next edge arriving early: some tools 'do not allow buffers to toggle sooner than the end of the V-T table'. The specification has no concept of a pulse arriving before the previous transition has completed, which is why recovery is a third regime the file cannot pin.

### P14 · Exhibit 14: open-drain shows the stress law bare

**Our finding.** Kd at the pad minimum is linear in depth and the real gate tracks depth on all three open-drains; both IBIS models pull all the way down at every width.

> "Open-drain: This is a type of output driver model with an open pullup side. This name is retained for backward compatibility."
> — p.274 [pdf 284], 10.2 IBIS Specification

> "These model types indicate that the output has an OPEN side (do not use the [Pullup] keyword, or if it must be used, set I = 0 mA for all voltages specified) and the output SINKS current. Open_drain model type is retained for backward compatibility."
> — p.282 [pdf 292], 10.2 IBIS Specification

> "If: The Model_type is either an Open_sink type or Open_drain type; attach either a 50 ohm resistor or the semiconductor vendor suggested termination resistance to either POWER or the suggested termination voltage. Use this load to derive both the rising and falling edges."
> — p.121 [pdf 136], 4.5 IBIS Models

> "Due to the resistor, output swings will not make a full transition as expected."
> — p.121 [pdf 136], 4.5 IBIS Models

> "Or, as in the case of an open pullup, the pullup element may be missing."
> — p.297 [pdf 307], 10.5 Schematic of a Basic IBIS Model

**Reading.** The book gives the open-drain rules we used: no [Pullup] table, the output sinks current (p.282), the switching data taken with a 50 ohm resistor to POWER for both edges (p.121), and that 'output swings will not make a full transition' with the resistor (p.121). Nothing on its stressed behaviour.

### P15 · Exhibits 15-16: the slow-gate and cascade prototypes fix the pad without the gate

**Our finding.** A slow RC gate and a cascade of RC stages reproduce the stressed pad on ex2 but with the wrong internal gate: a fit, not a mechanism.

> "Viewing transistors as current sources allows the replacement of many stages of transistors. A few strategically placed controlled current sources act as the building blocks of a behavioral SPICE-based macromodel."
> — p.602 [pdf 607], 20.6 Developing a Macromodel from the Behavioral Model

> "Even in SPICE-based macromodeling, the top-level schematic circuit of the I/O is considered, and a parameterized template for this class of I/O is developed, using SPICE and IBIS building blocks. Then the parameters are tweaked to model specific parts, and correlated to whatever is considered "golden" data."
> — p.592 [pdf 597], 20.6 Developing a Macromodel from the Behavioral Model

> "Parameter values can be modified and passed into the model. Thus, the model can be tuned to match measured results."
> — p.604 [pdf 609], 20.6 Developing a Macromodel from the Behavioral Model

> "When we simplify the model equations, we give up detail, subtlety, and accuracy."
> — p.590 [pdf 595], 20.6 Developing a Macromodel from the Behavioral Model

**Reading.** p.602-604 describe the Cadence macromodel approach: transistors viewed as controlled current sources replace 'many stages of transistors', and 'the model can be tuned to match measured results'. The book endorses templates tuned to golden data; our gate-tracking test is the check it does not describe, that the tuned template also reproduces the internal node.

### P16 · Exhibit 17: the residual depth rule and the time fence

**Our finding.** Scale the io_buf residual by pad depth and stop it before the pull-down turns on; the pedestal and bump are restored, the deep-stress peak is not.

> "close to the bias conditions where the data was measured. Limitations to vaHd measurements are particularly important in semiconductors because they are usually quite non-linear."
> — p.609 [pdf 614], 20.7 Developing a SPICE Macromodel from a Physical Model.... 592 20.8 Limitations in Models Due to Simplification

> "First, behavioral models are usually accurate only over a narrow range close to their measurement conditions."
> — p.613 [pdf 618], 20.9 AMS Modeling Simplified

**Reading.** No passage on residual scaling. The book's validity-range statements (p.609, p.613) are the general reason a correction fitted at full swing needs a depth term.

## The seven rounds

### R1 · Exhibits 1-2: a short pulse is lost inside the predriver, and the stages are current-limited (ex2), linear (io_buf), or near-linear (inv_chain)

**Our finding.** Probing every node of the transistor: the pulse is lost one stage at a time; each ex2 stage answers a short pulse with less charge than the sum of its step responses.

> "The black-box model can simplify the physical model of the output stage so that we can model driver and pre-driver at a less detailed level."
> — p.580 [pdf 585], 20.5 Behavioral Modeling

> "In these simulations, SPICE models of the driver, pre-driver, clamps, and other portions of the I/O buffers would be used the same way as when generating most IBIS models."
> — p.592 [pdf 597], 20.6 Developing a Macromodel from the Behavioral Model

> "A modern I/O circuit can contain 50 nodes or more for each I/O."
> — p.580 [pdf 585], 20.5 Behavioral Modeling

> "The chain rule states that the overall transfer function can be found by simply multiplying the individual voltage transfer functions together."
> — p.622 [pdf 627], 20.11 Limitations of Deterministic Modeling and Design

> "The chain rule is permissible when the loading of the succeeding stage does not significantly affect the transfer function of the preceding stage."
> — p.622 [pdf 627], 20.11 Limitations of Deterministic Modeling and Design

> "To visuaHze the IBIS driver-switching event, we should think about the IBIS dV/dt data. Figure 11-1 shows a current source charging a capacitor. The voltage is a ramp with a slope of i/C as in: i = C(dV/dt). This C is not identical with Ccomp."
> — p.319 [pdf 329], 11.5 Why We Use the IBIS Model

**Reading.** The book names the pre-driver as part of the SPICE model an IBIS extraction runs (p.592) and says it can be modelled 'at a less detailed level' (p.580). Its chain rule for cascaded stages (p.622) is the linear superposition we tested; its own caveat, that the rule holds only when a stage does not load the one before, is the condition ex2's stages violate. p.319's 'current source charging a capacitor' is the current-limited stage in one sentence.

### R2 · Exhibit 3: Ku and Kd are fixed curves of one gate voltage

**Our finding.** The rising and falling passes through the stressed pulse lie on one curve (loop under 0.1) against the real gate; one node drives both halves on ex2 and inv_chain.

> "For: Forward Region, VDS > 0 ID = 0 For: VGS - VTO < 0 ID=(KP/2) *(W/L) *(VGS- VTEf For:0 < VGS - VTO < VDS"
> — p.89 [pdf 105], 3.7 Examples of Computing Electrical Properties from Structure. 71 3.8 Examples of SPICE Models and Parameters

> "Zero bias threshold"
> — p.88 [pdf 104], 3.7 Examples of Computing Electrical Properties from Structure. 71 3.8 Examples of SPICE Models and Parameters

> "In the case of the I-V data lookup tables, when a given voltage is applied across an output, a particular current results. An approximate answer is that the element acts like a dynamic non-linear resistor."
> — p.299 [pdf 309], 10.5 Schematic of a Basic IBIS Model

> "The behavioral parts of the IBIS model are its I-V data tables (for its dynamic, non-linear impedance behavior) and its V-T data tables (for its dynamic, non-linear switching signal behavior)."
> — p.300 [pdf 310], 10.5 Schematic of a Basic IBIS Model

**Reading.** The SPICE MOSFET equations on p.89 (drain current zero below VTO, then a function of VGS - VT) are the physics of a static map from gate voltage to output current; the I-V table 'acts like a dynamic non-linear resistor' (p.299) and the coefficient is the fraction of it that the gate has opened.

### R3 · Exhibit 4: feed the model the transistor's real gate and the pad follows (within 6 % on ex2, 2 % on io_buf)

**Our finding.** The output-stage half of the model is right; every stressed error was the gate trajectory.

> "Simple systems are easier to understand and learn from. If the objective is to verify a semiconductor model, too much board complexity obscures what is going on with the IC."
> — p.542 [pdf 548], 17.16 Recommended Verification Strategy

> "The proper response to verification problems is to diagnose the cause and improve the results."
> — p.541 [pdf 547], 17.16 Recommended Verification Strategy

> "Golden Waveforms are a set of SPICE waveforms simulated using known real world and ideal (standard) test loads. They are useftil in verifying the accuracy of behavioral simulation results against the SPICE model from which the IBIS model parameters originated."
> — p.381 [pdf 390], 12.9 Tools Provided by the IBIS Committee

**Reading.** The replay is the book's verification advice in miniature: isolate one block so that 'too much complexity' does not obscure what is going on (p.542), diagnose the cause rather than tune around it (p.541), and compare against golden SPICE waveforms (p.381).

### R4 · Exhibits 5-6: the file fixes only the product 'gate trajectory x curve'; a MOSFET-shaped curve breaks the tie

**Our finding.** On a fast chip the IBIS-implied curve is 0.2 of the gate too late; assuming a threshold-plus-power-law curve recovers the gate from the tables to 10 ps.

> "IBIS is a behavioral model The behavior at its input and output pins is described, not what happens between input and output pins."
> — p.301 [pdf 311], 10.6 How IBIS Circuit Modeling Methodology Is Used

> "That balance is accomplished by ignoring the internal behavior of drivers and receivers and by modeling just the behavior at the terminals."
> — p.314 [pdf 324], 10.9 Summary

> "For: Forward Region, VDS > 0 ID = 0 For: VGS - VTO < 0 ID=(KP/2) *(W/L) *(VGS- VTEf For:0 < VGS - VTO < VDS"
> — p.89 [pdf 105], 3.7 Examples of Computing Electrical Properties from Structure. 71 3.8 Examples of SPICE Models and Parameters

> "Buffer switching speed information in the form of output rise and fall ramp rates or V-T rise and fall curves must be supplied. If V-T curves are supplied they supersede the ramp rates."
> — p.273 [pdf 283], 10.2 IBIS Specification

**Reading.** The book defines the limit (only pin behaviour is described, p.301, p.314) and separately gives the MOSFET law (p.89) whose shape is the prior. It never combines the two; the inversion of the tables through the curve is ours.

### R5 · Exhibits 7-8: a current-limited stage fitted at full swing predicts the stressed gate; K identical stages; the chain in ngspice

**Our finding.** Four numbers per stage (two drive rates, a threshold, a resistive fraction) fitted only to the full-swing edge predict ex2's stressed gate within 0.05; the stage count is where the fit stops improving (3 on ex2, 7 on inv_chain).

> "To visuaHze the IBIS driver-switching event, we should think about the IBIS dV/dt data. Figure 11-1 shows a current source charging a capacitor. The voltage is a ramp with a slope of i/C as in: i = C(dV/dt). This C is not identical with Ccomp."
> — p.319 [pdf 329], 11.5 Why We Use the IBIS Model

> "Viewing transistors as current sources allows the replacement of many stages of transistors. A few strategically placed controlled current sources act as the building blocks of a behavioral SPICE-based macromodel."
> — p.602 [pdf 607], 20.6 Developing a Macromodel from the Behavioral Model

> "Even in SPICE-based macromodeling, the top-level schematic circuit of the I/O is considered, and a parameterized template for this class of I/O is developed, using SPICE and IBIS building blocks. Then the parameters are tweaked to model specific parts, and correlated to whatever is considered "golden" data."
> — p.592 [pdf 597], 20.6 Developing a Macromodel from the Behavioral Model

> "It is the same basic philosophy as original IBIS, except the template is not totally "canned" and"
> — p.605 [pdf 610], 20.6 Developing a Macromodel from the Behavioral Model

> "For instance, the transistor-level model may not include certain effects that are readily apparent in a circuit's behavioral data."
> — p.612 [pdf 617], 20.9 AMS Modeling Simplified

**Reading.** p.319 gives the element (a current source into a capacitor makes a ramp) and p.602 the modelling move (controlled current sources standing in for stages of transistors). p.592: a parameterised template for a class of I/O whose parameters are 'tweaked to model specific parts, and correlated to ... golden data' is the recipe. p.612 notes a behavioural model can capture effects 'readily apparent in a circuit's behavioral data' that the transistor-level model misses; here it is the reverse, the tables miss what the transistor shows.

### R6 · Exhibit 9: IBIS file in, one stressed pad run, and eleven of twelve buffers within 10 %

**Our finding.** The stage threshold is the one number not in the file, because no table was recorded with a half-on stage; one stressed pad measurement places it.

> "All V-T tables start at Time = 0.0, since there is only one toggle event in a SPICE V-T simulation."
> — p.407 [pdf 416], 13.3 SPICE-to-IBIS Conversion Methodology

> "A waveform table must include the entire waveform; that is, the first entry (or entries) in a voltage column must be the DC voltage of the output before switching and the last entry (or entries) of the column must be the final DC value of the output after switching."
> — p.122 [pdf 137], 4.5 IBIS Models

> "Parameter values can be modified and passed into the model. Thus, the model can be tuned to match measured results."
> — p.604 [pdf 609], 20.6 Developing a Macromodel from the Behavioral Model

> "Adjusting a template's parameters to match lab results would be much more difficult if important parameters were missing. Missing or wrong parameters can be a result of new or poorly understood physical behavior."
> — p.609 [pdf 614], 20.7 Developing a SPICE Macromodel from a Physical Model.... 592 20.8 Limitations in Models Due to Simplification

> "Golden Waveforms are a set of SPICE waveforms simulated using known real world and ideal (standard) test loads. They are useftil in verifying the accuracy of behavioral simulation results against the SPICE model from which the IBIS model parameters originated."
> — p.381 [pdf 390], 12.9 Tools Provided by the IBIS Committee

> "IBIS 4.1 added support for external models in SPICE 3f5, VHDL-AMS, and Verilog-AMS as well as for "External Models.""
> — p.623 [pdf 628], 20.11 Limitations of Deterministic Modeling and Design

> "Thus, the [External Model] keyword can be used to replace the usual I-V and V-T tables, C_comp, C_comp__pullup, C__comp_pulldown, C_comp_power_clamp, C__comp_gnd_clamp subparameters, [Ramp], [Driver Schedule], [Submodel] keywords, etc. of a [Model] by any modeling technique that the external languages allow."
> — p.628 [pdf 633], 20.11 Limitations of Deterministic Modeling and Design

**Reading.** The file's tables come from one complete toggle (p.407, p.122), so a parameter that only acts on a partial input cannot be in them; p.609 says exactly this from the other side: tuning a template 'would be much more difficult if important parameters were missing'. The book's vehicle for such a model in an IBIS file is [External Model] / [External Circuit] (p.623, p.628), which can replace the tables and ramp 'by any modeling technique'.

### R7 · Exhibit 9b: io_buf, a linear predriver, wants its measured step response

**Our finding.** Every io_buf node sits on the sum of its step responses; the right command is the measured step, which the file-only route cannot supply.

> "The chain rule states that the overall transfer function can be found by simply multiplying the individual voltage transfer functions together."
> — p.622 [pdf 627], 20.11 Limitations of Deterministic Modeling and Design

> "The chain rule is permissible when the loading of the succeeding stage does not significantly affect the transfer function of the preceding stage."
> — p.622 [pdf 627], 20.11 Limitations of Deterministic Modeling and Design

**Reading.** The chain rule on p.622 is superposition of stage transfer functions; io_buf is the case where it holds end to end. The book gives no procedure for a step-response command.

### R8 · Exhibit 10: trains settle; recovery is a third regime and wants one more degree of freedom

**Our finding.** File-only chains are right on pulse 1 and 9-23 % low on the settled train; one resistive fraction cannot set both how much a stage recovers and when it arrives.

> "Also, some Signal Integrity tools do not allow buffers to toggle sooner than the end of the V-T table. In those tools, models created using default V-T end times might not toggle properly."
> — p.402 [pdf 411], 13.3 SPICE-to-IBIS Conversion Methodology

> "Adjusting a template's parameters to match lab results would be much more difficult if important parameters were missing. Missing or wrong parameters can be a result of new or poorly understood physical behavior."
> — p.609 [pdf 614], 20.7 Developing a SPICE Macromodel from a Physical Model.... 592 20.8 Limitations in Models Due to Simplification

> "To keep pace with evolving semiconductor technology, engineers should expect models to evolve. Sometimes laboratory measurements provide the first indication that something new needs to be considered."
> — p.544 [pdf 550], 17.17 Summary

**Reading.** p.402 (toggling before the table ends) is the only place the specification meets a train of short pulses. p.609 and p.544 describe the situation we are in: a parameter missing from the template, discovered because a measurement did not fit.

### R9 · Exhibit 11: Vinh 2.0 V on a 1.8 V part is the IBIS default, and the threshold is a population limit, not the switching point

**Our finding.** inv_chain's file carries Vinh 2.0 / Vinl 0.8 on a 1.8 V supply; the converter's midpoint threshold cut every pulse 29 ps short and hid half the error. The converter now clamps to mid-supply.

> "These model types must have VinI and Vinh defined. If they are not defined, the parser issues a warning and the default values of VinI = 0.8 V and Vinh = 2.0 V are assumed."
> — p.282 [pdf 292], 10.2 IBIS Specification

> "For example, if Vinh and Vinl are omitted from a model, then TTL values are used by default."
> — p.417 [pdf 426], 13.5 IBIS Model Validation

> "Subparameter of [Model] - input threshold - high limit of population (for Input and I/O). Comment: Used to automate flight time measurements."
> — p.289 [pdf 299], 10.3 Sample IBIS Data File

> "Some of the parameters required for an IBIS buffer model are not used in the SPICE simulations. These include Vinh and Vinl, and the fiming conditions (Vmeas, Vref, Rref, and Cref). C comp is also obtained separately."
> — p.406 [pdf 415], 13.3 SPICE-to-IBIS Conversion Methodology

> "When extracting the SPICE simulation results to create an IBIS buffer, we must add data such as Vinh and Vinl."
> — p.400 [pdf 409], 13.3 SPICE-to-IBIS Conversion Methodology

**Reading.** p.282 and p.417: if Vinh/Vinl are not defined, 'the default values of Vinl = 0.8 V and Vinh = 2.0 V are assumed' (TTL). p.289: Vinh is the 'high limit of population', used 'to automate flight time measurements', not a switching threshold. p.400 and p.406: they are entered by hand, not simulated. All three facts are the defect.

### R10 · Exhibit 12: C_comp on nine variants by the loop; declared values are defaults

**Our finding.** The whole ex2 family closes at 1.75-2.0 pF against a declared 5.0; the inv family at 0.3-0.5 against 0.47.

> "Notice that the C_comp parameter of a multi-stage buffer is defined in the top-level model. The value of C_comp therefore includes the total capacitance of the entire buffer, including all of its stages."
> — p.125 [pdf 140], 4.5 IBIS Models

> "The data in the waveform table is taken with the effects of the C_comp parameter included"
> — p.122 [pdf 137], 4.5 IBIS Models

> "Information about such correlation is not available in all cases and C_comp is considered an independent variable. This is because C_comp includes bonding pad capacitance, which does not necessarily track fabrication process variations."
> — p.116 [pdf 131], 4.5 IBIS Models

> "Today, two-thirds to three-fourths of all IBIS models do not work as initially downloaded."
> — p.364 [pdf 373], 12.4 Step 2: Diagnose the Problem's Root Cause

> "Suppliers normally guardband (pad)^ the published data sheet min-max specs on their parameters."
> — p.365 [pdf 374], 12.4 Step 2: Diagnose the Problem's Root Cause

**Reading.** C_comp is the top-level total of all stages (p.125) and is inside the V-T data (p.122), so a wrong declared value is both a wrong pad load and a wrong solve. p.364 and p.365 on model quality and supplier guard-banding explain why a declared value can be a placeholder.

## Open-drain

### OD1 · Open-drain support in the converter: one predriver, one device, the pull-down half of the push-pull machinery

**Our finding.** The two-column open-drain Kd tables are widened with a mirrored placeholder and the gate-state build runs unchanged; no [Pullup] means no branch reads Ku. Rest state and depth dependence are now right.

> "These model types indicate that the output has an OPEN side (do not use the [Pullup] keyword, or if it must be used, set I = 0 mA for all voltages specified) and the output SINKS current. Open_drain model type is retained for backward compatibility."
> — p.282 [pdf 292], 10.2 IBIS Specification

> "Or, as in the case of an open pullup, the pullup element may be missing."
> — p.297 [pdf 307], 10.5 Schematic of a Basic IBIS Model

> "If: The Model_type is either an Open_sink type or Open_drain type; attach either a 50 ohm resistor or the semiconductor vendor suggested termination resistance to either POWER or the suggested termination voltage. Use this load to derive both the rising and falling edges."
> — p.121 [pdf 136], 4.5 IBIS Models

**Reading.** p.282 (no [Pullup] or I = 0, the output sinks current) and p.297 (the pullup element may simply be missing) are the two rules the change relies on; p.121 is the single-load, both-edges characterisation that makes the open-drain a one-fixture solve.

### OD2 · The open-drain NMOS map turns on at 0.2 of its gate swing, not the pull-up's 0.52

**Our finding.** Measured on eight widths: one curve, threshold 0.20, alpha 1.3, saturation 0.88. One prior cannot serve both halves.

> "For: Forward Region, VDS > 0 ID = 0 For: VGS - VTO < 0 ID=(KP/2) *(W/L) *(VGS- VTEf For:0 < VGS - VTO < VDS"
> — p.89 [pdf 105], 3.7 Examples of Computing Electrical Properties from Structure. 71 3.8 Examples of SPICE Models and Parameters

> "Zero bias threshold"
> — p.88 [pdf 104], 3.7 Examples of Computing Electrical Properties from Structure. 71 3.8 Examples of SPICE Models and Parameters

> "The same device operated in low, mid and high currents is then modeled differently based on its use in the circuit."
> — p.620 [pdf 625], 20.10 Limitations Because of Parameter Variation

**Reading.** The MOSFET law (p.89) has its own VTO per device; p.620 notes the same device is 'modeled differently based on its use in the circuit'. The book does not compare NMOS and PMOS maps; the 0.2-versus-0.52 finding is ours.

### OD3 · Fit in the Kd domain, bracket the threshold from the fitted value, use the loop C_comp (3.0 pF)

**Our finding.** Three fitting traps found on the open-drain: the mirrored-Ku fit leaves the onset unconstrained, the excursion is not monotone in the threshold below the fitted value, and the declared 5 pF gives a visibly worse map than 3.0 pF.

> "Since 1 = C*(dV/dt), and C = I/(dV/dt), C_comp is easily found using a voltage ramp. dV is the typical signal swing and dt is the typical transition time. Similarly, values for C comp can be determined for the min and max corner conditions. The current I is not measured instantaneously, but is averaged over a rising and falling ramp. This averages out the voltage dependence of the capacitance just as a signal would see it averaged."
> — p.406 [pdf 415], 13.3 SPICE-to-IBIS Conversion Methodology

> "Sometimes an averaged capacitance is not sufficient (for example, if reflections from a driver or the capacitance varies with driver state, and this is significant in a design). In this case, a table-based IBIS model could be replaced with a SPICE, Verilog-AMS, or VHDL-AMS model."
> — p.406 [pdf 415], 13.3 SPICE-to-IBIS Conversion Methodology

> "The proper response to verification problems is to diagnose the cause and improve the results."
> — p.541 [pdf 547], 17.16 Recommended Verification Strategy

**Reading.** Only the C_comp point has a source: the averaged capacitance of p.406 and its caveat. The fitting traps are method, not physics, and have no counterpart in the book.

## Method

### M1 · Transistor is truth, native IBIS is the bar; whole shapes, not single numbers; back every claim with a figure

**Our finding.** Every comparison is against the HSPICE transistor with the same model card; native HSPICE IBIS is a second model, not a reference. Errors are read along the whole leg and across every width.

> "This accuracy checking is done either directly, or by the substituting a comparison of simulations with a previously hardware verified SPICE model."
> — p.369 [pdf 378], 12.5 Step 3: Design a Fix Based on Root Cause

> "Golden Waveforms are a set of SPICE waveforms simulated using known real world and ideal (standard) test loads. They are useftil in verifying the accuracy of behavioral simulation results against the SPICE model from which the IBIS model parameters originated."
> — p.381 [pdf 390], 12.9 Tools Provided by the IBIS Committee

> "The IBIS Accuracy Handbook uses the absolute error for its "curve overlay metric" FOM (in percent):"
> — p.488 [pdf 494], 16.2 Model Verification Methodology

> "These differences would be significant for verification studies where it is desirable for measured and simulated results to agree within a couple of percent."
> — p.339 [pdf 349], 11.11 Experiment 4: Using V-T Data Versus a Ramp

> "The rule of thumb then was that agreement within an engineering approximation of +/-10% was acceptable."
> — p.545 [pdf 551], 18.1 Establishing Absolute Accuracy Is Difficult

> "This process of observation �> theory -> observation -> theory... continues today as we develop ever-smaller MOSFET geometries and new types of semiconductor devices such as GaAs and SiGe transistors."
> — p.540 [pdf 546], 17.15 How Unexpected Errors Led to an Advance in Modeling

> "His point was to not let theory get one too detached from observation and to not let surprises make you give up the effort."
> — p.540 [pdf 546], 17.15 How Unexpected Errors Led to an Advance in Modeling

> "Simple systems are easier to understand and learn from. If the objective is to verify a semiconductor model, too much board complexity obscures what is going on with the IC."
> — p.542 [pdf 548], 17.16 Recommended Verification Strategy

**Reading.** The book allows verification 'by the substituting a comparison of simulations with a previously hardware verified SPICE model' (p.369) and defines the golden-waveform and curve-overlay comparison (p.381, p.488). Its accuracy expectations (a couple of percent for verification, 10 % as the classic engineering rule, p.339, p.545) bracket our +/-10 % target. Its story of observation leading to a new model (p.540) is the register the investigation followed.

### M2 · What the book does not contain

**Our finding.** For honesty: the switching-coefficient algorithm (Ku, Kd), partial-transition or short-pulse behaviour, predriver stage equations, C_comp hysteresis, and the calibration procedure have no counterpart in the book.

> "Also, some Signal Integrity tools do not allow buffers to toggle sooner than the end of the V-T table. In those tools, models created using default V-T end times might not toggle properly."
> — p.402 [pdf 411], 13.3 SPICE-to-IBIS Conversion Methodology

> "Traditional IBIS modeling is designed to ignore any pass-through, input-output modeling of behavior. But complex I/O requires some modeling of the buffer internal behavior. A new balance between simulation speed and I/O internal modeling will have to be devised."
> — p.580 [pdf 585], 20.5 Behavioral Modeling

**Reading.** The words Ku and Kd never occur; the only mention of an early next edge is p.402; the only mention of internal modelling is the call for it on p.580. The book frames the problem and its rules; the mechanism and the recipe are this project's.
