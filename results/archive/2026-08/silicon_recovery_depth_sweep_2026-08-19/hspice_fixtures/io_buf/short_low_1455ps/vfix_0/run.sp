* realistic-pulse transistor reference
.title io_buf transistor short_low_1455ps
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 3.3
+ 10n 3.3
+ 10.05n 0
+ 11.4545454545n 0
+ 11.5045454545n 3.3
+ 22n 3.3 )

.include 'hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF
Vdd_src vdd_src 0 DC 3.3
Rvdd vdd_src vdd 1
Cdec vdd 0 10p
Voe oe 0 DC 3.3
XDUT in_dig oe pad_sp in_sense vdd 0 SPICE_BUF

Vfix fix 0 DC 0
Rfix pad_sp fix 50
.probe tran V(in_dig) V(pad_sp)
.tran 0.002n 22n
.end
