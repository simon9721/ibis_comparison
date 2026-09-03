* inv_chain HSPICE native IBIS reference
* case: visible_sweep_70ps_low
.title inv_chain native IBIS visible_sweep_70ps_low
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 1.8
+ 10n 1.8
+ 10.001n 0
+ 10.07n 0
+ 10.071n 1.8
+ 14n 1.8 )

VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='inv_chain_slow_1ns.ibs'
+ model='driver2'
+ buffer=2
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rload pad_ibis 0 50.0
Cload pad_ibis 0 2.0p

.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran 0.001n 14n
.end
