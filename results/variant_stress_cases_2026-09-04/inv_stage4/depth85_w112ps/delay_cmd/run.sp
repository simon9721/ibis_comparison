* variant stressed pybis, state probed
.options reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC 1.8
Vin IN 0 PWL(0n 0  5n 0  5.001n 1.8  5.1119n 1.8  5.1129n 0  22n 0)
Ven EN 0 DC 1.8
X1 OUT IN EN VCC 0 driver2_OutputInput_Typical
Rload OUT 0 50.0
Cload OUT 0 2.0p
.tran 0.002n 22.0n
.save V(OUT) V(X1.Ku) V(X1.Kd)
.end
