* ============================================================
* Long-hold RSF debug bench for the input-driven pybis2spice
* model. Saves internal selector/timing nodes to diagnose which
* K family is active during the high hold.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin   in_dig   0  PWL(0 0  1n 0  1.005n 3.3  21n 3.3  21.005n 0  24n 0)
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

T1  pad  0  ntst  0  Z0=50 Td=30p
R1  ntst 0  50

.save V(in_dig) V(pad) V(ntst)
+ V(xdrv.ni) V(xdrv.n2) V(xdrv.n3) V(xdrv.n4) V(xdrv.n5) V(xdrv.n6) V(xdrv.n8) V(xdrv.nx)
+ V(xdrv.kur0) V(xdrv.kdr0) V(xdrv.kuf0) V(xdrv.kdf0)
+ V(xdrv.nkur) V(xdrv.nkdr) V(xdrv.nkuf) V(xdrv.nkdf)
+ V(xdrv.ku) V(xdrv.kd)
.tran 10p 6n

.end
