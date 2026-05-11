* Test 1: Single rising edge only, no channel — baseline
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

Vin   in_dig  0  PWL(0 0  0.2n 3.3)
* NOTE: edge starts at t=0 -> N6 latches ~0.085V << 1.0V threshold in B18 -> NX frozen=0
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3
.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
Rload  pad  0  50
.save V(in_dig) V(pad)
.tran 10p 20n
.end
