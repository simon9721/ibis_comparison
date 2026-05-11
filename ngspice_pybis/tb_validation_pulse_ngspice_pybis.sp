* ============================================================
* Compact ngspice validation bench for the pybis2spice input-driven model
* Mirrors the role of SPISim's Ibs2Spc_Coef.spc:
*   simple pulse input -> converted buffer -> 50 ohm delayed line -> 50 ohm load
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

* Input / supplies
Vin   in_dig   0  PULSE(0 3.3 1n 5p 5p 1.5n 3n)
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

* Converted pybis2spice model, using SPISim-style Ku/Kd timing control
.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

* SPISim-style validation load: ideal delayed 50 ohm environment
T1  pad  0  ntst  0  Z0=50 Td=30p
R1  ntst 0  50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)

.control
set filetype=ascii
tran 10p 20n uic
linearize V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
write tb_validation_pulse_ngspice_pybis.raw V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.endc

.end
