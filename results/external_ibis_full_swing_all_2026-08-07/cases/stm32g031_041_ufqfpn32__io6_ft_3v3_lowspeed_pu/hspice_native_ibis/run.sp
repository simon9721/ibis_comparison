* Generic full-transition native-IBIS comparison
.title stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed_pu
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PULSE(0 3.3 5n 50p 50p 15n 40n)
Ven en_sig 0 DC 0
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig en_sig dig_q pc_ref gc_ref
+ file='stm32g031_041_ufqfpn32.ibs'
+ model='io6_ft_3v3_lowspeed_pu'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rdig dig_q 0 1k
Rload pad_h 0 50
Cload pad_h 0 2p

.probe tran V(in_dig) V(pad_h) V(ku) V(kd)
.tran 0.001n 35n
.end
