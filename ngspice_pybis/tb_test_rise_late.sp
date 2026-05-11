* Test A1: Rise-only but edge delayed to t=1.5ns
* Hypothesis: N6 latches at 1.5V > 1.0V -> B18 gate opens -> NX advances -> no freeze
* If this PASSES where tb_test_rise FAILS, the B18 gate threshold is the root cause.
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

Vin   in_dig  0  PWL(0 0  1.5n 0  1.7n 3.3)
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3
.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
Rload  pad  0  50
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.nx)
.tran 10p 20n
.end
