* variant stressed transistor
.title stressed transistor
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5n 0  5.001n 3.3  6.3n 3.3  6.301n 0  22n 0)
.include 'hspice.mod'
.subckt EX2B in out vdd gnd
.include 'buffer.sp'
.ends EX2B
Vdd vdd 0 DC 3.3
XDUT in_dig pad vdd 0 EX2B
Rload pad 0 50.0
Cload pad 0 2.0p
.probe tran V(pad)
.tran 0.002n 22.0n
.end
