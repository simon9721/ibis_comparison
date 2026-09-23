.options reltol=0.001 abstol=1e-09 vntol=1e-06 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC 1.8
Vin IN 0 PWL(0n 0  5n 0  5.05n 1.8  5.111n 1.8  5.161n 0  5.222n 0  5.272n 1.8  5.333n 1.8  5.383n 0  5.444n 0  5.494n 1.8  5.555n 1.8  5.605n 0  5.666n 0  5.716n 1.8  5.777n 1.8  5.827n 0  5.888n 0  5.938n 1.8  5.999n 1.8  6.049n 0  6.11n 0  6.16n 1.8  6.221n 1.8  6.271n 0  6.332n 0  6.382n 1.8  6.443n 1.8  6.493n 0  6.554n 0  6.604n 1.8  6.665n 1.8  6.715n 0  12.776n 0)
Ven EN 0 DC 1.8
X1 OUT IN EN VCC 0 driver2_OutputInput_Typical
Rload OUT 0 50
Cload OUT 0 2p
.tran 0.002n 12.776n
.save V(OUT)
.end
