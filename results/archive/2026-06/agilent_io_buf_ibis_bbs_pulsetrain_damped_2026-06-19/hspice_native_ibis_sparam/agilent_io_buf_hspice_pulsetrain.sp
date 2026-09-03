* HSPICE: io_buf native IBIS driving Agilent_E5071B.s4p, repeated pulses
* Port convention: p1=Tx driven by IBIS, p2=near-side unused, p3=RX observed, p4=far-side unused.
* All non-driven channel ports are matched to 75 ohms, matching the Touchstone R 75 reference.
.option post=2 probe accurate
.option ingold=2
.temp 27

VPU  pu_ref  0  DC 3.3
VPD  pd_ref  0  DC 0
VPC  pc_ref  0  DC 3.3
VGC  gc_ref  0  DC 0

Vin  in_dig  0  PWL(
+ 0 0
+ 1e-09 0
+ 1.5e-09 3.3
+ 6e-09 3.3
+ 6.5e-09 0
+ 1.1e-08 0
+ 1.15e-08 3.3
+ 1.6e-08 3.3
+ 1.65e-08 0
+ 2.1e-08 0
+ 2.15e-08 3.3
+ 2.6e-08 3.3
+ 2.65e-08 0
+ 3.1e-08 0
+ 3.15e-08 3.3
+ 3.6e-08 3.3
+ 3.65e-08 0
+ 4.1e-08 0
+ 4.4e-08 0)
Ven  en_sig  0  DC 3.3

BIBIS pu_ref pd_ref drv_out in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2

Rdig  dig_q  0  1k
Rsrc  drv_out  p1  75


Schannel  p1  p2  p3  p4  0  MNAME=agilent_ch
Rterm_p2  p2  0  75
Rterm_p3  p3  0  75
Rterm_p4  p4  0  75

.MODEL agilent_ch S
+ TSTONEFILE='Agilent_E5071B.s4p'
+ Z0=75
+ RATIONAL_FUNC=1
+ INTERPOLATION=HYBRID
+ LOWPASS=1
+ HIGHPASS=3
+ PASSIVE=1

.probe tran V(in_dig) V(p1) V(p2) V(p3) V(p4) V(dig_q)
.tran 2p 4.4e-08
.end
