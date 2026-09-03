* Generic full-transition legacy-pybis comparison
.title sn74lvc2t45.ibs / LVC2T45_IO_A_25
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PULSE(0 2.5 5n 0.05n 0.05n 15n 60.2n)
Ven en_sig 0 DC 0
Vdd vdd 0 DC 2.5

.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 LVC2T45_IO_A_25_OutputInput_Typical

Rload pad_n 0 50
Cload pad_n 0 2p

.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 30.1n
.end
