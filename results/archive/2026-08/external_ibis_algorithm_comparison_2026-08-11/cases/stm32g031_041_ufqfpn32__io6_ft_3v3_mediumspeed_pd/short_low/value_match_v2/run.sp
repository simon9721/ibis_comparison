* Experimental pybis model-adaptive interrupted-transition comparison
.title stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_mediumspeed_pd / short_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 3.3 41.485435n 3.3 41.535435n 0 43.869458415n 0 43.919458415n 3.3)
Ven en_sig 0 DC 0
Vdd vdd 0 DC 3.3
.include 'algorithm.sub'
XDRV pad_n in_dig en_sig vdd 0 io6_ft_3v3_mediumspeed_pd_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 80.354893415n 40.485435n
.end
