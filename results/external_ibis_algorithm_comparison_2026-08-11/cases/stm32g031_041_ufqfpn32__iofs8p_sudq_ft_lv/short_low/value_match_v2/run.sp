* Experimental pybis model-adaptive interrupted-transition comparison
.title stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_lv / short_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 1.8 27.07102125n 1.8 27.12102125n 0 31.0996646224n 0 31.1496646224n 1.8)
Ven en_sig 0 DC 0
Vdd vdd 0 DC 1.8
.include 'algorithm.sub'
XDRV pad_n in_dig en_sig vdd 0 iofs8p_sudq_ft_lv_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 53.1706858724n 26.07102125n
.end
