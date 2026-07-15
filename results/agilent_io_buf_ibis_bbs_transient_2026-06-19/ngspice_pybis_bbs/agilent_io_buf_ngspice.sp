* ngspice: pybis io_buf driving BBS converted Agilent_E5071B channel
* Port convention matches HSPICE deck: p1=Tx, p3=RX observed.
.temp 27
.options method=gear maxord=2 reltol=2e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin  in_dig  0  PWL(0 0 1n 0 1.005e-09 3.3 9n 3.3 9.005e-09 0)
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
.tran 2p 12n
.end
