* Model-adaptive interrupted-transition legacy-pybis stress case
.title test.ibs / driver / short_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 3.3 5n 3.3 5.05n 0 5.6314n 0 5.6814n 3.3)
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3
.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 driver_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 15.6814n 4n
.end
