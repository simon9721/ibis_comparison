* realistic-pulse ngspice
.title inv_chain InputDrivenHybridV3AlignedReplay short_high_swing70
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 1.8
+ 5.110786n 1.8
+ 5.160786n 0
+ 22n 0 )

Ven en_sig 0 DC 1.8
Vdd vdd 0 DC 1.8
.include 'driver2_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver2_OutputInput_Typical
Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget) V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kuleg) V(xdrv.kdleg) V(xdrv.kutarget) V(xdrv.kdtarget) V(xdrv.hfall_after_rise) V(xdrv.hrise_after_fall) V(xdrv.hreverseraw) V(xdrv.hsettled) V(xdrv.hhybridactive) V(xdrv.kures) V(xdrv.kdres) V(xdrv.guprate) V(xdrv.gdnrate) V(xdrv.v3revedge) V(xdrv.v3latchpulse) V(xdrv.v3activate) V(xdrv.v3kupre) V(xdrv.v3kdpre) V(xdrv.v3kuvissamp) V(xdrv.v3kdvissamp) V(xdrv.v3kugatesamp) V(xdrv.v3kdgatesamp) V(xdrv.v3alignerrku) V(xdrv.v3alignerrkd) V(xdrv.v3gatealigned) V(xdrv.v3kuanchor) V(xdrv.v3kdanchor) V(xdrv.v3dir) V(xdrv.v3trku) V(xdrv.v3trkd) V(xdrv.v3tfku) V(xdrv.v3tfkd) V(xdrv.v3kustart) V(xdrv.v3kdstart) V(xdrv.v3t0) V(xdrv.v3elapsed) V(xdrv.v3kuarg) V(xdrv.v3kdarg) V(xdrv.v3kuprogress) V(xdrv.v3kdprogress) V(xdrv.v3kureplay) V(xdrv.v3kdreplay) V(xdrv.v3enderrku) V(xdrv.v3enderrkd) V(xdrv.v3done) V(xdrv.hv3active) V(xdrv.hv3pending) V(xdrv.v3prehold)
.tran 0.002n 22n
.end
