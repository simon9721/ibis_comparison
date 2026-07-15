* ngspice channel smoke: amp0p5_edge5_ideal
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin  p1  0  PWL(0 0 1n 0 1.005e-09 0.5 9n 0.5 9.005e-09 0)
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Agilent_E5071B_17b7949f/models/bbs_passivity2_gspice_lowfreq/Agilent_E5071B_17b7949f_bbs_passivity2_gspice_lowfreq_ngspice_wrapper.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rnear_neg  p2  0  50
Rterm_pos  p3  0  50
Rterm_neg  p4  0  50
.save V(p1) V(p2) V(p3) V(p4)
.tran 10p 1.2e-08
.end
