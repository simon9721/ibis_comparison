* Model-adaptive interrupted-transition legacy-pybis stress case
.title sn74lvc2t45.ibs / LVC2T45_IO_B_18 / short_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 1.8 5n 1.8 5.05n 0 11.59473625n 0 11.64473625n 1.8)
Ven en_sig 0 DC 1.8
Vdd vdd 0 DC 1.8
.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 LVC2T45_IO_B_18_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 27.11348625n 4n
.end
