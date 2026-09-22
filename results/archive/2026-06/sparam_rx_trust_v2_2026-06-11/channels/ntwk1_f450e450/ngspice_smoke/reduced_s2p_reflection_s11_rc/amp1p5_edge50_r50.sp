* ngspice channel smoke: amp1p5_edge50_r50
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin   src  0  PWL(0 0 1n 0 1.05e-09 1.5 9n 1.5 9.05e-09 0)
Rsrc  src  p1  50
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_rx_trust_v2_2026-06-11/channels/ntwk1_f450e450/models/reduced_s2p_reflection_s11_rc/ntwk1_f450e450_reduced_s2p_reflection_s11_rc.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2) V(src)
.tran 10p 1.20445997124e-08
.end
