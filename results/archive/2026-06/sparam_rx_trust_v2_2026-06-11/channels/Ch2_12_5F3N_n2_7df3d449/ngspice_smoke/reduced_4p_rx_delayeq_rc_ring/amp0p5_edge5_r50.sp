* ngspice channel smoke: amp0p5_edge5_r50
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin   src  0  PWL(0 0 1n 0 1.005e-09 0.5 9n 0.5 9.005e-09 0)
Rsrc  src  p1  50
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_rx_trust_v2_2026-06-11/channels/Ch2_12_5F3N_n2_7df3d449/models/reduced_4p_rx_delayeq_rc_ring/Ch2_12_5F3N_n2_7df3d449_reduced_4p_rx_delayeq_rc_ring.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rnear_neg  p2  0  50
Rterm_pos  p3  0  50
Rterm_neg  p4  0  50
.save V(p1) V(p2) V(p3) V(p4) V(src)
.tran 10p 1.31070476317e-08
.end
