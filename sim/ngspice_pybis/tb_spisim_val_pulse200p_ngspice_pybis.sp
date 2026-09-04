* Generated SPISim-style pybis validation bench: Practical pulse, 200 ps edges

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin   in_dig   0  PULSE(0 3.3 1n 200p 200p 1.5n 3n)
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

TVAL  pad  0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0  50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p 20n
.end
