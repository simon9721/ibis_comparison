* ============================================================
* Medium ngspice verification bench for pybis2spice input-driven model
* Same topology as tb_exp1_ngspice_pybis_inputdriven.sp, 500 ns stop time.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vsupply vdd 0 DC 3.3
Ven     en_sig 0 DC 3.3

.include 'prbs11_ngspice.inc'
.include 'driver_OutputInput_Typical.sub'
XDRV  tx_out  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

Bdig  dig_q  0  V = (V(in_dig) > 1.4) ? 0.5 : 0
Rdig  dig_q  0  1k

.include 'channel.sp'
Rterm  n10b  0  85

.save V(tx_out) V(n10b) V(dig_q) V(in_dig) V(xdrv.ku) V(xdrv.kd)

.control
set filetype=ascii
tran 10p 500n uic
linearize V(tx_out) V(n10b) V(dig_q) V(in_dig) V(xdrv.ku) V(xdrv.kd)
write tb_exp1_ngspice_pybis_inputdriven_500n.raw V(tx_out) V(n10b) V(dig_q) V(in_dig) V(xdrv.ku) V(xdrv.kd)
.endc

.end
