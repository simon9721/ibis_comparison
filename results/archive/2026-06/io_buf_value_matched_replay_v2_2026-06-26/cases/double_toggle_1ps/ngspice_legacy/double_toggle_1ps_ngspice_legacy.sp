* io_buf ngspice legacy pybis value-matched replay redo
* Sweep case: double_toggle_1ps
* 1 ps high then 1 ps low double toggle, 50 ohm + 2 pF
.title io_buf ngspice ngspice legacy pybis double_toggle_1ps
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+     5.001n      3.3
+     5.002n        0
+     5.002n        0
+     5.003n      3.3
+      12.5n      3.3 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 12.5n
.end
