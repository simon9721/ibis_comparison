* HSPICE testbench: IBIS Tx + S-parameter channel (Clarity_example.S2P)
* PrimeSim HSPICE T-2022.06

.option post=2 probe accurate
.temp 27

* --- Supplies ---
VPU  pu_ref  0  DC 3.3
VPD  pd_ref  0  DC 0
VPC  pc_ref  0  DC 3.3
VGC  gc_ref  0  DC 0

* --- Stimulus ---
Vin  in_dig  0  PWL(0 0 1n 0 1.005n 3.3 9n 3.3 9.005n 0)
Ven  en_sig  0  DC 3.3

* --- IBIS buffer ---
BIBIS pu_ref pd_ref pad_ibis in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ ramp_rwf=2
+ ramp_fwf=2
Rdig  dig_q  0  1k

* --- 2-port S-parameter channel ---
* port1=pad_ibis (Tx), port2=rx_node (Rx), ref=GND
Schannel  pad_ibis  rx_node  0  MNAME=ch_model

.MODEL ch_model S
+ TSTONEFILE='Clarity_example.S2P'
+ Z0=50
+ RATIONAL_FUNC=1
+ INTERPOLATION=HYBRID
+ LOWPASS=1
+ HIGHPASS=3
+ PASSIVE=1

* --- Rx termination ---
Rterm  rx_node  0  50

* --- Probes ---
.probe tran V(in_dig) V(pad_ibis) V(rx_node) V(dig_q)

.tran 10p 12n
.end
