* inv_chain reversal hybrid
* case: short_pulse_200ps_low
.title inv_chain reversal hybrid short_pulse_200ps_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12 filetype=binary

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 1.8
+ 10n 1.8
+ 10.001n 0
+ 10.2n 0
+ 10.201n 1.8
+ 14n 1.8 )

Ven en_sig 0 DC 1.8
Vdd vdd 0 DC 1.8
.include 'driver2_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver2_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
+ V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.kutarget) V(xdrv.kdtarget)
+ V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget)
+ V(xdrv.kugate) V(xdrv.kdgate)
+ V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall)
+ V(xdrv.hreverseraw) V(xdrv.hsettled) V(xdrv.hhybridactive)
+ V(xdrv.highage) V(xdrv.lowage)
+ V(xdrv.kures) V(xdrv.kures_table) V(xdrv.guprate)
+ V(xdrv.kdres) V(xdrv.kdres_table) V(xdrv.gdnrate)
.tran 0.001n 14n
.end
