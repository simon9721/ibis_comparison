* ============================================================
* D2 — Channel isolation: refspice + Rload + PRBS7 1000ns
* Issue dimension D2: does the channel (T-line) cause stalls?
* Counterpart: tb_refspice_prbs7_batch.sp (T-line, known good)
* This bench removes T-line so D1 vs D2 can be diffed.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10

.include 'prbs7_vstim.inc'
Rin    in_src  in_dig  1

Vdd_ref  vdd_ref_src  0  DC 3.3
Voe_ref  oe_ref_src   0  DC 3.3
Rvdd_ref vdd_ref_src  vdd_ref  1
Roe_ref  oe_ref_src   oe_ref   1
Cdec_ref vdd_ref      0        10p

.subckt SPICE_BUF in oe out in_sense vdd vss
.include '../hspice_ngspice.mod'
.include '../io_buf.sp'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF

* D2: Rload only — channel removed
Rload  pad_ref  0  50

.save V(in_dig) V(pad_ref)
.tran 10p 1000n

.end
