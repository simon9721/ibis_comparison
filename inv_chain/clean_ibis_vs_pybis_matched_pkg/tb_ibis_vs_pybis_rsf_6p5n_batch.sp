* ============================================================
* Clean RSF validation bench for:
*   - native IBIS VT waveform overlay (offline, from t2b_0615_v5.ibs)
*   - converted pybis2spice ngspice model
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin   in_dig   0  PWL(0 0 1n 0 1.005n 1.8 4n 1.8 4.005n 0)
Ven   en_sig   0  DC 1.8
Vdd   vdd      0  DC 1.8

.include 'driver2_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver2_OutputInput_Typical

T1  pad  0  ntst  0  Z0=50 Td=30p
R1  ntst 0  50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p 6.5n

.end
