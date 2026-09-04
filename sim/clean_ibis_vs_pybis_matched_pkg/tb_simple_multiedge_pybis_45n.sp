* ============================================================
* Simple 50-ohm/30 ps validation fixture with a deterministic
* multi-transition pattern for pybis timing-offset study.
* ============================================================

.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

* Pattern after initial low:
*   1 0 1 1 0 0 1 0
* Transition order: R F R F R F
Vin in_src 0 PWL(0 0  1.5n 0  1.7n 3.3  6.5n 3.3  6.7n 0  11.5n 0  11.7n 3.3  21.5n 3.3  21.7n 0  31.5n 0  31.7n 3.3  36.5n 3.3  36.7n 0  45n 0)
Rin in_src in_dig 1
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

T1 pad 0 ntst 0 Z0=50 Td=30p
R1 ntst 0 50

.save V(in_dig) V(pad) V(ntst)
.tran 20p 45n

.end
