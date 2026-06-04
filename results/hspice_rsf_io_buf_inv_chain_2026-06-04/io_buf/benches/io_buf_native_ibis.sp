* Generated HSPICE native IBIS RSF bench for io_buf
.option post=2 probe accurate
.temp 27

Vin in_dig 0 PWL(0 0 1n 0 1.005n 3.3 9n 3.3 9.005n 0)

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
+ ramp_rwf=2
+ ramp_fwf=2

Rdig dig_q 0 1k

TIBIS pad_ibis 0 ntst_ibis 0 Z0=50 TD=30p
RIBIS ntst_ibis 0 50

.probe tran V(in_dig) V(pad_ibis) V(ntst_ibis) V(dig_q)
.tran 10p 12n
.end
