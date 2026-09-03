* delay-aware parallel ngspice audit: audit_amp1p5_edge50_r50
.temp 27
.options method=gear maxord=2 reltol=1e-5 abstol=1e-11 vntol=1e-7 gmin=1e-12
Vin   src  0  PWL(0 0 1n 0 1.05e-09 1.5 9n 1.5 9.05e-09 0)
Rsrc  src  p1  50
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_cisco_s11_proto_2026-06-09_strength050/Ch5_22_5F3N_t/models/s_equivalent_delay_parallel_s11.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rnear_neg  p2  0  50
Rterm_pos  p3  0  50
Rterm_neg  p4  0  50
.save V(src) V(p1) V(p2) V(p3) V(p4)
.tran 5p 3.5e-08
.end
