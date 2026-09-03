* io_buf ChargeLimitedGateHybrid/ngspice charge-limited Ku/Kd extraction
* Sweep case: short_pulse_500ps_low
* 500 ps low pulse after settled high, 50 ohm + 2 pF
.title io_buf ngspice ChargeLimitedGateHybrid Ku/Kd extraction short_pulse_500ps_low
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

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.kutarget) V(xdrv.kdtarget) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.hinterrupt) V(xdrv.hshort) V(xdrv.highage) V(xdrv.lowage) V(xdrv.koverlap) V(xdrv.gup) V(xdrv.gdn) V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.ku_on) V(xdrv.ku_off) V(xdrv.kd_off) V(xdrv.kd_on) V(xdrv.kudir) V(xdrv.kddir) V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall) V(xdrv.hdiractive) V(xdrv.halign) V(xdrv.haligned) V(xdrv.qpu) V(xdrv.qpd) V(xdrv.qputarget) V(xdrv.qpdtarget) V(xdrv.kuchg) V(xdrv.kdchg) V(xdrv.hchgactive) V(xdrv.had_rise) V(xdrv.had_fall) V(xdrv.hchgunsettled)
.tran 0.001n 16n
.end
