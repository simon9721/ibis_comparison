* io_buf ngspice two-state identity full two-state gate study
* Sweep case: short_pulse_2ns_high
* 2 ns high pulse before output settles, 1 ps edges, 50 ohm + 2 pF
.title io_buf ngspice ngspice two-state identity full short_pulse_2ns_high
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

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.kutarget) V(xdrv.kdtarget) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget) V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kugate_on) V(xdrv.kugate_off) V(xdrv.kdgate_on) V(xdrv.kdgate_off) V(xdrv.gdnrate) V(xdrv.kdres) V(xdrv.kdres_table) V(xdrv.pdrecoveredge) V(xdrv.pdnormalfall) V(xdrv.pdonp_norm) V(xdrv.pdonp_recover) V(xdrv.hshort_high_recovery) V(xdrv.hnx) V(xdrv.h2stateactive) V(xdrv.koverlap) V(xdrv.vmarg) V(xdrv.vmstart_latch) V(xdrv.vmelapsed) V(xdrv.start_disagree) V(xdrv.match_ambiguous)
.tran 0.001n 14n
.end
