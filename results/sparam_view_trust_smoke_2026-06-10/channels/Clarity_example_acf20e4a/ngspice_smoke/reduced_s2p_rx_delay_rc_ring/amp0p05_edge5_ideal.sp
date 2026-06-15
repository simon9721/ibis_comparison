* ngspice channel smoke: amp0p05_edge5_ideal
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin  p1  0  PWL(0 0 1n 0 1.005e-09 0.05 9n 0.05 9.005e-09 0)
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_view_trust_smoke_2026-06-10/channels/Clarity_example_acf20e4a/models/reduced_s2p_rx_delay_rc_ring/Clarity_example_acf20e4a_reduced_s2p_rx_delay_rc_ring.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2)
.tran 10p 1.23650420205e-08
.end
