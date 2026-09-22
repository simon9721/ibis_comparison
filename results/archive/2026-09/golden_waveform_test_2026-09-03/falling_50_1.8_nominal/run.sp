* golden-waveform replay, falling, R=50.0 V=1.8, C_comp=4.680e-13
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC 1.8
Vin IN 0 PWL(0n 0  2.5n 0  2.501n 1.8  5.0n 1.8  5.001n 0  6.6231n 0)
Ven EN 0 DC 1.8
X1 OUT IN EN VCC 0 driver2_OutputInput_Typical C_comp=4.680000e-13
Vfix FIX 0 DC 1.8
Rfix OUT FIX 50.0
.tran 0.0002n 6.6231n
.save V(OUT)
.end
