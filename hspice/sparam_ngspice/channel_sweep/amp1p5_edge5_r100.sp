* Channel-only ngspice sweep case: amp1p5_edge5_r100
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin   src  0    PWL(0 0 1n 0 1.005e-09 1.5 9n 1.5 9.005e-09 0)
Rsrc  src  pad  100

.include '../Clarity_example.sp'
Xchannel  pad  ntst  s_equivalent
Rterm  ntst  0  50

.save V(src) V(pad) V(ntst)
.tran 10p 1.2e-08
.end
