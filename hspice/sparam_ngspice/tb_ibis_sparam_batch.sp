* ============================================================
* ngspice batch testbench: pybis2spice driver + scikit-rf S-param channel
* Same topology as tb_ibis_sparam.sp, without interactive .control plot.
* ============================================================
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

* --- Stimulus ---
Vin   in_dig   0  PWL(0 0 1n 0 1.005n 3.3 9n 3.3 9.005n 0)
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

* --- IBIS converted driver ---
.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

* --- S-parameter channel ---
.include 'Clarity_example.sp'
Xchannel  pad  ntst  s_equivalent

* --- Rx termination ---
Rterm  ntst  0  50

* --- Probes and simulation ---
.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p 12n

.end
