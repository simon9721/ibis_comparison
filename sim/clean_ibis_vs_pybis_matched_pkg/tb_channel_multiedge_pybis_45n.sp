* ============================================================
* Actual RLGC channel with the same deterministic multi-transition
* pattern for pybis timing-offset study.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_src 0 PWL(0 0  1.5n 0  1.7n 3.3  6.5n 3.3  6.7n 0  11.5n 0  11.7n 3.3  21.5n 3.3  21.7n 0  31.5n 0  31.7n 3.3  36.5n 3.3  36.7n 0  45n 0)
Rin in_src in_dig 1
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV tx_out in_dig en_sig vdd 0 driver_OutputInput_Typical

.include 'channel.sp'
Rterm n10b 0 85

.save V(in_dig) V(tx_out) V(n10b) V(xdrv.ku) V(xdrv.kd)
.tran 10p 45n

.end
