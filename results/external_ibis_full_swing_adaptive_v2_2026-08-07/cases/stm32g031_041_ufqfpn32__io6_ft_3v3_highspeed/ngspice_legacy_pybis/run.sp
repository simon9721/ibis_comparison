* Generic full-transition legacy-pybis comparison
.title stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_highspeed
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PULSE(0 3.3 5n 0.05n 0.05n 15n 60.2n)
Ven en_sig 0 DC 0
Vdd vdd 0 DC 3.3

.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 io6_ft_3v3_highspeed_OutputInput_Typical

Rload pad_n 0 50
Cload pad_n 0 2p

.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 30.1n
.end
