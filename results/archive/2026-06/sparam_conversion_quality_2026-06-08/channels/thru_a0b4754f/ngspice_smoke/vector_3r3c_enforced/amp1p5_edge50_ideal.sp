* ngspice channel smoke: amp1p5_edge50_ideal
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin  p1  0  PWL(0 0 1n 0 1.05e-09 1.5 9n 1.5 9.05e-09 0)
.include '../../models/vector_3r3c_enforced/thru_a0b4754f_vector_3r3c_enforced.sp'
Xchannel  p1  p2  s_equivalent
Rterm  p2  0  50
.save V(p1) V(p2)
.tran 10p 1.2e-08
.end
