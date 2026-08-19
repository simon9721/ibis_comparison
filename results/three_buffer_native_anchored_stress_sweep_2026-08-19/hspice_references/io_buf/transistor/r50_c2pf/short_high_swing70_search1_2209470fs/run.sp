* realistic-pulse transistor reference
.title io_buf transistor short_high_swing70_search1_2209470fs
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 3.3
+ 7.20947n 3.3
+ 7.25947n 0
+ 22n 0 )

.include 'hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF
Vdd_src vdd_src 0 DC 3.3
Rvdd vdd_src vdd 1
Cdec vdd 0 10p
Voe oe 0 DC 3.3
XDUT in_dig oe pad_sp in_sense vdd 0 SPICE_BUF
Rload pad_sp 0 50
Cload pad_sp 0 2p

.probe tran V(in_dig) V(pad_sp) v(xdut.n2) v(xdut.n3)
.tran 0.002n 22n
.end
