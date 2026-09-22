* realistic-pulse HSPICE native IBIS
.title inv_chain slow_1ns native IBIS short_high_500ps
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 1.8
+ 5.5n 1.8
+ 5.55n 0
+ 22n 0 )

VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='input.ibs' model='driver2' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd
Rload pad_ibis 0 25
Cload pad_ibis 0 0p

.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran 0.002n 22n
.end
