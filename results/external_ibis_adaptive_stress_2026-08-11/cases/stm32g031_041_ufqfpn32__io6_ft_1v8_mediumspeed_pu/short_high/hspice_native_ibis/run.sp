* Model-adaptive interrupted-transition stress reference
.title stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pu / short_high
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL(0n 0 5n 0 5.05n 1.8 6.686626625n 1.8 6.736626625n 0)
Ven en_sig 0 DC 0
VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig en_sig dig_q pc_ref gc_ref
+ file='stm32g031_041_ufqfpn32.ibs'
+ model='io6_ft_1v8_mediumspeed_pu'
+ typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
+ xv_pu=ku xv_pd=kd

Rdig dig_q 0 1k
Rload pad_h 0 50
Cload pad_h 0 2p
.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran 0.001n 100.579469125n 4n
.end
