* realistic-pulse transistor reference
.title inv_chain transistor edge_250ps_sweep_short_high_375ps
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.25n 1.8
+ 5.375n 1.8
+ 5.625n 0
+ 20n 0 )

.include 'invchain_ref_ngspice.sub'
Vdd vdd 0 DC 1.8
XDUT in_dig pad_sp vdd 0 invchain_ref
Rload pad_sp 0 50
Cload pad_sp 0 2p

.probe tran V(in_dig) V(pad_sp) v(xdut.vout7)
.tran 0.002n 20n
.end
