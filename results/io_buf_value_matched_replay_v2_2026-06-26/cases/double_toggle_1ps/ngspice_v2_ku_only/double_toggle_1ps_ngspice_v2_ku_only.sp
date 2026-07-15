* io_buf ngspice value-matched v2 Ku-only value-matched replay redo
* Sweep case: double_toggle_1ps
* 1 ps high then 1 ps low double toggle, 50 ohm + 2 pF
.title io_buf ngspice ngspice value-matched v2 Ku-only double_toggle_1ps
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

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.kutarget) V(xdrv.kdtarget) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.kupre) V(xdrv.kdpre) V(xdrv.kupending) V(xdrv.kdpending) V(xdrv.hprehold) V(xdrv.hvmpending) V(xdrv.hvmholdtarget) V(xdrv.kusamp) V(xdrv.kdsamp) V(xdrv.tf_ku) V(xdrv.tf_kd) V(xdrv.tf_start) V(xdrv.tr_ku) V(xdrv.tr_kd) V(xdrv.tr_start) V(xdrv.vmstart) V(xdrv.vmstart_latch) V(xdrv.vmt0) V(xdrv.vmelapsed) V(xdrv.vmarg) V(xdrv.kuarg) V(xdrv.kdarg) V(xdrv.kustart_latch) V(xdrv.kdstart_latch) V(xdrv.match_err_ku) V(xdrv.match_err_kd) V(xdrv.start_disagree) V(xdrv.match_ambiguous) V(xdrv.hvmatch) V(xdrv.vmsample) V(xdrv.vmlatchpulse) V(xdrv.vmarg_backstep) V(xdrv.coeff_jump_ku) V(xdrv.coeff_jump_kd) V(xdrv.hnx) V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall) V(xdrv.hreverse_edge) V(xdrv.hintwindow) V(xdrv.had_rise) V(xdrv.had_fall) V(xdrv.kumatch) V(xdrv.kdmatch)
.tran 0.001n 12.5n
.end
