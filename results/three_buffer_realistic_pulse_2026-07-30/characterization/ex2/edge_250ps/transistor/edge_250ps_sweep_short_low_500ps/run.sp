* realistic-pulse transistor reference
.title ex2 transistor edge_250ps_sweep_short_low_500ps
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.25n 3.3
+ 10n 3.3
+ 10.25n 0
+ 10.5n 0
+ 10.75n 3.3
+ 20n 3.3 )

.include 'hspice.mod'
.subckt EX2_BUFFER in out vdd gnd
.include 'buffer.sp'
.ends EX2_BUFFER
Vdd vdd 0 DC 3.3
XDUT in_dig pad_sp vdd 0 EX2_BUFFER
Rload pad_sp 0 50
Cload pad_sp 0 2p

.probe tran V(in_dig) V(pad_sp) v(xdut.n4)
.tran 0.002n 20n
.end
