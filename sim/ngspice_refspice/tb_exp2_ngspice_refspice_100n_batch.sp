* ============================================================
* Ngspice comparison bench using transistor-level reference SPICE
* Short 100 ns batch/raw variant for fast validation.
* Adapted from tb_exp2.sp to use ngspice-compatible PRBS stimulus.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

.subckt SPICE_BUF in oe out in_sense vdd vss
.include '../models/hspice_ngspice.mod'
.include '../models/io_buf.sp'
.ends SPICE_BUF

Vsupply vdd 0 DC 3.3
Vgnd    vss 0 DC 0
Voe     oe_sig 0 DC 3.3

.include '../ngspice_pybis/prbs11_ngspice.inc'

X1 in_dig oe_sig tx_out in_sense vdd vss SPICE_BUF

.include '../channels/channel.sp'
Rterm n10b 0 85

.save V(tx_out) V(n10b) V(in_sense) V(in_dig)
.tran 10p 100n

.end
