* ngspice channel smoke: amp0p05_edge5_r50
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin   src  0  PWL(0 0 1n 0 1.005e-09 0.05 9n 0.05 9.005e-09 0)
Rsrc  src  p1  50
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_view_trust_cisco_smoke2_2026-06-10/channels/Ch10_35_5F3N_f2_f23c49e2/models/reduced_4p_reflection/Ch10_35_5F3N_f2_f23c49e2_reduced_4p_reflection.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rnear_neg  p2  0  50
Rterm_pos  p3  0  50
Rterm_neg  p4  0  50
.save V(p1) V(p2) V(p3) V(p4) V(src)
.tran 10p 1.53091568587e-08
.end
