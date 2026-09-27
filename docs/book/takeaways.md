# Key takeaways from the book

Leventhal & Green, *Semiconductor Modeling* (Springer 2006), the copy in the repository root. Printed page with the PDF page in brackets. Every quote is checked verbatim against `docs/book/pages.json` (OCR spellings kept); the finding-by-finding map is `docs/book/citations.md`.

## Core: how the IBIS model behaves in simulation, against the transistor

1. **The V-T table is replayed as one complete event.** The simulator starts a table at the toggle and plays it to its DC end; there is no representation of a transition that is interrupted part-way.
   > "A waveform table must include the entire waveform; that is, the first entry (or entries) in a voltage column must be the DC voltage of the output before switching and the last entry (or entries) of the column must be the final DC value of the output after switching." — p.122 [pdf 137], §4.5
   > "All V-T tables start at Time = 0.0, since there is only one toggle event in a SPICE V-T simulation." — p.407 [pdf 416], §13.3
   > "Also, some Signal Integrity tools do not allow buffers to toggle sooner than the end of the V-T table. In those tools, models created using default V-T end times might not toggle properly." — p.402 [pdf 411], §13.3

2. **Between events the driver is only its I-V curve.** The tables act during the event; the rest of the time the pad is a static non-linear resistor.
   > "After the switching event is over, the V-T characteristics of the driver do not enter into circuit behavior until another switch event occurs. The driver spends most of its time in the steady-state condition, where subsequent behavior is determined by its I-V curve." — p.301 [pdf 311], §10.6
   > "In the case of the I-V data lookup tables, when a given voltage is applied across an output, a particular current results. An approximate answer is that the element acts like a dynamic non-linear resistor." — p.299 [pdf 309], §10.5

3. **All internal delay is folded into the output cell and shows up as lead-in in the tables.** The simulator has no internal node to interrupt; the predriver is a wait, not a state.
   > "Propagation delay of a buffer is assumed to be entirely due to turn-on and turn-off delay in the output cell itself. Actual flight time from input pin to output pin of a device is assumed to be negligible." — p.354 [pdf 364], §11.14
   > "The first several table entries might be some lead-in time caused by some undefined internal buffer delay before the voltage actually starts transitioning." — p.123 [pdf 138], §4.5
   > "In logic terms, a state-variable change." — p.354 [pdf 364], §11.14

4. **C_comp double-counting check.** The tables were recorded with the pad capacitance in place; a simulator that also loads the pad with C_comp counts it twice. Test: change C_comp and see whether the rise time moves.
   > "It is important to know that the effect of Ccomp on dV/dt or V-T is already included in the dV/dt and V-T data. Wrong answers will be calculated if a simulator uses the Ccomp data as an additional load on the output and adjusts the initial ramp rate accordingly. This will be double-counting the effect of Ccomp." — p.328 [pdf 338], §11.8
   > "If the buffer rise time changes as C_comp is varied, then C_comp may be getting double counted in the simulation." — p.332 [pdf 342], §11.9
   > "The data in the waveform table is taken with the effects of the C_comp parameter included" — p.122 [pdf 137], §4.5

5. **One C_comp for a capacitance that depends on voltage and on buffer state.** A driving buffer and a released one do not present the same capacitance; the file carries one number, averaged over a ramp. (Open-drain into 1 kΩ: the file's 5 pF against a measured 0.2 pF when the NMOS is off.)
   > "Physically, there is capacitance to each DC voltage. This capacitance also varies with voltage, as well as with buffer state (driving high, driving low, or receiving). However, there is only one parameter in the IBIS 3.2 model for this capacitance." — p.405 [pdf 414], §13.3
   > "The current I is not measured instantaneously, but is averaged over a rising and falling ramp." — p.406 [pdf 415], §13.3
   > "values, the value of C_comp is sometimes tweaked to get better agreement between the IBIS model and SPICE and bench measurements." — p.406 [pdf 415], §13.3

6. **The switching ramp is a current source into a capacitor, and that C is not C_comp.** The ramp rate is set by the internal drive, Miller capacitance included.
   > "Figure 11-1 shows a current source charging a capacitor. The voltage is a ramp with a slope of i/C as in: i = C(dV/dt). This C is not identical with Ccomp." — p.319 [pdf 329], §11.5
   > "Actually, the ramp rate is limited by all the internal driver linear and non-linear small-signal and large-signal characteristics, including real and effective reactive elements ... Internal Miller Capacitance [87] also plays a role." — p.319 [pdf 329], §11.5

7. **The initial bump on a CMOS V-T curve is gate-to-pad feedthrough.** A real transistor effect that the table carries only at the width it was recorded.
   > "One also sees a feedforward effect from gate to drain, which is what causes the initial bump sometimes seen in CMOS V-T curves." — p.64 [pdf 80], §3.5
   > "The curves also exhibit an initial peak due to forward voltage coupling caused by the capacitance from the FET gates to the output pad (Cds)." — p.404 [pdf 413], §13.3

8. **Two rising and two falling waveforms are needed; letting the buffer settle can mislead.**
   > "Note: In most cases, two [Rising Waveform] tables and two [Falling Waveform] tables will be necessary for accurate modeling." — p.124 [pdf 139], §4.5
   > "Allowing a buffer to reach quiescent conditions is a lot easier to measure, but this can be misleading in modeling dynamic switching behavior." — p.276 [pdf 286], §10.2

9. **Open-drain is characterised into 50 Ω (or the vendor termination) and will not swing fully into that load.** Whatever the real pull-up is, the tables were taken into that fixture.
   > "If: The Model_type is either an Open_sink type or Open_drain type; attach either a 50 ohm resistor or the semiconductor vendor suggested termination resistance to either POWER or the suggested termination voltage. Use this load to derive both the rising and falling edges." — p.121 [pdf 136], §4.5
   > "Due to the resistor, output swings will not make a full transition as expected." — p.121 [pdf 136], §4.5

10. **Vinh/Vinl are added by hand and default to TTL 0.8/2.0 V; they are population limits, not the switching point.**
    > "These model types must have VinI and Vinh defined. If they are not defined, the parser issues a warning and the default values of VinI = 0.8 V and Vinh = 2.0 V are assumed." — p.282 [pdf 292], §10.2
    > "Some of the parameters required for an IBIS buffer model are not used in the SPICE simulations. These include Vinh and Vinl, and the fiming conditions (Vmeas, Vref, Rref, and Cref). C comp is also obtained separately." — p.406 [pdf 415], §13.3

11. **A behavioural model is valid only near its measurement conditions.** Full-swing tables say nothing about a short pulse or a different load.
    > "First, behavioral models are usually accurate only over a narrow range close to their measurement conditions." — p.613 [pdf 618], §20.9
    > "One challenging aspect of deep sub-sub-micron CMOS technology is that driver behavior is becoming sensitive to loading effects seen at the output terminals of the driver." — p.651 [pdf 655], §22.6

12. **A discrepancy can be the simulator's, not the model's; verify against the golden SPICE waveforms.**
    > "Be aware that not all behavioral and physical simulators are created equal; discrepancies may be an artifact of the simulators rather than the IBIS model extraction process. An example would be double-counting the ramp rate effects of Ccomp." — p.371 [pdf 380], §12.6
    > "Golden Waveforms are a set of SPICE waveforms simulated using known real world and ideal (standard) test loads. They are useftil in verifying the accuracy of behavioral simulation results against the SPICE model from which the IBIS model parameters originated." — p.381 [pdf 390], §12.9

13. **The book itself says the black box will not hold for complex I/O.**
    > "Traditional IBIS modeling is designed to ignore any pass-through, input-output modeling of behavior. But complex I/O requires some modeling of the buffer internal behavior. A new balance between simulation speed and I/O internal modeling will have to be devised." — p.580 [pdf 585], §20.5

## More (the full list, grouped)

## What an IBIS model is

- **IBIS describes the pins, not the inside.** The predriver is not in the file by design; its delay is assumed to sit inside the output cell.
  > "IBIS is a behavioral model The behavior at its input and output pins is described, not what happens between input and output pins." — p.301 [pdf 311], §10.6
  > "Propagation delay of a buffer is assumed to be entirely due to turn-on and turn-off delay in the output cell itself. Actual flight time from input pin to output pin of a device is assumed to be negligible." — p.354 [pdf 364], §11.14

- **The predriver shows up only as lead-in time in the V-T tables.** That is the whole representation of the internal delay: a wait before the pad moves.
  > "The first several table entries might be some lead-in time caused by some undefined internal buffer delay before the voltage actually starts transitioning." — p.123 [pdf 138], §4.5

- **Between switching events the driver is just its I-V curve.** The V-T tables act only during the event.
  > "After the switching event is over, the V-T characteristics of the driver do not enter into circuit behavior until another switch event occurs. The driver spends most of its time in the steady-state condition, where subsequent behavior is determined by its I-V curve." — p.301 [pdf 311], §10.6

- **The book itself says the black box will not hold for complex I/O.**
  > "Traditional IBIS modeling is designed to ignore any pass-through, input-output modeling of behavior. But complex I/O requires some modeling of the buffer internal behavior. A new balance between simulation speed and I/O internal modeling will have to be devised." — p.580 [pdf 585], §20.5

## The V-T tables

- **Every table is one complete transition, from DC to DC, with one toggle.** Nothing in the file describes an interrupted transition.
  > "A waveform table must include the entire waveform; that is, the first entry (or entries) in a voltage column must be the DC voltage of the output before switching and the last entry (or entries) of the column must be the final DC value of the output after switching." — p.122 [pdf 137], §4.5
  > "All V-T tables start at Time = 0.0, since there is only one toggle event in a SPICE V-T simulation." — p.407 [pdf 416], §13.3

- **Toggling before the table ends is a known tool problem.**
  > "Also, some Signal Integrity tools do not allow buffers to toggle sooner than the end of the V-T table. In those tools, models created using default V-T end times might not toggle properly." — p.402 [pdf 411], §13.3

- **Two rising and two falling waveforms are needed.** One waveform per edge is not enough for an accurate model.
  > "Note: In most cases, two [Rising Waveform] tables and two [Falling Waveform] tables will be necessary for accurate modeling." — p.124 [pdf 139], §4.5

- **Letting the buffer settle is convenient for measurement but can mislead about dynamic behaviour.**
  > "The device is allowed to settle to semi- quiescent conditions. Allowing a buffer to reach quiescent conditions is a lot easier to measure, but this can be misleading in modeling dynamic switching behavior." — p.276 [pdf 286], §10.2

- **The initial bump in a CMOS V-T curve is gate-to-pad feedthrough (Miller).**
  > "One also sees a feedforward effect from gate to drain, which is what causes the initial bump sometimes seen in CMOS V-T curves." — p.64 [pdf 80], §3.5
  > "The curves also exhibit an initial peak due to forward voltage coupling caused by the capacitance from the FET gates to the output pad (Cds)." — p.404 [pdf 413], §13.3

- **Ramps are a poor substitute for V-T data; V-T supersedes [Ramp].**
  > "The ramps described by dV/dt can be a good approximation to the rising and falling edge waveforms, but often they are not." — p.278 [pdf 288], §10.2
  > "If V-T curves are supplied they supersede the ramp rates." — p.273 [pdf 283], §10.2

## C_comp

- **C_comp double-counting check.** The V-T tables already contain the effect of C_comp. A simulator that also loads the output with C_comp double-counts it; the test is whether the rise time moves when C_comp is changed.
  > "It is important to know that the effect of Ccomp on dV/dt or V-T is already included in the dV/dt and V-T data. Wrong answers will be calculated if a simulator uses the Ccomp data as an additional load on the output and adjusts the initial ramp rate accordingly. This will be double-counting the effect of Ccomp." — p.328 [pdf 338], §11.8
  > "If the buffer rise time changes as C_comp is varied, then C_comp may be getting double counted in the simulation. In that case, we suggest simulating the rise and fall time of the IBIS test fixture with the correct values of Ccomp entered in min-typ-max. Then, we can observer whether the IBIS slew rate and/or V-T curves can be reproduced." — p.332 [pdf 342], §11.9

- **C_comp is the hardest parameter to get, and one number stands in for a voltage- and state-dependent capacitance.**
  > "Ccomp is one of the most difficult parameters to obtain for an IBIS model." — p.405 [pdf 414], §13.3
  > "Physically, there is capacitance to each DC voltage. This capacitance also varies with voltage, as well as with buffer state (driving high, driving low, or receiving). However, there is only one parameter in the IBIS 3.2 model for this capacitance." — p.405 [pdf 414], §13.3

- **C_comp is measured as an average over a ramp, and vendors tweak it to fit.** So the declared value is not a measurement to trust blindly.
  > "The current I is not measured instantaneously, but is averaged over a rising and falling ramp." — p.406 [pdf 415], §13.3
  > "values, the value of C_comp is sometimes tweaked to get better agreement between the IBIS model and SPICE and bench measurements." — p.406 [pdf 415], §13.3

- **C_comp of a multi-stage buffer is the whole buffer's capacitance, and the waveform tables were taken with it in place.**
  > "Notice that the C_comp parameter of a multi-stage buffer is defined in the top-level model. The value of C_comp therefore includes the total capacitance of the entire buffer, including all of its stages." — p.125 [pdf 140], §4.5
  > "The data in the waveform table is taken with the effects of the C_comp parameter included" — p.122 [pdf 137], §4.5

- **The C in "i = C dV/dt" for the switching ramp is not C_comp.**
  > "Figure 11-1 shows a current source charging a capacitor. The voltage is a ramp with a slope of i/C as in: i = C(dV/dt). This C is not identical with Ccomp." — p.319 [pdf 329], §11.5

## Thresholds and open-drain

- **Vinh/Vinl default to TTL values (0.8 V / 2.0 V) if omitted, regardless of supply.** They are population limits for flight-time measurement, not the switching point.
  > "These model types must have VinI and Vinh defined. If they are not defined, the parser issues a warning and the default values of VinI = 0.8 V and Vinh = 2.0 V are assumed." — p.282 [pdf 292], §10.2
  > "Subparameter of [Model] - input threshold - high limit of population (for Input and I/O). Comment: Used to automate flight time measurements." — p.289 [pdf 299], §10.3

- **Vinh, Vinl and the timing-condition parameters are added by hand; SPICE does not produce them.**
  > "Some of the parameters required for an IBIS buffer model are not used in the SPICE simulations. These include Vinh and Vinl, and the fiming conditions (Vmeas, Vref, Rref, and Cref). C comp is also obtained separately." — p.406 [pdf 415], §13.3

- **Open-drain: no [Pullup] (or all zeros), characterised into 50 Ω or the vendor's termination, and it will not swing fully into that load.**
  > "These model types indicate that the output has an OPEN side (do not use the [Pullup] keyword, or if it must be used, set I = 0 mA for all voltages specified) and the output SINKS current." — p.282 [pdf 292], §10.2
  > "If: The Model_type is either an Open_sink type or Open_drain type; attach either a 50 ohm resistor or the semiconductor vendor suggested termination resistance to either POWER or the suggested termination voltage. Use this load to derive both the rising and falling edges." — p.121 [pdf 136], §4.5
  > "Due to the resistor, output swings will not make a full transition as expected." — p.121 [pdf 136], §4.5

## Validity and verification

- **A behavioural model is only valid near where it was measured.** Full-swing tables say nothing about a short pulse.
  > "First, behavioral models are usually accurate only over a narrow range close to their measurement conditions." — p.613 [pdf 618], §20.9
  > "Limitations to vaHd measurements are particularly important in semiconductors because they are usually quite non-linear." — p.609 [pdf 614], §20.8

- **Verify against golden waveforms from the SPICE model the IBIS came from.** The transistor is the reference, not another IBIS simulator.
  > "Golden Waveforms are a set of SPICE waveforms simulated using known real world and ideal (standard) test loads. They are useftil in verifying the accuracy of behavioral simulation results against the SPICE model from which the IBIS model parameters originated." — p.381 [pdf 390], §12.9

- **Discrepancies can be the simulator's fault, not the model's.** (Native "dead" on finely sampled tables is this case.)
  > "Be aware that not all behavioral and physical simulators are created equal; discrepancies may be an artifact of the simulators rather than the IBIS model extraction process. An example would be double-counting the ramp rate effects of Ccomp." — p.371 [pdf 380], §12.6

- **Most downloaded IBIS models do not work as delivered; check the parameters.**
  > "Today, two-thirds to three-fourths of all IBIS models do not work as initially downloaded." — p.364 [pdf 373], §12.4
  > "For example, if Vinh and Vinl are omitted from a model, then TTL values are used by default." — p.417 [pdf 426], §13.5

- **Keep the verification bench simple; diagnose the cause rather than tune around it.**
  > "Simple systems are easier to understand and learn from. If the objective is to verify a semiconductor model, too much board complexity obscures what is going on with the IC." — p.542 [pdf 548], §17.16
  > "The proper response to verification problems is to diagnose the cause and improve the results." — p.541 [pdf 547], §17.16

- **Accuracy expectations: ±10 % was the old rule of thumb; verification studies want a couple of percent; the IBIS Accuracy Handbook's figure of merit is a curve overlay, not a single number.**
  > "The rule of thumb then was that agreement within an engineering approximation of +/-10% was acceptable." — p.545 [pdf 551], §18.1
  > "These differences would be significant for verification studies where it is desirable for measured and simulated results to agree within a couple of percent." — p.339 [pdf 349], §11.11
  > "The IBIS Accuracy Handbook uses the absolute error for its "curve overlay metric" FOM (in percent):" — p.488 [pdf 494], §16.2

## Macromodels (where the chain sits)

- **A macromodel is a parameterised template of the I/O's top-level schematic, tuned to golden data.** Missing parameters are what makes tuning fail.
  > "Even in SPICE-based macromodeling, the top-level schematic circuit of the I/O is considered, and a parameterized template for this class of I/O is developed, using SPICE and IBIS building blocks. Then the parameters are tweaked to model specific parts, and correlated to whatever is considered "golden" data." — p.592 [pdf 597], §20.6
  > "Adjusting a template's parameters to match lab results would be much more difficult if important parameters were missing. Missing or wrong parameters can be a result of new or poorly understood physical behavior." — p.609 [pdf 614], §20.8

- **Stages of transistors can be replaced by a few controlled current sources.**
  > "Viewing transistors as current sources allows the replacement of many stages of transistors. A few strategically placed controlled current sources act as the building blocks of a behavioral SPICE-based macromodel." — p.602 [pdf 607], §20.6

- **The chain rule holds only when the next stage does not load the previous one.**
  > "The chain rule is permissible when the loading of the succeeding stage does not significantly affect the transfer function of the preceding stage." — p.622 [pdf 627], §20.11

- **The MOSFET law behind the Ku/Kd map** (level-1 forward region).
  > "For: Forward Region, VDS > 0 ID = 0 For: VGS - VTO < 0 ID=(KP/2) *(W/L) *(VGS- VTEf For:0 < VGS - VTO < VDS" — p.89 [pdf 105], §3.8

## What the book does not contain

The book never uses the words Ku or Kd, never discusses a pulse shorter than a transition, has no predriver-stage equations, no C_comp hysteresis, and no calibration procedure. Those parts of the work have no book source.
