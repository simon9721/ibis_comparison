* Model-adaptive interrupted-transition stress reference
.title hct1g08.ibs / HCT1G08_OUTN_50 / short_low
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL(0n 5 5n 5 5.05n 0 6.3325n 0 6.3825n 5)

VPU pu_ref 0 DC 5
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 5
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig pc_ref gc_ref
+ file='hct1g08.ibs'
+ model='HCT1G08_OUTN_50'
+ typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
+ xv_pu=ku xv_pd=kd


Rload pad_h 0 50
Cload pad_h 0 2p
.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran 0.001n 16.3825n 4n
.end
