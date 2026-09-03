* Generated HSPICE native IBIS RSF bench for inv_chain
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL(0 0 1n 0 1.005n 1.8 4n 1.8 4.005n 0)

VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='t2b_0615_v5.ibs'
+ model='driver2'
+ buffer=2
+ typ=typ
+ power=off
+ ramp_rwf=2
+ ramp_fwf=2

TIBIS pad_ibis 0 ntst_ibis 0 Z0=50 TD=30p
RIBIS ntst_ibis 0 50

.probe tran V(in_dig) V(pad_ibis) V(ntst_ibis)
.tran 10p 6.5n
.end
