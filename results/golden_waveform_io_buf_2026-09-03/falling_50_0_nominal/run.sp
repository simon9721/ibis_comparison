* golden-waveform replay, falling, R=50.0 V=0.0, C_comp=1.200e-12
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 0  2.5n 0  2.501n 3.3  5.0n 3.3  5.001n 0  12n 0)
Ven EN 0 DC 3.3
X1 OUT IN EN VCC 0 driver_OutputInput_Typical C_comp=1.200000e-12
Vfix FIX 0 DC 0.0
Rfix OUT FIX 50.0
.tran 0.0002n 12n
.save V(OUT)
.end
