* Generic full-transition legacy-pybis comparison
.title stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd_lv
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PULSE(0 1.8 5n 0.05n 0.05n 281.28n 1395.58n)
Ven en_sig 0 DC 0
Vdd vdd 0 DC 1.8

.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 iols8p_sudq_ft_pd_lv_OutputInput_Typical

Rload pad_n 0 50
Cload pad_n 0 2p

.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.0069779n 697.79n
.end
