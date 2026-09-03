* realistic-pulse HSPICE native IBIS
.title ex2 fast_5ps native IBIS edge_100ps_visible_short_low_100ps
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.1n 3.3
+ 10n 3.3
+ 10.1n 0
+ 10.1n 0
+ 10.2n 3.3
+ 20n 3.3 )

VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='input.ibs' model='driver' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd
Rload pad_ibis 0 50
Cload pad_ibis 0 2p

.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran 0.002n 20n
.end
