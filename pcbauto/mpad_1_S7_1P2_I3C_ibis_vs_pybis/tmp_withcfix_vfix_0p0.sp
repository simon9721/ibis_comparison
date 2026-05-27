.temp 50
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12
Vin in_src 0 PULSE(0 1.2 5n 5p 5p 30n 140n)
Rin in_src in_dig 1
Ven en_sig 0 DC 0.0
Vdd vdd 0 DC 1.2
Vfix vfix 0 DC 0.0
.include 'C:/Users/simom/Desktop/IBIS_Comparison/pcbauto/mpad_1_S7_1P2_I3C_ibis_vs_pybis/mpad_1_S7_1P2_I3C-with_cfixsolve.sub'
XDRV pad in_dig en_sig vdd 0 mpad_1_S7_1P2_I3C_OutputInput_Typical
Rload pad vfix 1000.0
Cload pad 0 2e-11
.save V(in_dig) V(pad)
.tran 25p 70.0n
.end
