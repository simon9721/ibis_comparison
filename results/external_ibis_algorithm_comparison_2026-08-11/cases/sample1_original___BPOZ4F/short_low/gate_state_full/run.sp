* Experimental pybis model-adaptive interrupted-transition comparison
.title sample1(original).ibs / BPOZ4F / short_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 3.3 20.05n 3.3 20.1n 0 20.65195n 0 20.70195n 3.3)
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3
.include 'algorithm.sub'
XDRV pad_n in_dig en_sig vdd 0 BPOZ4F_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 30.70195n 19.05n
.end
