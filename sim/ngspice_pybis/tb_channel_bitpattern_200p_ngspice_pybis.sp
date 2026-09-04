* NGspice pybis: short deterministic bit pattern + new 50-ohm RLGC channel.
* Pattern after initial low: 1 0 1 1 0 0 1 0, 5 ns UI, 200 ps edges.
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

Vin   in_dig  0  PWL(0 0  1.5n 0  1.7n 3.3  6.5n 3.3  6.7n 0  11.5n 0  11.7n 3.3  21.5n 3.3  21.7n 0  31.5n 0  31.7n 3.3  36.5n 3.3  36.7n 0  45n 0)
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

RCH_TX  pad tx_out 1u
.include '../new 50ohm channel/channel_ngspice.sp'
RTERM   n10b 0 50

.save V(in_dig) V(pad) V(tx_out) V(n10b) V(xdrv.ku) V(xdrv.kd) V(xdrv.nx)
.tran 10p 45n
.end
