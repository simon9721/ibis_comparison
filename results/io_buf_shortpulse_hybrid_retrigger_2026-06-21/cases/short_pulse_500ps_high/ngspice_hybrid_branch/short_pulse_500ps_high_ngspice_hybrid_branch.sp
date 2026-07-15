* io_buf ShortPulseHybrid branch/ngspice switching coefficient extraction
* Sweep case: short_pulse_500ps_high
* 500 ps high pulse with 1 ps edges, 50 ohm + 2 pF
.title io_buf ngspice ShortPulseHybrid branch Ku/Kd extraction short_pulse_500ps_high
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+       5.5n      3.3
+     5.501n        0
+      12.5n        0 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.kutarget) V(xdrv.kdtarget) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.kucor) V(xdrv.kdcor) V(xdrv.hshort) V(xdrv.highage)
.tran 0.001n 12.5n
.end
