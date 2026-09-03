* ex2 HSPICE transistor reference
.title ex2 transistor short_pulse_50ps_high
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 3.3
+ 5.05n 3.3
+ 5.051n 0
+ 12n 0 )

Vdd vdd 0 DC 3.3
.include 'hspice.mod'
.subckt ex2_buffer in out vdd gnd
.include 'buffer.sp'
.ends ex2_buffer
XREF in_dig pad_sp vdd 0 ex2_buffer

Rload pad_sp 0 50.0
Cload pad_sp 0 2.0p
.probe tran V(in_dig) V(pad_sp)
.tran 0.002n 12n
.end
