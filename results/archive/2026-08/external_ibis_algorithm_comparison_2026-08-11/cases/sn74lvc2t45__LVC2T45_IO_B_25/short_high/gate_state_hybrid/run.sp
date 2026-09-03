* Experimental pybis model-adaptive interrupted-transition comparison
.title sn74lvc2t45.ibs / LVC2T45_IO_B_25 / short_high
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 2.5 9.722625n 2.5 9.772625n 0)
Ven en_sig 0 DC 2.5
Vdd vdd 0 DC 2.5
.include 'algorithm.sub'
XDRV pad_n in_dig en_sig vdd 0 LVC2T45_IO_B_25_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 19.772625n 4n
.end
