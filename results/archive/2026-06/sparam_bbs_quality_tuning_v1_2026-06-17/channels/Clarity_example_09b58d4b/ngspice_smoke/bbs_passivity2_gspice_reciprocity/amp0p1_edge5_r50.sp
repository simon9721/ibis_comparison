* ngspice channel smoke: amp0p1_edge5_r50
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin   src  0  PWL(0 0 1n 0 1.005e-09 0.1 9n 0.1 9.005e-09 0)
Rsrc  src  p1  50
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/models/bbs_passivity2_gspice_reciprocity/Clarity_example_09b58d4b_bbs_passivity2_gspice_reciprocity_ngspice_wrapper.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2) V(src)
.tran 10p 1.2e-08
.end
