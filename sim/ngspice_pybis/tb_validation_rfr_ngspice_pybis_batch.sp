* ============================================================
* Rise-fall-rise ngspice validation bench for the input-driven
* pybis2spice model.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

* Input / supplies
Vin   in_dig   0  PWL(0 0 1n 0 1.005n 3.3 9n 3.3 9.005n 0 17n 0 17.005n 3.3 25n 3.3 25.005n 0)
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

* Converted pybis2spice model, using SPISim-style Ku/Kd timing control
.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

* SPISim-style validation load: ideal delayed 50 ohm environment
T1  pad  0  ntst  0  Z0=50 Td=30p
R1  ntst 0  50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p 26n

.end
