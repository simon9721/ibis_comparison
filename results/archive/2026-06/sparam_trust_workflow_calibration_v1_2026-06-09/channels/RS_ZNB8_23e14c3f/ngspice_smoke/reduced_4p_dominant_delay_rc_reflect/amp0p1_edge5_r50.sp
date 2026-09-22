* ngspice channel smoke: amp0p1_edge5_r50
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin   src  0  PWL(0 0 1n 0 1.005e-09 0.1 9n 0.1 9.005e-09 0)
Rsrc  src  p1  50
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_trust_workflow_calibration_v1_2026-06-09/channels/RS_ZNB8_23e14c3f/models/reduced_4p_dominant_delay_rc_reflect/RS_ZNB8_23e14c3f_reduced_4p_dominant_delay_rc_reflect.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rnear_neg  p2  0  50
Rterm_pos  p3  0  50
Rterm_neg  p4  0  50
.save V(p1) V(p2) V(p3) V(p4) V(src)
.tran 10p 1.97971888367e-08
.end
