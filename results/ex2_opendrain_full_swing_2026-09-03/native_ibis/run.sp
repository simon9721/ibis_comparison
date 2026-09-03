* ex2 open-drain native IBIS, pull-up load
.title ex2 open-drain native IBIS
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5.0n 0  5.001n 3.3  15.0n 3.3  15.001n 0  22.0n 0)
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='ex2_opendrain.ibs' model='driver' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2
Rpu pad_ibis od_rail 50.0
Vodrail od_rail 0 DC 3.3
Cload pad_ibis 0 2.0p
.probe tran V(in_dig) V(pad_ibis)
.tran 0.001n 22.0n
.end
