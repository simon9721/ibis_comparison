#!/usr/bin/env python3
"""The findings of the stress investigation, each with the passages of Leventhal & Green,
*Semiconductor Modeling* (Springer 2006; `silicon modeling book.pdf`) that bear on it.

Every quote is checked verbatim (whitespace-insensitive) against docs/book/pages.json, so a
citation cannot drift from the text. Output: docs/book/citations.json and citations.md.

    py -3.14 scripts/extract_book_json.py      # once, builds pages.json
    py -3.14 scripts/build_book_citations.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs" / "book"

# --------------------------------------------------------------------------------------- #
# Quotes. key -> (pdf_page, quote). Printed page and section come from pages.json.
# --------------------------------------------------------------------------------------- #
Q = {
    # what IBIS is
    "terminals_only": (324, "That balance is accomplished by ignoring the internal behavior of drivers and receivers and by modeling just the behavior at the terminals."),
    "behavioral_def": (311, "IBIS is a behavioral model The behavior at its input and output pins is described, not what happens between input and output pins."),
    "event_generator": (311, "IBIS assumes that an \"event generator\" tells the output generator/driver to switch and send its signal down a transmission line to a load/receiver."),
    "no_history": (311, "After the switching event is over, the V-T characteristics of the driver do not enter into circuit behavior until another switch event occurs. The driver spends most of its time in the steady-state condition, where subsequent behavior is determined by its I-V curve."),
    "internal_nodes": (273, "Solving a SPICE circuit requires solving all the internal nodes of the SPICE models. Simulation run times increase as the cube of the number of circuit nodes- and a SPICE model can contain over 50 nodes. The workload of simulating a board using the IBIS model is manageable because IBIS models have only three to six internal nodes."),
    "black_boxes": (310, "The difference is that most of the sub-elements of the IBIS model are visualized only as \"black boxes.\""),
    "tables_are_behavior": (310, "The behavioral parts of the IBIS model are its I-V data tables (for its dynamic, non-linear impedance behavior) and its V-T data tables (for its dynamic, non-linear switching signal behavior)."),
    "nonlinear_resistor": (309, "In the case of the I-V data lookup tables, when a given voltage is applied across an output, a particular current results. An approximate answer is that the element acts like a dynamic non-linear resistor."),
    "glossary_behavioral": (711, "Provides data on behavior at the input and output ports of a device. What the device consists of internally remains a black (opaque) box."),
    # the buffer delay assumption
    "buffer_delay_event": (364, "IBIS ignores propagation delay (= flight time) from input to output through an IC device. But the rise and fall times of a buffer (buffer delay) can affect time-of-flight measurements from driver to receiver. An event' occurs that tells the output buffer to turn-on and turn-off. Because of its finite slew rate, the turn-on and turn-off time of a buffer behaves nearly identically with propagation delay. Thus, the term buffer delay."),
    "buffer_delay_assumption": (364, "Propagation delay of a buffer is assumed to be entirely due to turn-on and turn-off delay in the output cell itself. Actual flight time from input pin to output pin of a device is assumed to be negligible."),
    "state_variable": (364, "In logic terms, a state-variable change."),
    "lead_in": (138, "The first several table entries might be some lead-in time caused by some undefined internal buffer delay before the voltage actually starts transitioning."),
    "lead_in_diff": (138, "Any actual device differences in internal buffer delay time between rising and falling edges should appear as differing lead-in times between the rising and the falling waveforms in the tables just as any differences in actual device rise and fall times appear as differing voltage-time entries in the tables."),
    # the ramp as a current source into a capacitor
    "current_source_ramp": (329, "To visuaHze the IBIS driver-switching event, we should think about the IBIS dV/dt data. Figure 11-1 shows a current source charging a capacitor. The voltage is a ramp with a slope of i/C as in: i = C(dV/dt). This C is not identical with Ccomp."),
    "ramp_state_event": (329, "Actually, the ramp rate is limited by all the internal driver linear and non-linear small-signal and large-signal characteristics, including real and effective reactive elements�not just slew-rate rise-time-limited. Internal Miller Capacitance [87] also plays a role. From a simulator point of view, the ramp slew-rate limit is a behavioral model of an internal rise-time-limited component. In any event, something (a state event) switches the output, which then ramps the voltage up depending on this internal drive limit and the loading seen at the driver."),
    "ramp_not_good": (288, "The ramps described by dV/dt can be a good approximation to the rising and falling edge waveforms, but often they are not."),
    "ramp_linear_assumption": (347, "Simplifying assumptions are made when the dV/dt of the rising and falling waveforms of a driver are used in simulations. The assumption is made that the waveforms are linear (straight lines) from 0% to 100% of the output swing."),
    "soft_turnon_slew": (303, "This is particularly seen in bus drivers that have been designed to avoid such reflections by having soft turnon and turnoff (example GTLP). The behavior of such devices in complex topologies cannot be modeled by simple slew rate information."),
    # V-T tables: full transitions from rest
    "entire_waveform": (137, "A waveform table must include the entire waveform; that is, the first entry (or entries) in a voltage column must be the DC voltage of the output before switching and the last entry (or entries) of the column must be the final DC value of the output after switching."),
    "one_toggle": (416, "All V-T tables start at Time = 0.0, since there is only one toggle event in a SPICE V-T simulation."),
    "toggle_sooner": (411, "Also, some Signal Integrity tools do not allow buffers to toggle sooner than the end of the V-T table. In those tools, models created using default V-T end times might not toggle properly."),
    "settle_before_end": (411, "First, the slowest transition needs to settle before the end of the simulation time."),
    "two_tables": (139, "Note: In most cases, two [Rising Waveform] tables and two [Falling Waveform] tables will be necessary for accurate modeling."),
    "four_vt_sims": (410, "Vpad vs. Time (data rising, R_fixture to Vcc) Vpad vs. Time (data falling, R_fixture to Vcc) Vpad vs. Time (data rising, R fixture to GND) Vpad vs. Time (data falling, R_fixture to GND)"),
    "vt_supersede": (283, "Buffer switching speed information in the form of output rise and fall ramp rates or V-T rise and fall curves must be supplied. If V-T curves are supplied they supersede the ramp rates."),
    "quiescent_misleading": (286, "The device is allowed to settle to semi- quiescent conditions. Allowing a buffer to reach quiescent conditions is a lot easier to measure, but this can be misleading in modeling dynamic switching behavior."),
    # C_comp
    "ccomp_independent": (131, "Information about such correlation is not available in all cases and C_comp is considered an independent variable. This is because C_comp includes bonding pad capacitance, which does not necessarily track fabrication process variations."),
    "ccomp_all_stages": (140, "Notice that the C_comp parameter of a multi-stage buffer is defined in the top-level model. The value of C_comp therefore includes the total capacitance of the entire buffer, including all of its stages."),
    "ccomp_included_in_vt": (137, "The data in the waveform table is taken with the effects of the C_comp parameter included"),
    "ccomp_difficult": (414, "Ccomp is one of the most difficult parameters to obtain for an IBIS model. C_comp is the effective loading capacitance for signal reflections at the I/O pad for a driver or receiver. This is greater than the fixed wiring capacitance at the pad, since it also includes junction capacitances."),
    "ccomp_varies": (414, "Physically, there is capacitance to each DC voltage. This capacitance also varies with voltage, as well as with buffer state (driving high, driving low, or receiving). However, there is only one parameter in the IBIS 3.2 model for this capacitance."),
    "ccomp_tweaked": (415, "values, the value of C_comp is sometimes tweaked to get better agreement between the IBIS model and SPICE and bench measurements."),
    "ccomp_measure": (415, "Since 1 = C*(dV/dt), and C = I/(dV/dt), C_comp is easily found using a voltage ramp. dV is the typical signal swing and dt is the typical transition time. Similarly, values for C comp can be determined for the min and max corner conditions. The current I is not measured instantaneously, but is averaged over a rising and falling ramp. This averages out the voltage dependence of the capacitance just as a signal would see it averaged."),
    "ccomp_averaged_insufficient": (415, "Sometimes an averaged capacitance is not sufficient (for example, if reflections from a driver or the capacitance varies with driver state, and this is significant in a design). In this case, a table-based IBIS model could be replaced with a SPICE, Verilog-AMS, or VHDL-AMS model."),
    "ccomp_double_count": (338, "It is important to know that the effect of Ccomp on dV/dt or V-T is already included in the dV/dt and V-T data. Wrong answers will be calculated if a simulator uses the Ccomp data as an additional load on the output and adjusts the initial ramp rate accordingly. This will be double-counting the effect of Ccomp."),
    "ccomp_sets_ramp": (338, "The setting of ramp rate out of a driver."),
    "ccomp_test": (342, "If the buffer rise time changes as C_comp is varied, then C_comp may be getting double counted in the simulation. In that case, we suggest simulating the rise and fall time of the IBIS test fixture with the correct values of Ccomp entered in min-typ-max. Then, we can observer whether the IBIS slew rate and/or V-T curves can be reproduced."),
    "ccomp_interdependent": (341, "But in a real device, C comp will be interdependent with slew rate. So from this manipulation, we can only draw general conclusions."),
    "pad_capacitance": (407, "The netlist used to generate IBIS model data must also include all of the capacitance loading on the output pad of the buffer. Total pad capacitances of 2-5 pF are not uncommon. Some of this capacitance comes from the transistor and diode capacitances, which are nonnally included in the SPICE models for these devices. Because the output drive transistors are relatively large, their capacitance is usually large."),
    # Miller / feedforward
    "miller_bump": (80, "One also sees a feedforward effect from gate to drain, which is what causes the initial bump sometimes seen in CMOS V-T curves."),
    "cds_peak": (413, "The curves also exhibit an initial peak due to forward voltage coupling caused by the capacitance from the FET gates to the output pad (Cds)."),
    # Vinh / Vinl
    "vinh_defaults": (292, "These model types must have VinI and Vinh defined. If they are not defined, the parser issues a warning and the default values of VinI = 0.8 V and Vinh = 2.0 V are assumed."),
    "vinh_population": (299, "Subparameter of [Model] - input threshold - high limit of population (for Input and I/O). Comment: Used to automate flight time measurements."),
    "vinh_manual": (415, "Some of the parameters required for an IBIS buffer model are not used in the SPICE simulations. These include Vinh and Vinl, and the fiming conditions (Vmeas, Vref, Rref, and Cref). C comp is also obtained separately."),
    "vinh_ttl_default": (426, "For example, if Vinh and Vinl are omitted from a model, then TTL values are used by default."),
    "vinh_added": (409, "When extracting the SPICE simulation results to create an IBIS buffer, we must add data such as Vinh and Vinl."),
    # open drain
    "od_type": (284, "Open-drain: This is a type of output driver model with an open pullup side. This name is retained for backward compatibility."),
    "od_rules": (292, "These model types indicate that the output has an OPEN side (do not use the [Pullup] keyword, or if it must be used, set I = 0 mA for all voltages specified) and the output SINKS current. Open_drain model type is retained for backward compatibility."),
    "od_ramp_load": (136, "If: The Model_type is either an Open_sink type or Open_drain type; attach either a 50 ohm resistor or the semiconductor vendor suggested termination resistance to either POWER or the suggested termination voltage. Use this load to derive both the rising and falling edges."),
    "od_no_full_swing": (136, "Due to the resistor, output swings will not make a full transition as expected."),
    "open_pullup_missing": (307, "Or, as in the case of an open pullup, the pullup element may be missing."),
    # MOSFET physics
    "mosfet_eq": (105, "For: Forward Region, VDS > 0 ID = 0 For: VGS - VTO < 0 ID=(KP/2) *(W/L) *(VGS- VTEf For:0 < VGS - VTO < VDS"),
    "mosfet_params": (104, "Zero bias threshold"),
    "modeled_by_use": (625, "The same device operated in low, mid and high currents is then modeled differently based on its use in the circuit."),
    # pre-driver and internal modelling
    "predriver_less_detail": (585, "The black-box model can simplify the physical model of the output stage so that we can model driver and pre-driver at a less detailed level."),
    "pass_through": (585, "Traditional IBIS modeling is designed to ignore any pass-through, input-output modeling of behavior. But complex I/O requires some modeling of the buffer internal behavior. A new balance between simulation speed and I/O internal modeling will have to be devised."),
    "io_50_nodes": (585, "A modern I/O circuit can contain 50 nodes or more for each I/O."),
    "predriver_spice": (597, "In these simulations, SPICE models of the driver, pre-driver, clamps, and other portions of the I/O buffers would be used the same way as when generating most IBIS models."),
    "template_correlated": (597, "Even in SPICE-based macromodeling, the top-level schematic circuit of the I/O is considered, and a parameterized template for this class of I/O is developed, using SPICE and IBIS building blocks. Then the parameters are tweaked to model specific parts, and correlated to whatever is considered \"golden\" data."),
    "transistors_as_current_sources": (607, "Viewing transistors as current sources allows the replacement of many stages of transistors. A few strategically placed controlled current sources act as the building blocks of a behavioral SPICE-based macromodel."),
    "template_tuned": (609, "Parameter values can be modified and passed into the model. Thus, the model can be tuned to match measured results."),
    "template_vs_ibis": (610, "It is the same basic philosophy as original IBIS, except the template is not totally \"canned\" and"),
    "simplify_gives_up": (595, "When we simplify the model equations, we give up detail, subtlety, and accuracy."),
    "chain_rule": (627, "The chain rule states that the overall transfer function can be found by simply multiplying the individual voltage transfer functions together."),
    "chain_rule_loading": (627, "The chain rule is permissible when the loading of the succeeding stage does not significantly affect the transfer function of the preceding stage."),
    "driver_schedule": (629, "[Driver Schedule] Describes the relative model switching sequence for referenced models to produce a multi-staged driver."),
    "external_models": (628, "IBIS 4.1 added support for external models in SPICE 3f5, VHDL-AMS, and Verilog-AMS as well as for \"External Models.\""),
    "external_replaces": (633, "Thus, the [External Model] keyword can be used to replace the usual I-V and V-T tables, C_comp, C_comp__pullup, C__comp_pulldown, C_comp_power_clamp, C__comp_gnd_clamp subparameters, [Ramp], [Driver Schedule], [Submodel] keywords, etc. of a [Model] by any modeling technique that the external languages allow."),
    # model validity, verification, missing parameters
    "valid_near_measured": (613, "Measurement-based behavioral models are only valid"),
    "valid_near_measured2": (614, "close to the bias conditions where the data was measured. Limitations to vaHd measurements are particularly important in semiconductors because they are usually quite non-linear."),
    "narrow_range": (618, "First, behavioral models are usually accurate only over a narrow range close to their measurement conditions."),
    "missing_parameters": (614, "Adjusting a template's parameters to match lab results would be much more difficult if important parameters were missing. Missing or wrong parameters can be a result of new or poorly understood physical behavior."),
    "behavioral_can_beat": (617, "For instance, the transistor-level model may not include certain effects that are readily apparent in a circuit's behavioral data."),
    "golden_waveforms": (390, "Golden Waveforms are a set of SPICE waveforms simulated using known real world and ideal (standard) test loads. They are useftil in verifying the accuracy of behavioral simulation results against the SPICE model from which the IBIS model parameters originated."),
    "fom": (494, "The IBIS Accuracy Handbook uses the absolute error for its \"curve overlay metric\" FOM (in percent):"),
    "verify_simple_board": (548, "Simple systems are easier to understand and learn from. If the objective is to verify a semiconductor model, too much board complexity obscures what is going on with the IC."),
    "diagnose": (547, "The proper response to verification problems is to diagnose the cause and improve the results."),
    "observation_theory": (546, "This process of observation �> theory -> observation -> theory... continues today as we develop ever-smaller MOSFET geometries and new types of semiconductor devices such as GaAs and SiGe transistors."),
    "surprises": (546, "His point was to not let theory get one too detached from observation and to not let surprises make you give up the effort."),
    "verification_hardware_spice": (378, "This accuracy checking is done either directly, or by the substituting a comparison of simulations with a previously hardware verified SPICE model."),
    "few_percent": (349, "These differences would be significant for verification studies where it is desirable for measured and simulated results to agree within a couple of percent."),
    "ten_percent": (551, "The rule of thumb then was that agreement within an engineering approximation of +/-10% was acceptable."),
    "models_evolve": (550, "To keep pace with evolving semiconductor technology, engineers should expect models to evolve. Sometimes laboratory measurements provide the first indication that something new needs to be considered."),
    "two_thirds_broken": (373, "Today, two-thirds to three-fourths of all IBIS models do not work as initially downloaded."),
    "guardband": (374, "Suppliers normally guardband (pad)^ the published data sheet min-max specs on their parameters."),
    "vt_beats_ramp": (356, "So with a more complex topology, a more sophisticated and correct model of the V-T behavior makes a big difference in results."),
    "sensitive_loading": (655, "One challenging aspect of deep sub-sub-micron CMOS technology is that driver behavior is becoming sensitive to loading effects seen at the output terminals of the driver."),
}

# --------------------------------------------------------------------------------------- #
# Findings -> citations. Each finding: id, group, title, our finding (one or two sentences),
# quotes (keys), and 'reading': what the passage does and does not support.
# --------------------------------------------------------------------------------------- #
FINDINGS = [
    # ---------------- the frame
    dict(id="F0", group="Frame", title="What an IBIS model is, and what it leaves out",
         ours="Every stressed error on twelve buffers traced to the gate driver (the predriver), which the IBIS file does not describe. The model has a static output stage and, until this work, no internal state between the input pin and the pad.",
         quotes=["terminals_only", "behavioral_def", "internal_nodes", "black_boxes", "glossary_behavioral", "pass_through"],
         reading="The book states the design intent we ran into: IBIS describes behaviour at the pins and nothing between them (p.301, p.314), a SPICE buffer has 50+ nodes where IBIS has three to six (p.263), and complex I/O 'requires some modeling of the buffer internal behavior' (p.580). Our predriver chain is that internal modelling."),
    dict(id="F0b", group="Frame", title="The assumption the whole investigation overturned: the predriver's delay is folded into the output cell",
         ours="The V-T tables carry the predriver only as a dead time before the pad moves. Under a short pulse the real predriver is a chain of stages that is interrupted mid-travel; a delay cannot be interrupted, so the model turns fully on at every width.",
         quotes=["buffer_delay_event", "buffer_delay_assumption", "state_variable", "lead_in", "lead_in_diff", "event_generator"],
         reading="p.354 is the book's explicit statement of the assumption: propagation through the device is 'entirely due to turn-on and turn-off delay in the output cell itself', triggered by an 'event' (a state-variable change). p.123 says the table's lead-in is 'some undefined internal buffer delay'. This is exactly why adding the table delay back cannot reproduce a partial pulse: the book's model has an event and a delay, not a mechanism that can be caught half way."),

    # ---------------- before the rounds (page 1 exhibits)
    dict(id="P1", group="Before the rounds", title="Exhibit 1: the timing shift splits into an accumulating part and a stress pedestal",
         ours="Native and our model share an outward, accumulating lateness; a fixed pedestal appears only when the pulse is cut short and is ours alone.",
         quotes=["no_history", "buffer_delay_assumption"],
         reading="p.301: once a switching event is over the V-T data 'do not enter into circuit behavior until another switch event occurs'. A table replay therefore has no notion of an interrupted transition, which is the pedestal. The book does not discuss short pulses; it supports the diagnosis by describing the machinery."),
    dict(id="P2", group="Before the rounds", title="Exhibit 2: the accumulating part scales with C_comp, and the declared value is not trustworthy",
         ours="The outward lateness is the pad capacitor; io_buf closes at 0.3 pF, not the declared 1.2 pF. Later: the whole ex2 family closes at 1.75 to 2.0 pF against a declared 5.0.",
         quotes=["ccomp_independent", "ccomp_difficult", "ccomp_varies", "ccomp_tweaked", "ccomp_measure", "ccomp_averaged_insufficient", "pad_capacitance"],
         reading="The book says C_comp is 'one of the most difficult parameters to obtain', an effective, voltage- and state-dependent quantity that 'is sometimes tweaked' (p.405-406), an 'independent variable' that includes the bond pad (p.116), typically 2-5 pF (p.398). Our loop method is a dynamic version of the I = C dV/dt extraction on p.406; the book's caveat that an averaged capacitance is sometimes not sufficient matches the 1.75 versus 3.0 pF gap between the two solves."),
    dict(id="P3", group="Before the rounds", title="Exhibit 3: three dead ends closed (stranded command charge, the gate as a stopwatch, the restore gate)",
         ours="None of the three mechanisms inside the command layer explains the pedestal; the residual does.",
         quotes=["ramp_state_event", "current_source_ramp"],
         reading="p.319 is the closest the book comes to a mechanism: 'something (a state event) switches the output, which then ramps'. It names no internal state beyond the event, so nothing in the book predicts or excludes these mechanisms; the passage only confirms that the replay layer is stateless by design."),
    dict(id="P4", group="Before the rounds", title="Exhibit 4: the stressed pad and its coefficients; two-fixture solve",
         ours="Ku and Kd are solved from the transistor's two fixture runs; both IBIS models cut the pull-up short and turn the pull-down on late under stress.",
         quotes=["two_tables", "four_vt_sims", "tables_are_behavior"],
         reading="The book gives the two-fixture requirement (two rising and two falling tables, p.124; the four V-T simulations to Vcc and GND, p.401) without the switching-coefficient algebra. The term Ku/Kd does not appear anywhere in the book; the coefficient view is ours, built on the book's tables."),
    dict(id="P5", group="Before the rounds", title="Exhibit 5: coefficients solved within ~90 ps of a reversal are unusable; the Miller bump",
         ours="Within 80-90 ps of the reversal the solved Ku/Kd spike, not from ill-conditioning but because both fixtures are not in the same internal state mid-reversal. Every window starts at +90 ps.",
         quotes=["miller_bump", "cds_peak", "ramp_state_event"],
         reading="The book attributes the 'initial bump sometimes seen in CMOS V-T curves' to gate-to-drain feedforward (p.64) and the 'initial peak' in extracted V-T curves to gate-to-pad capacitance (p.404): the same Miller coupling that puts the transistor's Ku above 1 at the falling edge and spoils the solve at the reversal."),
    dict(id="P6", group="Before the rounds", title="Exhibit 6: the pedestal is the Kd residual, calibrated on a complete transition and applied to a truncated one",
         ours="The residual term reproduces a full edge and is 2 to 2.5 times too large on a partial one; scaling it by depth removes the pedestal.",
         quotes=["entire_waveform", "one_toggle", "settle_before_end", "quiescent_misleading"],
         reading="p.122 and p.407: a table 'must include the entire waveform' from one DC level to the other, and there is 'only one toggle event in a SPICE V-T simulation'. Everything the file knows is a complete transition from rest, which is why anything derived from it is calibrated for a complete transition. p.276 warns that quiescent characterisation 'can be misleading in modeling dynamic switching behavior'."),
    dict(id="P7", group="Before the rounds", title="Exhibit 7: the +1.8 ns pull-down turn-on bump is a marker the model cannot move",
         ours="The transistor's bump arrives earlier the shorter the pulse; ours does not move because it has no gate state to move it.",
         quotes=["buffer_delay_event", "no_history"],
         reading="No passage on this event. The book's turn-on/turn-off as an 'event' with a delay (p.354) is the reason the bump is fixed in our model; the book does not discuss a stress-dependent turn-on."),
    dict(id="P8", group="Before the rounds", title="Exhibit 8: pu_off cannot be derived; one parameter, two jobs",
         ours="The coefficient error and the amplitude error fall in opposite directions with the delay scale; no value serves both.",
         quotes=["ramp_not_good", "ramp_linear_assumption", "soft_turnon_slew", "simplify_gives_up"],
         reading="The book's recurring point is that a single slew or delay number cannot carry the shape of a transition (p.278, p.337, p.293), and that simplifying a model 'gives up detail, subtlety, and accuracy' (p.590). Our result is the same statement one level up: one delay cannot carry both the timing and the amount of a partial transition."),
    dict(id="P9", group="Before the rounds", title="Exhibit 9: the transistor's Ku overshoots at full swing; native's stored trajectory equals our solve",
         ours="Ku rises to 1.15-1.2 at the falling edge on both the transistor and native; our two-fixture solve reproduces native's stored St on all four edges.",
         quotes=["miller_bump", "cds_peak", "golden_waveforms", "fom"],
         reading="Miller feedforward (p.64, p.404) is the physics of the overshoot. Comparing our extraction against native's stored trajectory is the book's golden-waveform idea (p.381) applied to coefficients rather than pads; the curve-overlay figure of merit (p.488) is the same kind of comparison."),
    dict(id="P10", group="Before the rounds", title="Exhibit 10: twelve buffers, two regimes",
         ours="Eleven buffers enter the reversal fully on (native too); io_buf alone is in the residual regime. Full-swing tables fit all twelve equally and say nothing about which regime a buffer is in.",
         quotes=["valid_near_measured", "valid_near_measured2", "narrow_range", "sensitive_loading"],
         reading="p.608-609 and p.613: measurement-based behavioural models are 'only valid close to the bias conditions where the data was measured' and 'accurate only over a narrow range close to their measurement conditions'. A short pulse is outside the measured condition (a complete transition), which is the regime problem in the book's own terms."),
    dict(id="P11", group="Before the rounds", title="Exhibit 11: Ku is a static map of the real gate, and the loop measures C_comp",
         ours="Ku against the real gate voltage is single-valued once the solve uses the right C_comp; the C_comp that closes the loop is the pad's effective capacitance (ex2 1.75 pF, declared 5).",
         quotes=["mosfet_eq", "nonlinear_resistor", "ccomp_measure", "ccomp_varies"],
         reading="The MOSFET equations (3-23)-(3-26) on p.89 make the drain current a function of gate voltage and drain voltage only, which is the static map. The loop method is the book's C = I/(dV/dt) extraction (p.406) made self-consistent: the value that makes the map single-valued."),
    dict(id="P12", group="Before the rounds", title="Exhibit 12: correcting C_comp alone makes ex2 worse (negative result)",
         ours="The declared 5 pF was compensating a third of the gate-timing error; the true 1.7 pF exposes it.",
         quotes=["ccomp_tweaked", "ccomp_double_count", "ccomp_test", "ccomp_interdependent"],
         reading="p.406 admits C_comp 'is sometimes tweaked to get better agreement'; p.328-332 explain that C_comp sets the ramp rate and is already inside the V-T data, and that changing it must not change the edge if the model is consistent. Our negative result is that consistency check failing: the right C_comp changed the edge, so something else (the gate) was wrong."),
    dict(id="P13", group="Before the rounds", title="Exhibit 13: a stressed train, nothing accumulates, but pulse 1 differs from the rest",
         ours="Errors re-settle within three pulses; a pulse arriving before the stages have returned to rest behaves differently (the recovery regime).",
         quotes=["toggle_sooner", "no_history", "one_toggle"],
         reading="p.402 is the book's only reference to a next edge arriving early: some tools 'do not allow buffers to toggle sooner than the end of the V-T table'. The specification has no concept of a pulse arriving before the previous transition has completed, which is why recovery is a third regime the file cannot pin."),
    dict(id="P14", group="Before the rounds", title="Exhibit 14: open-drain shows the stress law bare",
         ours="Kd at the pad minimum is linear in depth and the real gate tracks depth on all three open-drains; both IBIS models pull all the way down at every width.",
         quotes=["od_type", "od_rules", "od_ramp_load", "od_no_full_swing", "open_pullup_missing"],
         reading="The book gives the open-drain rules we used: no [Pullup] table, the output sinks current (p.282), the switching data taken with a 50 ohm resistor to POWER for both edges (p.121), and that 'output swings will not make a full transition' with the resistor (p.121). Nothing on its stressed behaviour."),
    dict(id="P15", group="Before the rounds", title="Exhibits 15-16: the slow-gate and cascade prototypes fix the pad without the gate",
         ours="A slow RC gate and a cascade of RC stages reproduce the stressed pad on ex2 but with the wrong internal gate: a fit, not a mechanism.",
         quotes=["transistors_as_current_sources", "template_correlated", "template_tuned", "simplify_gives_up"],
         reading="p.602-604 describe the Cadence macromodel approach: transistors viewed as controlled current sources replace 'many stages of transistors', and 'the model can be tuned to match measured results'. The book endorses templates tuned to golden data; our gate-tracking test is the check it does not describe, that the tuned template also reproduces the internal node."),
    dict(id="P16", group="Before the rounds", title="Exhibit 17: the residual depth rule and the time fence",
         ours="Scale the io_buf residual by pad depth and stop it before the pull-down turns on; the pedestal and bump are restored, the deep-stress peak is not.",
         quotes=["valid_near_measured2", "narrow_range"],
         reading="No passage on residual scaling. The book's validity-range statements (p.609, p.613) are the general reason a correction fitted at full swing needs a depth term."),

    # ---------------- the seven rounds (page 2 exhibits)
    dict(id="R1", group="The seven rounds", title="Exhibits 1-2: a short pulse is lost inside the predriver, and the stages are current-limited (ex2), linear (io_buf), or near-linear (inv_chain)",
         ours="Probing every node of the transistor: the pulse is lost one stage at a time; each ex2 stage answers a short pulse with less charge than the sum of its step responses.",
         quotes=["predriver_less_detail", "predriver_spice", "io_50_nodes", "chain_rule", "chain_rule_loading", "current_source_ramp"],
         reading="The book names the pre-driver as part of the SPICE model an IBIS extraction runs (p.592) and says it can be modelled 'at a less detailed level' (p.580). Its chain rule for cascaded stages (p.622) is the linear superposition we tested; its own caveat, that the rule holds only when a stage does not load the one before, is the condition ex2's stages violate. p.319's 'current source charging a capacitor' is the current-limited stage in one sentence."),
    dict(id="R2", group="The seven rounds", title="Exhibit 3: Ku and Kd are fixed curves of one gate voltage",
         ours="The rising and falling passes through the stressed pulse lie on one curve (loop under 0.1) against the real gate; one node drives both halves on ex2 and inv_chain.",
         quotes=["mosfet_eq", "mosfet_params", "nonlinear_resistor", "tables_are_behavior"],
         reading="The SPICE MOSFET equations on p.89 (drain current zero below VTO, then a function of VGS - VT) are the physics of a static map from gate voltage to output current; the I-V table 'acts like a dynamic non-linear resistor' (p.299) and the coefficient is the fraction of it that the gate has opened."),
    dict(id="R3", group="The seven rounds", title="Exhibit 4: feed the model the transistor's real gate and the pad follows (within 6 % on ex2, 2 % on io_buf)",
         ours="The output-stage half of the model is right; every stressed error was the gate trajectory.",
         quotes=["verify_simple_board", "diagnose", "golden_waveforms"],
         reading="The replay is the book's verification advice in miniature: isolate one block so that 'too much complexity' does not obscure what is going on (p.542), diagnose the cause rather than tune around it (p.541), and compare against golden SPICE waveforms (p.381)."),
    dict(id="R4", group="The seven rounds", title="Exhibits 5-6: the file fixes only the product 'gate trajectory x curve'; a MOSFET-shaped curve breaks the tie",
         ours="On a fast chip the IBIS-implied curve is 0.2 of the gate too late; assuming a threshold-plus-power-law curve recovers the gate from the tables to 10 ps.",
         quotes=["behavioral_def", "terminals_only", "mosfet_eq", "vt_supersede"],
         reading="The book defines the limit (only pin behaviour is described, p.301, p.314) and separately gives the MOSFET law (p.89) whose shape is the prior. It never combines the two; the inversion of the tables through the curve is ours."),
    dict(id="R5", group="The seven rounds", title="Exhibits 7-8: a current-limited stage fitted at full swing predicts the stressed gate; K identical stages; the chain in ngspice",
         ours="Four numbers per stage (two drive rates, a threshold, a resistive fraction) fitted only to the full-swing edge predict ex2's stressed gate within 0.05; the stage count is where the fit stops improving (3 on ex2, 7 on inv_chain).",
         quotes=["current_source_ramp", "transistors_as_current_sources", "template_correlated", "template_vs_ibis", "behavioral_can_beat"],
         reading="p.319 gives the element (a current source into a capacitor makes a ramp) and p.602 the modelling move (controlled current sources standing in for stages of transistors). p.592: a parameterised template for a class of I/O whose parameters are 'tweaked to model specific parts, and correlated to ... golden data' is the recipe. p.612 notes a behavioural model can capture effects 'readily apparent in a circuit's behavioral data' that the transistor-level model misses; here it is the reverse, the tables miss what the transistor shows."),
    dict(id="R6", group="The seven rounds", title="Exhibit 9: IBIS file in, one stressed pad run, and eleven of twelve buffers within 10 %",
         ours="The stage threshold is the one number not in the file, because no table was recorded with a half-on stage; one stressed pad measurement places it.",
         quotes=["one_toggle", "entire_waveform", "template_tuned", "missing_parameters", "golden_waveforms", "external_models", "external_replaces"],
         reading="The file's tables come from one complete toggle (p.407, p.122), so a parameter that only acts on a partial input cannot be in them; p.609 says exactly this from the other side: tuning a template 'would be much more difficult if important parameters were missing'. The book's vehicle for such a model in an IBIS file is [External Model] / [External Circuit] (p.623, p.628), which can replace the tables and ramp 'by any modeling technique'."),
    dict(id="R7", group="The seven rounds", title="Exhibit 9b: io_buf, a linear predriver, wants its measured step response",
         ours="Every io_buf node sits on the sum of its step responses; the right command is the measured step, which the file-only route cannot supply.",
         quotes=["chain_rule", "chain_rule_loading"],
         reading="The chain rule on p.622 is superposition of stage transfer functions; io_buf is the case where it holds end to end. The book gives no procedure for a step-response command."),
    dict(id="R8", group="The seven rounds", title="Exhibit 10: trains settle; recovery is a third regime and wants one more degree of freedom",
         ours="File-only chains are right on pulse 1 and 9-23 % low on the settled train; one resistive fraction cannot set both how much a stage recovers and when it arrives.",
         quotes=["toggle_sooner", "missing_parameters", "models_evolve"],
         reading="p.402 (toggling before the table ends) is the only place the specification meets a train of short pulses. p.609 and p.544 describe the situation we are in: a parameter missing from the template, discovered because a measurement did not fit."),
    dict(id="R9", group="The seven rounds", title="Exhibit 11: Vinh 2.0 V on a 1.8 V part is the IBIS default, and the threshold is a population limit, not the switching point",
         ours="inv_chain's file carries Vinh 2.0 / Vinl 0.8 on a 1.8 V supply; the converter's midpoint threshold cut every pulse 29 ps short and hid half the error. The converter now clamps to mid-supply.",
         quotes=["vinh_defaults", "vinh_ttl_default", "vinh_population", "vinh_manual", "vinh_added"],
         reading="p.282 and p.417: if Vinh/Vinl are not defined, 'the default values of Vinl = 0.8 V and Vinh = 2.0 V are assumed' (TTL). p.289: Vinh is the 'high limit of population', used 'to automate flight time measurements', not a switching threshold. p.400 and p.406: they are entered by hand, not simulated. All three facts are the defect."),
    dict(id="R10", group="The seven rounds", title="Exhibit 12: C_comp on nine variants by the loop; declared values are defaults",
         ours="The whole ex2 family closes at 1.75-2.0 pF against a declared 5.0; the inv family at 0.3-0.5 against 0.47.",
         quotes=["ccomp_all_stages", "ccomp_included_in_vt", "ccomp_independent", "two_thirds_broken", "guardband"],
         reading="C_comp is the top-level total of all stages (p.125) and is inside the V-T data (p.122), so a wrong declared value is both a wrong pad load and a wrong solve. p.364 and p.365 on model quality and supplier guard-banding explain why a declared value can be a placeholder."),

    # ---------------- open-drain
    dict(id="OD1", group="Open-drain", title="Open-drain support in the converter: one predriver, one device, the pull-down half of the push-pull machinery",
         ours="The two-column open-drain Kd tables are widened with a mirrored placeholder and the gate-state build runs unchanged; no [Pullup] means no branch reads Ku. Rest state and depth dependence are now right.",
         quotes=["od_rules", "open_pullup_missing", "od_ramp_load"],
         reading="p.282 (no [Pullup] or I = 0, the output sinks current) and p.297 (the pullup element may simply be missing) are the two rules the change relies on; p.121 is the single-load, both-edges characterisation that makes the open-drain a one-fixture solve."),
    dict(id="OD2", group="Open-drain", title="The open-drain NMOS map turns on at 0.2 of its gate swing, not the pull-up's 0.52",
         ours="Measured on eight widths: one curve, threshold 0.20, alpha 1.3, saturation 0.88. One prior cannot serve both halves.",
         quotes=["mosfet_eq", "mosfet_params", "modeled_by_use"],
         reading="The MOSFET law (p.89) has its own VTO per device; p.620 notes the same device is 'modeled differently based on its use in the circuit'. The book does not compare NMOS and PMOS maps; the 0.2-versus-0.52 finding is ours."),
    dict(id="OD3", group="Open-drain", title="Fit in the Kd domain, bracket the threshold from the fitted value, use the loop C_comp (3.0 pF)",
         ours="Three fitting traps found on the open-drain: the mirrored-Ku fit leaves the onset unconstrained, the excursion is not monotone in the threshold below the fitted value, and the declared 5 pF gives a visibly worse map than 3.0 pF.",
         quotes=["ccomp_measure", "ccomp_averaged_insufficient", "diagnose"],
         reading="Only the C_comp point has a source: the averaged capacitance of p.406 and its caveat. The fitting traps are method, not physics, and have no counterpart in the book."),

    # ---------------- method
    dict(id="M1", group="Method", title="Transistor is truth, native IBIS is the bar; whole shapes, not single numbers; back every claim with a figure",
         ours="Every comparison is against the HSPICE transistor with the same model card; native HSPICE IBIS is a second model, not a reference. Errors are read along the whole leg and across every width.",
         quotes=["verification_hardware_spice", "golden_waveforms", "fom", "few_percent", "ten_percent", "observation_theory", "surprises", "verify_simple_board"],
         reading="The book allows verification 'by the substituting a comparison of simulations with a previously hardware verified SPICE model' (p.369) and defines the golden-waveform and curve-overlay comparison (p.381, p.488). Its accuracy expectations (a couple of percent for verification, 10 % as the classic engineering rule, p.339, p.545) bracket our +/-10 % target. Its story of observation leading to a new model (p.540) is the register the investigation followed."),
    dict(id="M2", group="Method", title="What the book does not contain",
         ours="For honesty: the switching-coefficient algorithm (Ku, Kd), partial-transition or short-pulse behaviour, predriver stage equations, C_comp hysteresis, and the calibration procedure have no counterpart in the book.",
         quotes=["toggle_sooner", "pass_through"],
         reading="The words Ku and Kd never occur; the only mention of an early next edge is p.402; the only mention of internal modelling is the call for it on p.580. The book frames the problem and its rules; the mechanism and the recipe are this project's."),
]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def main() -> int:
    pages = {p["pdf_page"]: p for p in json.loads((BOOK / "pages.json").read_text(encoding="utf-8"))}
    bad = []
    cites = {}
    for key, (pdf, quote) in Q.items():
        page = pages[pdf]
        if norm(quote) not in norm(page["text"]):
            bad.append((key, pdf))
        cites[key] = dict(pdf_page=pdf, printed_page=page["printed_page"], section=page["section"], quote=quote)
    if bad:
        for k, p in bad:
            print(f"QUOTE NOT FOUND on pdf page {p}: {k}")
        return 1
    out = dict(
        book="Roy G. Leventhal and Lynne Green, Semiconductor Modeling: For Simulating Signal, Power, and Electromagnetic Integrity, Springer 2006 (ISBN 0-387-24159-0). Repository copy: silicon modeling book.pdf. 'p.' is the printed page; 'pdf' the page index in the file.",
        quotes=cites,
        findings=[dict(f, quotes=[dict(key=k, **cites[k]) for k in f["quotes"]]) for f in FINDINGS],
    )
    (BOOK / "citations.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    md = ["# The findings against the book",
          "",
          "Leventhal & Green, *Semiconductor Modeling: For Simulating Signal, Power, and Electromagnetic Integrity* (Springer 2006), the copy in the repository root. Page references are the printed page (p.) with the PDF page in brackets; the OCR text is in `docs/book/pages.json` and every quote below is checked verbatim against it (OCR spellings kept).",
          "",
          "The book never uses the words Ku or Kd, never discusses a pulse shorter than a transition, and contains no predriver equations. What it does contain is the frame: what an IBIS model is defined to be, the assumptions the specification makes about delay and about the V-T tables, the rules for C_comp, Vinh/Vinl and open-drain, the MOSFET law behind the curve, and the verification discipline. Each finding below is placed against that frame, and where the book has nothing, the entry says so.",
          ""]
    group = None
    for f in out["findings"]:
        if f["group"] != group:
            group = f["group"]
            md += [f"## {group}", ""]
        md += [f"### {f['id']} · {f['title']}", "", f"**Our finding.** {f['ours']}", ""]
        for q in f["quotes"]:
            md += [f"> \"{q['quote']}\"", f"> — p.{q['printed_page']} [pdf {q['pdf_page']}], {q['section']}", ""]
        md += [f"**Reading.** {f['reading']}", ""]
    (BOOK / "citations.md").write_text("\n".join(md), encoding="utf-8")
    print(f"{len(cites)} quotes verified, {len(FINDINGS)} findings -> {BOOK / 'citations.md'}, citations.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
