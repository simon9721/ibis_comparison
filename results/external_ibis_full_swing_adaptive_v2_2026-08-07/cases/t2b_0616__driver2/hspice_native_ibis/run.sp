* Generic full-transition native-IBIS comparison
.title t2b_0616.ibs / driver2
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PULSE(0 1.8 5n 0.05n 0.05n 15n 60.2n)

VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig pc_ref gc_ref
+ file='t2b_0616.ibs'
+ model='driver2'
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
.tran 0.001n 30.1n
.end
