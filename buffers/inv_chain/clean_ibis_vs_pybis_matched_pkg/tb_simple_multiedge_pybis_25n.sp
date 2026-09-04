* ============================================================
* Simple 50-ohm/30 ps validation fixture with a deterministic
* multi-transition pattern for pybis timing-offset study.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

* Pattern after initial low:
*   1 0 1 1 0 0 1 0
* Transition order: R F R F R F
Vin in_src 0 PWL(0 0  1n 0  1.005n 1.8  4n 1.8  4.005n 0  7n 0  7.005n 1.8  13n 1.8  13.005n 0  19n 0  19.005n 1.8  22n 1.8  22.005n 0  25n 0)
Rin in_src in_dig 1
Ven en_sig 0 DC 1.8
Vdd vdd 0 DC 1.8

.include 'driver2_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver2_OutputInput_Typical

T1 pad 0 ntst 0 Z0=50 Td=30p
R1 ntst 0 50

.save V(in_dig) V(pad) V(ntst)
.tran 10p 25n

.end
