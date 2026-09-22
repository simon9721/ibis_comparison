* ex2 open-drain pybis, pull-up load
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 0  5.0n 0  5.001n 3.3  15.0n 3.3  15.001n 0  22.0n 0)
Ven EN 0 DC 0   $ active-low enable: EN low enables the open-drain
X1 OUT IN EN VCC 0 driver_OutputInput_Typical
Rpu OUT VCC 50.0
Cload OUT 0 2.0p
.tran 0.001n 22.0n
.save V(OUT) V(IN)
.end
