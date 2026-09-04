* ============================================================
* Simple 50-ohm/30 ps validation fixture with a deterministic
* multi-transition pattern for reference SPICE timing-offset study.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10

Vin in_src 0 PWL(0 0  1.5n 0  1.7n 3.3  6.5n 3.3  6.7n 0  11.5n 0  11.7n 3.3  21.5n 3.3  21.7n 0  31.5n 0  31.7n 3.3  36.5n 3.3  36.7n 0  45n 0)
Rin in_src in_dig 1

Vdd_ref  vdd_ref_src 0 DC 3.3
Voe_ref  oe_ref_src  0 DC 3.3
Rvdd_ref vdd_ref_src vdd_ref 1
Roe_ref  oe_ref_src oe_ref 1
Cdec_ref vdd_ref 0 10p

.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'hspice_ngspice.mod'
.include 'io_buf.sp'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF

T1 pad_ref 0 ntst_ref 0 Z0=50 Td=30p
R1 ntst_ref 0 50

.save V(in_dig) V(pad_ref) V(ntst_ref) V(in_sense_ref)
.tran 10p 45n

.end
