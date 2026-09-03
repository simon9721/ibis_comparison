* io_buf ngspice legacy pybis two-state gate study
* Sweep case: short_pulse_1ns_low
* 1 ns low pulse after high state, 1 ps edges, 50 ohm + 2 pF
.title io_buf ngspice ngspice legacy pybis short_pulse_1ns_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+        10n      3.3
+    10.001n        0
+        11n        0
+    11.001n      3.3
+        18n      3.3 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 18n
.end
