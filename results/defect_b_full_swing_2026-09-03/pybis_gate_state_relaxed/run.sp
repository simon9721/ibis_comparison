* io_buf gate-state full swing [relaxed]
.options reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 0  5n 0  5.001n 3.3  15n 3.3  15.001n 0  22n 0)
Ven EN 0 DC 3.3
X1 OUT IN EN VCC 0 driver_OutputInput_Typical
Rload OUT 0 50
Cload OUT 0 2p
.tran 0.002n 22n
.save V(OUT)
.end
