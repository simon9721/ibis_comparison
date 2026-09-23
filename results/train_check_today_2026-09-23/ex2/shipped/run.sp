.options reltol=0.001 abstol=1e-09 vntol=1e-06 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 0  5n 0  5.05n 3.3  5.858n 3.3  5.908n 0  6.716n 0  6.766n 3.3  7.574n 3.3  7.624n 0  8.432n 0  8.482n 3.3  9.29n 3.3  9.34n 0  10.148n 0  10.198n 3.3  11.006n 3.3  11.056n 0  11.864n 0  11.914n 3.3  12.722n 3.3  12.772n 0  13.58n 0  13.63n 3.3  14.438n 3.3  14.488n 0  15.296n 0  15.346n 3.3  16.154n 3.3  16.204n 0  17.012n 0  17.062n 3.3  17.87n 3.3  17.92n 0  24.728n 0)
Ven EN 0 DC 0
X1 OUT IN EN VCC 0 driver_OutputInput_Typical
Rload OUT 0 50
Cload OUT 0 2p
.tran 0.002n 24.728n
.save V(OUT)
.end
