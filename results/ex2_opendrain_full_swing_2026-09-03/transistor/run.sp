* ex2 open-drain transistor, pull-up load
.title ex2 open-drain transistor
.option post=2 probe accurate ingold=2
.temp 27
Vdd vdd 0 DC 3.3
Vin in_dig 0 PWL(0n 0  5.0n 0  5.001n 3.3  15.0n 3.3  15.001n 0  22.0n 0)
.include 'hspice.mod'
.subckt ex2_buffer in out vdd gnd
.include 'buffer.sp'
.ends ex2_buffer
XREF in_dig pad_sp vdd 0 ex2_buffer
Rpu pad_sp vdd 50.0
Cload pad_sp 0 2.0p
.probe tran V(in_dig) V(pad_sp)
.tran 0.001n 22.0n
.end
