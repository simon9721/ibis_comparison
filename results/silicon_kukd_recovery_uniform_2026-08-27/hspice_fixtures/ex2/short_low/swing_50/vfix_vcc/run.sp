* realistic-pulse transistor reference
.title ex2 transistor short_low_swing50
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 3.3
+ 10n 3.3
+ 10.05n 0
+ 10.440682n 0
+ 10.490682n 3.3
+ 22n 3.3 )

.include 'hspice.mod'
.subckt EX2_BUFFER in out vdd gnd
.include 'buffer.sp'
.ends EX2_BUFFER
Vdd vdd 0 DC 3.3
XDUT in_dig pad_sp vdd 0 EX2_BUFFER

Vfix fix 0 DC 3.3
Rfix pad_sp fix 50
.probe tran V(in_dig) V(pad_sp)
.tran 0.002n 22n
.end
