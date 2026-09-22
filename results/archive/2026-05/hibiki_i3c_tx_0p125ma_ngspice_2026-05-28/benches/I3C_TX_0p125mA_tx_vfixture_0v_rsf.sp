* I3C_TX_0p125mA_tx pybis2spice ngspice validation, 50 ohm to 0 V fixture
.temp 25
.options method=gear maxord=2 reltol=1e-4 abstol=1e-12 vntol=1e-7 gmin=1e-12
Vin in_dig 0 PULSE(0 1.2 10.0n 5p 5p 120.0n 440.0n)
Ven en_sig 0 DC 1.2
Vdd vdd 0 DC 1.2
.include 'C:/Users/simom/Desktop/Projects/IBIS_Comparison/results/hibiki_i3c_tx_0p125ma_ngspice_2026-05-28/converted/I3C_TX_0p125mA_tx_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 I3C_TX_0p125mA_tx_OutputInput_Typical
Rload pad 0 50.0
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 10.0p 220.0n
.end
