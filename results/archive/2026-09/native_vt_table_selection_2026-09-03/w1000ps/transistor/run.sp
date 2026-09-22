* io_buf transistor
.title io_buf transistor
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5.0n 0  5.001n 3.3  6.0n 3.3  6.001n 0  22.0n 0)
.include 'hspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF
Vdd_src vdd_src 0 DC 3.3
Rvdd vdd_src vdd 1
Cdec vdd 0 10p
Voe oe 0 DC 3.3
XDUT in_dig oe pad in_sense vdd 0 SPICE_BUF
Rload pad 0 50.0
Cload pad 0 2.0p
.probe tran V(pad)
.tran 0.002n 22.0n
.end
