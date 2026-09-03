* Experimental pybis model-adaptive interrupted-transition comparison
.title sample1.ibs / BPS2P10F_PU50K / short_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 3.3 20.05n 3.3 20.1n 0 20.65955n 0 20.70955n 3.3)
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3
.include 'algorithm.sub'
XDRV pad_n in_dig en_sig vdd 0 BPS2P10F_PU50K_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 30.70955n 19.05n
.end
