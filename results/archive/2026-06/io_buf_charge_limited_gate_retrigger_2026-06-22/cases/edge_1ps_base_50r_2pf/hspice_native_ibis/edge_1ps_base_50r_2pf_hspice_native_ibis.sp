* io_buf native IBIS HSPICE directional Ku/Kd extraction
* Sweep case: edge_1ps_base_50r_2pf
* Baseline 1 ps rise/fall, 50 ohm + 2 pF
.title io_buf HSPICE native IBIS Ku/Kd extraction edge_1ps_base_50r_2pf
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+        15n      3.3
+    15.001n        0
+        25n        0 )

Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig en_sig dig_q pc_ref gc_ref
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
Rload pad_ibis 0 50
Cload pad_ibis 0 2p

.probe tran V(in_dig) V(pad_ibis) V(dig_q) V(ku) V(kd)
.tran 0.001n 25n
.end
