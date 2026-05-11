* ============================================================
* Rise-steady-fall ngspice comparison bench:
* transistor-level reference SPICE vs converted IBIS-SPICE
*
* This is the closest compact analogue to the SPISim validation use:
* one rising transition, enough time to settle high, one falling
* transition, and enough time to settle low.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-5 gmin=1e-10 trtol=10 smoothbsrc=1

* Shared input stimulus with modest edge rate for ngspice convergence
Vin in_src 0 PULSE(0 3.3 1n 5p 5p 8n 20n)
Rin in_src in_dig 1

* Independent rails so supply currents can be observed separately later
Vdd_ref  vdd_ref_src  0  DC 3.3
Vdd_ibis vdd_ibis 0  DC 3.3
Ven_ref  oe_ref_src   0  DC 3.3
Ven_ibis en_ibis_src  0  DC 3.3
Rvdd_ref vdd_ref_src  vdd_ref  1
Cdec_ref vdd_ref      0        10p
Roe_ref  oe_ref_src   oe_ref   1
Ren_ibis en_ibis_src  en_ibis  1

* ---- Transistor-level reference SPICE buffer ----
.include '../hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include '../io_buf.sp'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF

* ---- Converted IBIS-SPICE buffer ----
.include '../ngspice_pybis/driver_OutputInput_Typical.sub'
XIBIS pad_ibis in_dig en_ibis vdd_ibis 0 driver_OutputInput_Typical

* ---- SPISim-style validation loads ----
TREF  pad_ref  0  ntst_ref  0  Z0=50 Td=30p
RREF  ntst_ref 0  50

TIBIS pad_ibis 0  ntst_ibis 0  Z0=50 Td=30p
RIBIS ntst_ibis 0 50

.save V(in_dig) V(pad_ref) V(ntst_ref) V(in_sense_ref) V(pad_ibis) V(ntst_ibis) V(xibis.ku) V(xibis.kd)
.tran 20p 12n

.end
