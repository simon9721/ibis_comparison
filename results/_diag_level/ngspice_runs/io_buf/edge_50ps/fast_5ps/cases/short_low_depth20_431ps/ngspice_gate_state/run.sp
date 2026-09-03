* realistic-pulse ngspice
.title io_buf InputDrivenTwoStateGateLevelCommandFull short_low_depth20_431ps
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 3.3
+ 10n 3.3
+ 10.05n 0
+ 10.4314n 0
+ 10.4814n 3.3
+ 22n 3.3 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3
.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical
Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget) V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.kutarget) V(xdrv.kdtarget) V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall) V(xdrv.hreverseraw) V(xdrv.hsettled) V(xdrv.hhybridactive) V(xdrv.kures) V(xdrv.kdres) V(xdrv.guprate) V(xdrv.gdnrate) V(xdrv.gupcmd) V(xdrv.gdncmd) V(xdrv.gupcmdtgt) V(xdrv.gdncmdtgt) V(xdrv.puonlvl) V(xdrv.puofflvl) V(xdrv.pdonlvl) V(xdrv.pdofflvl)
.tran 0.002n 22n
.end
