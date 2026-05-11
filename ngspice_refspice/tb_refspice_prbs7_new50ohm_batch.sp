* ============================================================
* PRBS7 transient bench — transistor-level refspice + new 50 ohm channel
* 200 Mbps (5 ns UI), 200 bits = 1000 ns
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
.include '../models/hspice_ngspice.mod'
.include '../models/io_buf.sp'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF

* New 50-ohm RLGC channel ladder (tx_out -> n10b)
RCH_TX  pad_ref tx_out 1u
.include '../new 50ohm channel/channel_ngspice.sp'
RTERM   n10b 0 50

.save V(in_dig) V(pad_ref) V(tx_out) V(n10b) V(in_sense_ref)
.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.tran 10p 1000n uic

.end
