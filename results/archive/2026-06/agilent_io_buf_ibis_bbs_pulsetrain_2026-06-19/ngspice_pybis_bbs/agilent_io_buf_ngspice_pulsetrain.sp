* ngspice: pybis io_buf driving BBS converted Agilent_E5071B channel, repeated pulses
* Port convention matches HSPICE deck: p1=Tx, p3=RX observed.
.temp 27
.options method=gear maxord=2 reltol=2e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin  in_dig  0  PWL(
+ 0 0
+ 1e-09 0
+ 1.005e-09 3.3
+ 2e-09 3.3
+ 2.005e-09 0
+ 3e-09 0
+ 3.005e-09 3.3
+ 4e-09 3.3
+ 4.005e-09 0
+ 5e-09 0
+ 5.005e-09 3.3
+ 6e-09 3.3
+ 6.005e-09 0
+ 7e-09 0
+ 7.005e-09 3.3
+ 8e-09 3.3
+ 8.005e-09 0
+ 9e-09 0
+ 9.005e-09 3.3
+ 1e-08 3.3
+ 1.0005e-08 0
+ 1.1e-08 0
+ 1.1005e-08 3.3
+ 1.2e-08 3.3
+ 1.2005e-08 0
+ 1.3e-08 0
+ 1.3005e-08 3.3
+ 1.4e-08 3.3
+ 1.4005e-08 0
+ 1.5e-08 0
+ 1.5005e-08 3.3
+ 1.6e-08 3.3
+ 1.6005e-08 0
+ 1.7e-08 0
+ 1.7005e-08 3.3
+ 1.8e-08 3.3
+ 1.8005e-08 0
+ 1.9e-08 0
+ 1.9005e-08 3.3
+ 2e-08 3.3
+ 2.0005e-08 0
+ 2.1e-08 0
+ 2.4e-08 0)
Ven  en_sig  0  DC 3.3
Vdd  vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  p1  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

.include 'agilent_bbs_wrapper.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rterm_p2  p2  0  75
Rterm_p3  p3  0  75
Rterm_p4  p4  0  75

.save V(in_dig) V(p1) V(p2) V(p3) V(p4) V(xdrv.ku) V(xdrv.kd)
.tran 2p 2.4e-08
.end
