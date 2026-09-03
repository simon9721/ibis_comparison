* realistic-pulse transistor reference
.title inv_chain transistor short_high_w318ps_318ps
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 1.8
+ 5.3182n 1.8
+ 5.3682n 0
+ 22n 0 )

.include 'invchain_ref_ngspice.sub'
Vdd vdd 0 DC 1.8
XDUT in_dig pad_sp vdd 0 invchain_ref
Rload pad_sp 0 50
Cload pad_sp 0 2p

.probe tran V(in_dig) V(pad_sp) v(xdut.vout7)
.tran 0.002n 22n
.end
