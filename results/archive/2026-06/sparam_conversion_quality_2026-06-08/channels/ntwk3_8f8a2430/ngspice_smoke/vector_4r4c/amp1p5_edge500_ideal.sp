* ngspice channel smoke: amp1p5_edge500_ideal
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin  p1  0  PWL(0 0 1n 0 1.5e-09 1.5 9n 1.5 9.5e-09 0)
.include '../../models/vector_4r4c/ntwk3_8f8a2430_vector_4r4c.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2)
.tran 10p 1.2e-08
.end
