* ngspice channel smoke: amp1p5_edge5_ideal
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin  p1  0  PWL(0 0 1n 0 1.005e-09 1.5 9n 1.5 9.005e-09 0)
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_bbs_quality_tuning_v1_smoke_2026-06-17/channels/Clarity_example_40c993a4/models/bbs_passivity2_gspice_lowfreq/Clarity_example_40c993a4_bbs_passivity2_gspice_lowfreq_ngspice_wrapper.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2)
.tran 10p 1.2e-08
.end
