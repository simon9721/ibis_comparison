* realistic-pulse transistor reference
.title inv_chain transistor short_low_swing90
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 1.8
+ 10n 1.8
+ 10.05n 0
+ 10.111029n 0
+ 10.161029n 1.8
+ 22n 1.8 )

.include 'invchain_ref_ngspice.sub'
Vdd vdd 0 DC 1.8
XDUT in_dig pad_sp vdd 0 invchain_ref

Vsense pad_sp fixa DC 0
Rfix fixa fix 50
Vfix fix 0 DC 1.8
.probe tran V(in_dig) V(pad_sp) I(Vsense)
.tran 0.002n 22n
.end
