* Channel-only ngspice sweep case: amp0p1_edge5_ideal
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin  pad  0  PWL(0 0 1n 0 1.005e-09 0.1 9n 0.1 9.005e-09 0)

.include '../Clarity_example_vector_3r3c_unforced.sp'
Xchannel  pad  ntst  s_equivalent
Rterm  ntst  0  50

.save V(pad) V(ntst)
.tran 10p 1.2e-08
.end
