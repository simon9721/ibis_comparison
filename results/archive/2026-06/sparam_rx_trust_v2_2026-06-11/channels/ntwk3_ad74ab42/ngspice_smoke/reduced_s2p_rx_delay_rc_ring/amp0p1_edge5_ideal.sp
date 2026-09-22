* ngspice channel smoke: amp0p1_edge5_ideal
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin  p1  0  PWL(0 0 1n 0 1.005e-09 0.1 9n 0.1 9.005e-09 0)
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_rx_trust_v2_2026-06-11/channels/ntwk3_ad74ab42/models/reduced_s2p_rx_delay_rc_ring/ntwk3_ad74ab42_reduced_s2p_rx_delay_rc_ring.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2)
.tran 10p 1.20632099593e-08
.end
