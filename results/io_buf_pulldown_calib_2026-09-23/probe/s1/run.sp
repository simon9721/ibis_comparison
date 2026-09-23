.options reltol=0.001 abstol=1e-09 vntol=1e-06 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 3.3  5n 3.3  5.05n 0  5.163n 0  5.213n 3.3  12n 3.3)
Ven EN 0 DC 3.3
X1 OUT IN EN VCC 0 driver_OutputInput_Typical
Rload OUT 0 50
Cload OUT 0 2p
.tran 0.002n 12n
.save V(OUT) V(X1.chin) V(X1.stgd1) V(X1.stgd2) V(X1.stgd3) V(X1.gdn) V(X1.kd) V(X1.ku)
.end
