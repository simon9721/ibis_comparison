* ex2 HSPICE native IBIS
.title ex2 native IBIS short_pulse_50ps_low
.option post=2 probe accurate ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 3.3
+ 10n 3.3
+ 10.001n 0
+ 10.05n 0
+ 10.051n 3.3
+ 17n 3.3 )

VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
+ file='ex2.ibs'
+ model='driver'
+ buffer=2 typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
+ xv_pu=ku xv_pd=kd

Rload pad_ibis 0 50.0
Cload pad_ibis 0 2.0p
.probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
.tran 0.002n 17n
.end
