* io_buf legacy pybis/ngspice value-matched replay extraction
* Sweep case: short_pulse_500ps_low
* 500 ps low pulse after settled high, 50 ohm + 2 pF
.title io_buf ngspice legacy pybis Ku/Kd extraction short_pulse_500ps_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         3n        0
+     3.001n      3.3
+         8n      3.3
+     8.001n        0
+       8.5n        0
+     8.501n      3.3
+        16n      3.3 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 16n
.end
