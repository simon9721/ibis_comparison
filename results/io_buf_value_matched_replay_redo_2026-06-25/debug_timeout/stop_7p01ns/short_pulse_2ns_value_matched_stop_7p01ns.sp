* io_buf ngspice ValueMatchedReplayHybrid value-matched replay redo
* Sweep case: short_pulse_2ns_high
* 2 ns high pulse before output settles, 1 ps edges, 50 ohm + 2 pF
.title io_buf ngspice ngspice ValueMatchedReplayHybrid short_pulse_2ns_high
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+         7n      3.3
+     7.001n        0
+        14n        0 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.kutarget) V(xdrv.kdtarget) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.kusamp) V(xdrv.kdsamp) V(xdrv.tf_ku) V(xdrv.tf_kd) V(xdrv.tf_start) V(xdrv.tr_ku) V(xdrv.tr_kd) V(xdrv.tr_start) V(xdrv.vmstart) V(xdrv.vmarg) V(xdrv.match_err_ku) V(xdrv.match_err_kd) V(xdrv.start_disagree) V(xdrv.match_ambiguous) V(xdrv.hvmatch) V(xdrv.kumatch) V(xdrv.kdmatch)
.tran 0.001n 7.01n
.end
