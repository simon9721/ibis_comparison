* Step2 alignment: add startup method only (uic + ic)
* Based on step1_rin; solver and power topology unchanged
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

.include '../ngspice_refspice/prbs7_vstim.inc'
Rin    in_src  in_dig  1
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

RCH_TX  pad tx_out 1u
.include '../new 50ohm channel/channel_ngspice.sp'
RTERM   n10b 0 50

.save V(in_dig) V(pad) V(tx_out) V(n10b)
.ic V(pad)=0 V(tx_out)=0 V(n10b)=0
.tran 10p 1000n uic
.end
