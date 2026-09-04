* variant stressed native
.title stressed native
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5n 0  5.001n 1.8  5.17n 1.8  5.171n 0  22n 0)
VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='input.ibs' model='driver2' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2
Rload pad 0 50.0
Cload pad 0 2.0p
.probe tran V(pad)
.tran 0.002n 22.0n
.end
