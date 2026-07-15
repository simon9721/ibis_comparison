* io_buf state-continuous pybis/ngspice switching coefficient extraction
* Sweep case: double_toggle_1ps
* Two 1 ps toggle cycles, 50 ohm + 2 pF
.title io_buf ngspice state-continuous pybis Ku/Kd extraction double_toggle_1ps
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         3n        0
+     3.001n      3.3
+         8n      3.3
+     8.001n        0
+        13n        0
+    13.001n      3.3
+        18n      3.3
+    18.001n        0
+        24n        0 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.pstate) V(xdrv.kutarget) V(xdrv.kdtarget)
.tran 0.001n 24n
.end
