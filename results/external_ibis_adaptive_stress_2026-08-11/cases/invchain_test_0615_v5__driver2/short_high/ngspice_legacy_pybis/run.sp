* Model-adaptive interrupted-transition legacy-pybis stress case
.title invchain_test_0615_v5.ibs / driver2 / short_high
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 1.8 5.2965n 1.8 5.3465n 0)
Ven en_sig 0 DC 1.8
Vdd vdd 0 DC 1.8
.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 driver2_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 15.3465n 4n
.end
