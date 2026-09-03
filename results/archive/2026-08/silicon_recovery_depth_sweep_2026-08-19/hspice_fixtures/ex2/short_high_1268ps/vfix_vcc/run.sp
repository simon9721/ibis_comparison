* realistic-pulse transistor reference
.title ex2 transistor short_high_1268ps
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 3.3
+ 6.26818181818n 3.3
+ 6.31818181818n 0
+ 22n 0 )

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
