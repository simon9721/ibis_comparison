* Model-adaptive interrupted-transition legacy-pybis stress case
.title stm32g031_041_ufqfpn32.ibs / iohs8p_sudq_ft_pu_lv / short_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 1.8 5n 1.8 5.05n 0 7.64377247188n 0 7.69377247188n 1.8)
Ven en_sig 0 DC 0
Vdd vdd 0 DC 1.8
.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 iohs8p_sudq_ft_pu_lv_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 20.1635762219n 4n
.end
