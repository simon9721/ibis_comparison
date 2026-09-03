* Generic full-transition native-IBIS comparison
.title inv_s2i.ibs / driver3
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PULSE(0 1.8 5n 50p 50p 15n 40n)

VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig pc_ref gc_ref
+ file='invchain_test_0615_v5_v2.ibs'
+ model='driver3'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd


Rload pad_h 0 50
Cload pad_h 0 2p

.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran 0.001n 35n
.end
