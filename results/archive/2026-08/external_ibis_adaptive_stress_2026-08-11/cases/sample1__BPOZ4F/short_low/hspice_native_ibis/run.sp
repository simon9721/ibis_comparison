* Model-adaptive interrupted-transition stress reference
.title sample1.ibs / BPOZ4F / short_low
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL(0n 3.3 5n 3.3 5.05n 0 5.60195n 0 5.65195n 3.3)
Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig en_sig pc_ref gc_ref
+ file='sample1.ibs'
+ model='BPOZ4F'
+ typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
+ xv_pu=ku xv_pd=kd


Rload pad_h 0 50
Cload pad_h 0 2p
.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran 0.001n 15.65195n 4n
.end
