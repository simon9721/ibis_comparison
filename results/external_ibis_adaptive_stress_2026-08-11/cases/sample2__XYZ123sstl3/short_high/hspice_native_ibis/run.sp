* Model-adaptive interrupted-transition stress reference
.title sample2.ibs / XYZ123sstl3 / short_high
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 3.3 5.52415n 3.3 5.57415n 0)

VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig pc_ref gc_ref
+ file='sample2.ibs'
+ model='XYZ123sstl3'
+ typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
+ xv_pu=ku xv_pd=kd


Rload pad_h 0 50
Cload pad_h 0 2p
.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran 0.001n 15.57415n 4n
.end
