* Generated HSPICE transistor/subcircuit RSF bench for io_buf regenerated tr/tf=5ps
.option post=2 probe accurate
.temp 27

Vin in_src 0 PULSE(0 3.3 1n 5p 5p 8n 20n)
Rin in_src in_dig 1

Vdd_ref vdd_ref_src 0 DC 3.3
Voe_ref oe_ref_src 0 DC 3.3
Rvdd_ref vdd_ref_src vdd_ref 1
Roe_ref oe_ref_src oe_ref 1
Cdec_ref vdd_ref 0 10p

.include 'hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF
TREF pad_ref 0 ntst_ref 0 Z0=50 TD=30p
RREF ntst_ref 0 50

.probe tran V(in_dig) V(pad_ref) V(ntst_ref) V(in_sense_ref)

.tran 10p 14n
.end
