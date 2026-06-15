* ngspice channel smoke: amp0p1_edge5_r50
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin   src  0  PWL(0 0 1n 0 1.005e-09 0.1 9n 0.1 9.005e-09 0)
Rsrc  src  p1  50
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_trust_workflow_calibration_v1_2026-06-09/channels/ntwk3_ad74ab42/models/vector_5r5c_enforced/ntwk3_ad74ab42_vector_5r5c_enforced.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2) V(src)
.tran 10p 1.2e-08
.end
