* ============================================================
* Compact ngspice comparison bench:
* transistor-level reference SPICE vs converted IBIS-SPICE
*
* This follows the same spirit as SPISim's short validation flow:
* a single pulse stimulus, short run time, and a 50 ohm delayed load.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

* Shared input stimulus
Vin in_dig 0 PULSE(0 3.3 1n 5p 5p 1.5n 3n)

* Independent rails so supply currents can be observed separately later
Vdd_ref  vdd_ref  0  DC 3.3
Vdd_ibis vdd_ibis 0  DC 3.3
Ven_ref  oe_ref   0  DC 3.3
Ven_ibis en_ibis  0  DC 3.3

* ---- Transistor-level reference SPICE buffer ----
.subckt SPICE_BUF in oe out in_sense vdd vss
.include '../hspice_ngspice.mod'
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
.tran 10p 20n

.end
