* Generic full-transition native-IBIS comparison
.title stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd_lv
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PULSE(0 1.8 5n 0.05n 0.05n 281.28n 1395.58n)
Ven en_sig 0 DC 0
VPU pu_ref 0 DC 1.8
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 1.8
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_h in_dig en_sig dig_q pc_ref gc_ref
+ file='stm32g031_041_ufqfpn32.ibs'
+ model='iols8p_sudq_ft_pd_lv'
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
.tran 0.0069779n 697.79n
.end
