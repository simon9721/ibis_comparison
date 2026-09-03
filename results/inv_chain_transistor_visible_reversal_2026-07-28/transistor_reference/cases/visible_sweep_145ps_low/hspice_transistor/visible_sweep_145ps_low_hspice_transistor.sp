* inv_chain HSPICE transistor reference
* case: visible_sweep_145ps_low
.title inv_chain transistor visible_sweep_145ps_low
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 1.8
+ 10n 1.8
+ 10.001n 0
+ 10.145n 0
+ 10.146n 1.8
+ 14n 1.8 )

Vdd vdd 0 DC 1.8
.include 'invchain_ref_ngspice.sub'
XREF in_dig pad_sp vdd 0 invchain_ref

Rload pad_sp 0 50.0
Cload pad_sp 0 2.0p

.probe tran V(in_dig) V(pad_sp)
.tran 0.001n 14n
.end
