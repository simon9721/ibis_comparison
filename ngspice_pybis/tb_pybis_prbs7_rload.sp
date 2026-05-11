* ============================================================
* PRBS7 Rload bench — pybis2spice driver, no T-line
* Purpose: capture runtime Ku/Kd/NX/NI for alignment analysis
* 200 Mbps (5 ns UI), 200 bits = 1000 ns
* ============================================================

.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

.include 'prbs7_vstim.inc'
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

Rload  pad  0  50

* Save input, output, and all Ku/Kd internal signals
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.nx) V(xdrv.ni)
.tran 10p 1000n

.end
