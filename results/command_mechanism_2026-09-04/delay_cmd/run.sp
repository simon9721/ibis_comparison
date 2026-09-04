.options reltol=0.001 abstol=1e-09 vntol=1e-06 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 0  5.0n 0  5.001n 3.3  7.354n 3.3  7.355n 0  22.0n 0)
Ven EN 0 DC 3.3
X1 OUT IN EN VCC 0 driver_OutputInput_Typical
Rload OUT 0 50
Cload OUT 0 2p
.tran 0.002n 22.0n
.save V(OUT) V(X1.gupcmd) V(X1.gup) V(X1.ku) V(X1.kd)
.end
