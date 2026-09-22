# Vector-Fit Audit Testbenches

This folder contains the model and exact transient testbench decks used for the vector-fit HSPICE/ngspice overlay figures in the parent folder.

## Case 01: Clarity Selected Vector Fit

This is the selected `.s2p` vector-fit case.

### Channel Model

- `selected_vector_model/Clarity_example_4ef781de_selected_raw_vector_3r3c_lin.sp`

This is the selected scikit-rf vector-fit SPICE export used by ngspice. It defines:

```spice
.SUBCKT s_equivalent p1 p2
```

### HSPICE Native S-Parameter Benches

These are exact copies of the HSPICE audit decks:

- `hspice_native_s/audit_amp1p5_edge5_r50_hspice.sp`
- `hspice_native_s/audit_amp1p5_edge50_r50_hspice.sp`
- `hspice_native_s/audit_amp1p5_edge500_r50_hspice.sp`

They use the native HSPICE `S` model:

```spice
Schannel  p1  p2  0  MNAME=ch_model
.MODEL ch_model S
+ TSTONEFILE='../../../../../converted_sp_comparison_2026-06-12/inputs/Clarity_example.S2P'
```

### ngspice Vector-Fit Benches

These are exact copies of the ngspice audit decks:

- `ngspice_vector_fit/audit_amp1p5_edge5_r50_ngspice.sp`
- `ngspice_vector_fit/audit_amp1p5_edge50_r50_ngspice.sp`
- `ngspice_vector_fit/audit_amp1p5_edge500_r50_ngspice.sp`

They include the selected scikit-rf vector-fit `.sp` and instantiate:

```spice
Xchannel  p1  p2  s_equivalent
```

### Input Touchstone

- `input_touchstone/Clarity_example.S2P`

This is copied here for convenience and inspection. The HSPICE decks above are exact copies from the audit run, so their `TSTONEFILE` line still points to the original generated study path rather than this local copy.

## Case 02: Ch10 Forced Vector-Fit Demo

This is a forced `.s4p` vector-fit demo case. It was not selected by the quality gates, but it is useful for showing that vector-fit conversion quality varies by channel and by metric.

Candidate:

- `case_02_Ch10_35_5F3N_f4_raw_vector_12r12c_lin/selected_vector_model/Ch10_35_5F3N_f4_cdb7d8f1_raw_vector_12r12c_lin.sp`

This candidate had:

- RX path complex RMS fit error: about `1.07e-4`
- full S-matrix complex RMS fit error: about `8.51e-2`
- reflection/S11-side complex RMS fit error: about `1.67e-1`

That makes it a good demonstration case: the RX-through path can look good while the full multiport/reflection quality is still poor.

HSPICE native S-parameter decks:

- `case_02_Ch10_35_5F3N_f4_raw_vector_12r12c_lin/hspice_native_s/audit_amp1p5_edge5_r50_hspice.sp`
- `case_02_Ch10_35_5F3N_f4_raw_vector_12r12c_lin/hspice_native_s/audit_amp1p5_edge50_r50_hspice.sp`
- `case_02_Ch10_35_5F3N_f4_raw_vector_12r12c_lin/hspice_native_s/audit_amp1p5_edge500_r50_hspice.sp`

ngspice vector-fit decks:

- `case_02_Ch10_35_5F3N_f4_raw_vector_12r12c_lin/ngspice_vector_fit/audit_amp1p5_edge5_r50_ngspice.sp`
- `case_02_Ch10_35_5F3N_f4_raw_vector_12r12c_lin/ngspice_vector_fit/audit_amp1p5_edge50_r50_ngspice.sp`
- `case_02_Ch10_35_5F3N_f4_raw_vector_12r12c_lin/ngspice_vector_fit/audit_amp1p5_edge500_r50_ngspice.sp`

Input Touchstone:

- `case_02_Ch10_35_5F3N_f4_raw_vector_12r12c_lin/input_touchstone/Ch10_35_5F3N_f4.s4p`

For Ch10, the HSPICE decks use the local copied `.s4p` filename because HSPICE failed to open the deeper relative path during the first forced audit attempt.

## Common Setup

All audit decks use:

- 1.5 V PWL input
- 50 ohm source resistance
- 50 ohm receiver termination
- edge rates: `5 ps`, `50 ps`, `500 ps`
- transient stop time: `35 ns`
