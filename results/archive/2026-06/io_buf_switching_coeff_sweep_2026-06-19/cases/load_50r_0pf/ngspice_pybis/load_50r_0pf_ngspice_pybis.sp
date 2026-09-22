* io_buf pybis/ngspice switching coefficient extraction
* Sweep case: load_50r_0pf
* 1 ps rise/fall, 50 ohm only
.title io_buf ngspice pybis Ku/Kd extraction load_50r_0pf
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+        15n      3.3
+    15.001n        0
+        25n        0 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50


.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 25n
.end
