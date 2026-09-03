* golden-waveform replay, rising, R=50.0 V=0.0, C_comp=0.000e+00
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 0  5.0n 0  5.001n 3.3  14n 3.3)
Ven EN 0 DC 0
X1 OUT IN EN VCC 0 driver_OutputInput_Typical C_comp=0.000000e+00
Vfix FIX 0 DC 0.0
Rfix OUT FIX 50.0
.tran 0.0002n 14n
.save V(OUT)
.end
