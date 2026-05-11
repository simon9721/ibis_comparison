* ============================================================
* D1 — Driver isolation: refspice + Rload + RSF (200ps tr/tf)
* Issue dimension D1: does the driver subcircuit alone converge?
* Channel: pure resistive load (no T-line)
* Input:   PWL RSF, 200ps tr/tf, 10ns hold
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10

Vin    in_src  0  PWL(0 0  1n 0  1.2n 3.3  11.2n 3.3  11.4n 0  21.4n 0)
Rin    in_src  in_dig  1

Vdd_ref  vdd_ref_src  0  DC 3.3
Voe_ref  oe_ref_src   0  DC 3.3
Rvdd_ref vdd_ref_src  vdd_ref  1
Roe_ref  oe_ref_src   oe_ref   1
Cdec_ref vdd_ref      0        10p

.subckt SPICE_BUF in oe out in_sense vdd vss
.include '../models/hspice_ngspice.mod'
.include '../models/io_buf.sp'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF

* D1: Rload only — no T-line
Rload  pad_ref  0  50

.save V(in_dig) V(pad_ref)
.tran 10p 22n

.end
