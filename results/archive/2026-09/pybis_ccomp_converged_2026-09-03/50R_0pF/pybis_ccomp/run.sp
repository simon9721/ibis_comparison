* base8 pybis, C_comp override
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC 1.8
Vin IN 0 PWL(0n 0  5n 0  5.001n 1.8  15n 1.8  15.001n 0  22n 0)
Ven EN 0 DC 1.8
X1 OUT IN EN VCC 0 driver2_OutputInput_Typical C_comp=4.680000e-13
Rload OUT 0 50.0
Cload OUT 0 0.0p
.tran 0.0002n 22.0n
.save V(OUT)
.end
