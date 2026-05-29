* I3C_TX_0p125mA_tx pybis2spice ngspice, 5 pulses, 1160 ohm to ground
.temp 25
.options method=gear maxord=2 reltol=1e-4 abstol=1e-12 vntol=1e-7 gmin=1e-12
Vin in_dig 0 PWL(0n 0 10n 0 10.005n 1.2 30n 1.2 30.005n 0 50n 0 50.005n 1.2 70n 1.2 70.005n 0 90n 0 90.005n 1.2 110n 1.2 110.005n 0 130n 0 130.005n 1.2 150n 1.2 150.005n 0 170n 0 170.005n 1.2 190n 1.2 190.005n 0 230n 0)
Ven en_sig 0 DC 1.2
Vdd vdd 0 DC 1.2
.include 'C:/Users/simom/Desktop/Projects/IBIS_Comparison/results/hibiki_i3c_tx_0p125ma_1160ohm_ground_5pulse_ngspice_2026-05-28/converted/I3C_TX_0p125mA_tx_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 I3C_TX_0p125mA_tx_OutputInput_Typical
Rload pad 0 1160.0
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 10.0p 230.0n
.end
