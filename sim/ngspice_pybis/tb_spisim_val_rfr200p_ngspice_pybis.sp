* Generated SPISim-style pybis validation bench: Rise-fall-rise, 200 ps edges

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin   in_dig   0  PWL(0 0 1n 0 1.2n 3.3 9n 3.3 9.2n 0 17n 0 17.2n 3.3 25n 3.3 25.2n 0)
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

TVAL  pad  0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0  50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p 26n
.end
