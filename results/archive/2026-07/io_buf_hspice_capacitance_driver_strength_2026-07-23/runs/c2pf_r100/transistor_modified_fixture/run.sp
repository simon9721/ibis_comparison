* io_buf transistor capacitance/driver-strength investigation
.title io_buf transistor C=2pF R=100ohm
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(0n 0 5n 0 5.001n 3.3 15n 3.3 15.001n 0 25n 0)
Vdd_src vdd_src 0 DC 3.3
Rvdd vdd_src vdd_ref 1
Cdec vdd_ref 0 10p
Voe_src oe_src 0 DC 3.3
Roe oe_src oe_ref 1

.include 'hspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XBUF in_dig oe_ref pad in_sense vdd_ref 0 SPICE_BUF
Rload pad 0 100
Cload pad 0 2p

.probe tran V(in_dig) V(pad) V(vdd_ref) V(xbuf.n2) V(xbuf.n3) I(Vdd_src)
.tran 0.001n 25n
.end
