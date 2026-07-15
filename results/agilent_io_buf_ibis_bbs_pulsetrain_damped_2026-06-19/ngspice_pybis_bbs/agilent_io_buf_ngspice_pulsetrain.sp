* ngspice: pybis io_buf driving BBS converted Agilent_E5071B channel, repeated pulses
* Port convention matches HSPICE deck: p1=Tx, p3=RX observed.
.temp 27
.options method=gear maxord=2 reltol=2e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

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
Vdd  vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  drv_out  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
Rsrc  drv_out  p1  75


.include 'agilent_bbs_wrapper.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rterm_p2  p2  0  75
Rterm_p3  p3  0  75
Rterm_p4  p4  0  75

.save V(in_dig) V(p1) V(p2) V(p3) V(p4) V(xdrv.ku) V(xdrv.kd)
.tran 2p 4.4e-08
.end
