* ============================================================
* Long-hold rise-steady-fall ngspice validation bench for the
* regenerated input-driven pybis2spice model.
* Same simple validation load, but includes the freshly
* regenerated state-aware selector netlist.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin   in_dig   0  PWL(0 0  1n 0  1.005n 3.3  21n 3.3  21.005n 0  24n 0)
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include 'driver_OutputInput_Typical_regen.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

T1  pad  0  ntst  0  Z0=50 Td=30p
R1  ntst 0  50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p 24n

.end
