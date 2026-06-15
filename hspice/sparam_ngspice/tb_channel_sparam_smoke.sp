* ============================================================
* ngspice smoke test: scikit-rf S-param equivalent channel only
* ============================================================
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin  pad  0  PWL(0 0 1n 0 1.005n 1.5 9n 1.5 9.005n 0)

.include 'Clarity_example.sp'
Xchannel  pad  ntst  s_equivalent

Rterm  ntst  0  50

.save V(pad) V(ntst)
.tran 10p 12n

.end
