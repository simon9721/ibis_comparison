* Three-buffer pad-match replay study
.title io_buf voltage_matching short_low_mid50_162ps
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 3.3
+ 10n 3.3
+ 10.05n 0
+ 10.1625n 0
+ 10.2125n 3.3
+ 22n 3.3 )
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3
.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical
Rload pad 0 50
Cload pad 0 2p
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.padsamp) V(xdrv.padslewpre) V(xdrv.padslewsamp) V(xdrv.tr_pad_early) V(xdrv.tf_pad_early) V(xdrv.tr_pad_late) V(xdrv.tf_pad_late) V(xdrv.tr_pad_score) V(xdrv.tf_pad_score) V(xdrv.tr_pad_score_late) V(xdrv.tf_pad_score_late) V(xdrv.padstartcmd) V(xdrv.padstart_latch) V(xdrv.padstartspan) V(xdrv.padmatch_ambiguous) V(xdrv.pmt0) V(xdrv.pmelapsed) V(xdrv.padarg) V(xdrv.kupadmatch) V(xdrv.kdpadmatch) V(xdrv.padmapactive) V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall) V(xdrv.hreverse_edge) V(xdrv.pmsample) V(xdrv.pmlatchpulse) V(xdrv.kutarget) V(xdrv.kdtarget) V(xdrv.coeff_jump_ku) V(xdrv.coeff_jump_kd)
.tran 2p 22n
.end
