* NGspice pybis: short 200 ps pulse train + new 50-ohm RLGC channel.
* Matching deterministic baseline for Xyce pybis option/model tests.
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

Vin   in_dig  0  PULSE(0 3.3 1.5n 200p 200p 2n 5n)
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

RCH_TX  pad tx_out 1u
.include '../new 50ohm channel/channel_ngspice.sp'
RTERM   n10b 0 50

.save V(in_dig) V(pad) V(tx_out) V(n10b) V(xdrv.ku) V(xdrv.kd) V(xdrv.nx)
.tran 10p 40n
.end
