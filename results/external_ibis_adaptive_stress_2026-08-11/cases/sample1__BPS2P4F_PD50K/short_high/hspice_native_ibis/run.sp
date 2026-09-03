* Model-adaptive interrupted-transition stress reference
.title sample1.ibs / BPS2P4F_PD50K / short_high
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 3.3 5.311n 3.3 5.361n 0)
Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig en_sig dig_q pc_ref gc_ref
+ file='sample1.ibs'
+ model='BPS2P4F_PD50K'
+ typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
+ xv_pu=ku xv_pd=kd

Rdig dig_q 0 1k
Rload pad_h 0 50
Cload pad_h 0 2p
.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran 0.001n 15.361n 4n
.end
