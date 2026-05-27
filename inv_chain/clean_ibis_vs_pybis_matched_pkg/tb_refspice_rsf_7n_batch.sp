* ============================================================
* Clean RSF validation bench for the original transistor-level
* inverter-chain reference SPICE in ngspice.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10

Vin in_src 0 PULSE(0 1.8 1n 5p 5p 3n 20n)
Rin in_src in_dig 1

Vdd_ref  vdd_ref_src  0  DC 1.8
Rvdd_ref vdd_ref_src  vdd_ref  1
Cdec_ref vdd_ref      0        10p

.include 'invchain_ref_ngspice.sub'

XREF in_dig pad_ref vdd_ref 0 invchain_ref

TREF  pad_ref  0  ntst_ref  0  Z0=50 Td=30p
RREF  ntst_ref 0  50

.save V(in_dig) V(pad_ref) V(ntst_ref)
.tran 10p 7n

.end
