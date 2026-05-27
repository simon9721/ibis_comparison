* ============================================================
* Simple 50-ohm/30 ps validation fixture with a deterministic
* multi-transition pattern for reference SPICE timing-offset study.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10

Vin in_src 0 PWL(0 0  1n 0  1.005n 1.8  4n 1.8  4.005n 0  7n 0  7.005n 1.8  13n 1.8  13.005n 0  19n 0  19.005n 1.8  22n 1.8  22.005n 0  25n 0)
Rin in_src in_dig 1

Vdd_ref  vdd_ref_src  0  DC 1.8
Rvdd_ref vdd_ref_src  vdd_ref  1
Cdec_ref vdd_ref      0        10p

.include 'invchain_ref_ngspice.sub'

XREF in_dig pad_ref vdd_ref 0 invchain_ref

TREF  pad_ref  0  ntst_ref  0  Z0=50 Td=30p
RREF  ntst_ref 0  50

.save V(in_dig) V(pad_ref) V(ntst_ref)
.tran 10p 25n

.end
