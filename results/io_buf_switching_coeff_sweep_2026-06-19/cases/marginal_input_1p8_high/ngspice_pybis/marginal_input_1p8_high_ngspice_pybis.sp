* io_buf pybis/ngspice switching coefficient extraction
* Sweep case: marginal_input_1p8_high
* 1.8 V high input, below nominal Vinh, 50 ohm + 2 pF
.title io_buf ngspice pybis Ku/Kd extraction marginal_input_1p8_high
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      1.8
+        15n      1.8
+    15.001n        0
+        25n        0 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 25n
.end
