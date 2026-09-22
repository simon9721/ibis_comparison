* ngspice channel smoke: amp0p5_edge5_ideal
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin  p1  0  PWL(0 0 1n 0 1.005e-09 0.5 9n 0.5 9.005e-09 0)
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18/selected_vector_models/Clarity_example_Fitted_55b55a71.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2)
.tran 10p 1.2e-08
.end
