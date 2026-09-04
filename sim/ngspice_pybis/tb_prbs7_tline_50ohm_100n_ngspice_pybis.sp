* PRBS7 + pybis2spice + ideal 30 ps 50-ohm T-line
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

.include 'prbs7_vstim.inc'
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

TVAL  pad  0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0 50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p 100n
.end
