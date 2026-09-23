.options reltol=0.001 abstol=1e-09 vntol=1e-06 gmin=1e-10 method=gear
.include driver.sub
Vdd VCC 0 DC 3.3
Vin IN 0 PWL(0n 3.3  5n 3.3  5.05n 0  5.22n 0  5.27n 3.3  22n 3.3)
Ven EN 0 DC 3.3
X1 OUT IN EN VCC 0 driver_OutputInput_Typical
Rload OUT 0 50
Cload OUT 0 2p
.tran 0.002n 22.0n
.save V(OUT) V(X1.ku) V(X1.kd) V(X1.gup) V(X1.guptarget) V(X1.kugate_base) V(X1.kugate_on) V(X1.kugate_off) V(X1.kures_table) V(X1.gdn) V(X1.gdntarget) V(X1.kdgate_base) V(X1.pucmdlvl) V(X1.pup5) V(X1.pup6) V(X1.pucmdraw)
.end
