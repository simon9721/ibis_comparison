* Corrected io_buf HSPICE native-IBIS reference
* Regenerated 5 ps IBIS; 1 ps runtime command; 50 ohm || 2 pF
.title corrected native IBIS short_pulse_1ns_high
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0.000000n 0.000000
+ 5.000000n 0.000000
+ 5.001000n 3.300000
+ 6.000000n 3.300000
+ 6.001000n 0.000000
+ 14.000000n 0.000000 )

Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rdig dig_q 0 1k
Rload pad 0 50
Cload pad 0 2p

.probe tran V(in_dig) V(pad) V(ku) V(kd)
.tran 0.001n 14.000000n
.end
