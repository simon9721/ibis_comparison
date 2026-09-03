* convergence gate, HSPICE native IBIS
.title inv_chain_fast_5ps_tr200ps
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5n 0  5.001n 1.8  15n 1.8  15.001n 0  22n 0)
VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='inv_chain_fast_5ps_tr200ps.ibs' model='driver2' buffer=2 typ=typ power=off
+ interpol=1 ramp_rwf=2 ramp_fwf=2
Rload pad_ibis 0 50.0
Cload pad_ibis 0 2p
.probe tran V(in_dig) V(pad_ibis)
.tran 0.001n 22n
.end
