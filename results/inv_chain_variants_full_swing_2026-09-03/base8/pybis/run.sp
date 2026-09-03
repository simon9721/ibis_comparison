* invchain_base8_tr1ps pybis subcircuit
.include driver.sub
Vdd VCC 0 DC 1.8
Vin IN 0 PWL(0n 0  5.0n 0  5.001n 1.8  15.0n 1.8  15.001n 0  22.0n 0)
Ven EN 0 DC 1.8
X1 OUT IN EN VCC 0 driver2_OutputInput_Typical
Rload OUT 0 50.0
Cload OUT 0 2.0p
.tran 0.001n 22.0n
.save V(OUT) V(IN)
.end
