* Generated HSPICE transistor/subcircuit RSF bench for inv_chain
.option post=2 probe accurate
.temp 27

Vin in_src 0 PULSE(0 1.8 1n 5p 5p 3n 20n)
Rin in_src in_dig 1

Vdd_ref vdd_ref_src 0 DC 1.8
Rvdd_ref vdd_ref_src vdd_ref 1
Cdec_ref vdd_ref 0 10p

.include 'invchain_ref_ngspice.sub'

XREF in_dig pad_ref vdd_ref 0 invchain_ref
TREF pad_ref 0 ntst_ref 0 Z0=50 TD=30p
RREF ntst_ref 0 50

.probe tran V(in_dig) V(pad_ref) V(ntst_ref)

.tran 10p 7n
.end
