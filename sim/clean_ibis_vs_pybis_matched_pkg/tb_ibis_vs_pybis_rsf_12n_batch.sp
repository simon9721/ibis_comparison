* ============================================================
* Clean RSF validation bench for:
*   - native IBIS VT waveform overlay (offline, from io_buf.ibs)
*   - converted pybis2spice ngspice model
*
* This bench drives only the converted model. The IBIS waveform
* is overlaid later in the local Python plot script using the
* matching R_fixture=50, V_fixture=0 waveform blocks.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin   in_dig   0  PWL(0 0 1n 0 1.005n 3.3 9n 3.3 9.005n 0)
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

T1  pad  0  ntst  0  Z0=50 Td=30p
R1  ntst 0  50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p 12n

.end
