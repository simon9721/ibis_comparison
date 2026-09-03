* Cross-buffer value-matched replay study
.title inv_chain v2_ku_only short_pulse_50ps_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 1.8
+ 10n 1.8
+ 10.001n 0
+ 10.05n 0
+ 10.051n 1.8
+ 18n 1.8 )

Ven en_sig 0 DC 1.8
Vdd vdd 0 DC 1.8
.include 'driver2_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver2_OutputInput_Typical
Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.kupre) V(xdrv.kdpre) V(xdrv.kusamp) V(xdrv.kdsamp) V(xdrv.tr_ku) V(xdrv.tr_kd) V(xdrv.tf_ku) V(xdrv.tf_kd) V(xdrv.tr_start) V(xdrv.tf_start) V(xdrv.vmstart_latch) V(xdrv.kustart_latch) V(xdrv.kdstart_latch) V(xdrv.vmt0) V(xdrv.vmelapsed) V(xdrv.vmarg) V(xdrv.kuarg) V(xdrv.kdarg) V(xdrv.start_disagree) V(xdrv.match_ambiguous) V(xdrv.hvmatch) V(xdrv.vmsample) V(xdrv.vmlatchpulse) V(xdrv.vmactivate) V(xdrv.hreverse_edge) V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall) V(xdrv.kumatch) V(xdrv.kdmatch) V(xdrv.kutarget) V(xdrv.kdtarget)
.tran 2p 18n
.end
