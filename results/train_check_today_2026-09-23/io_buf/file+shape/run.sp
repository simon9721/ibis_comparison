.options reltol=0.001 abstol=1e-09 vntol=1e-06 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 0  5n 0  5.05n 3.3  6.792n 3.3  6.842n 0  8.584n 0  8.634n 3.3  10.376n 3.3  10.426n 0  12.168n 0  12.218n 3.3  13.96n 3.3  14.01n 0  15.752n 0  15.802n 3.3  17.544n 3.3  17.594n 0  19.336n 0  19.386n 3.3  21.128n 3.3  21.178n 0  22.92n 0  22.97n 3.3  24.712n 3.3  24.762n 0  26.504n 0  26.554n 3.3  28.296n 3.3  28.346n 0  30.088n 0  30.138n 3.3  31.88n 3.3  31.93n 0  39.672n 0)
Ven EN 0 DC 3.3
X1 OUT IN EN VCC 0 driver_OutputInput_Typical
Rload OUT 0 50
Cload OUT 0 2p
.tran 0.002n 39.672n
.save V(OUT)
.end
