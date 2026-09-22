* base8 pybis, C_comp override
.include driver.sub
Vdd VCC 0 DC 1.8
Vin IN 0 PWL(0n 0  5n 0  5.001n 1.8  15n 1.8  15.001n 0  22n 0)
Ven EN 0 DC 1.8
X1 OUT IN EN VCC 0 driver2_OutputInput_Typical C_comp=0.000000e+00
Rload OUT 0 1000.0
Cload OUT 0 5.0p
.tran 0.001n 22.0n
.save V(OUT)
.end
