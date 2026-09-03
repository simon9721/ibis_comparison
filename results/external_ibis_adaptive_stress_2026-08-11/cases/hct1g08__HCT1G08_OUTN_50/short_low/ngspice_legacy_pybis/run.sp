* Model-adaptive interrupted-transition legacy-pybis stress case
.title hct1g08.ibs / HCT1G08_OUTN_50 / short_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(0n 5 5n 5 5.05n 0 6.3325n 0 6.3825n 5)
Ven en_sig 0 DC 5
Vdd vdd 0 DC 5
.include 'legacy.sub'
XDRV pad_n in_dig en_sig vdd 0 HCT1G08_OUTN_50_OutputInput_Typical
Rload pad_n 0 50
Cload pad_n 0 2p
.save V(in_dig) V(pad_n) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 16.3825n 4n
.end
