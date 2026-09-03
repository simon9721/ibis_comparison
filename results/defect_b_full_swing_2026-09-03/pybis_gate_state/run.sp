* io_buf pybis InputDrivenGateStateHybrid, full swing
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 0  5n 0  5.001n 3.3  15n 3.3  15.001n 0  22n 0)
Ven EN 0 DC 3.3
X1 OUT IN EN VCC 0 driver_OutputInput_Typical
Rload OUT 0 50.0
Cload OUT 0 2.0p
.tran 0.0005n 22.0n
.save V(OUT)
.end
