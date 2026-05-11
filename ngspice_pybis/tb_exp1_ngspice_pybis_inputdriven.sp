* ============================================================
* Ngspice comparison bench using pybis2spice input-driven model
* Matches tb_exp1.sp topology:
*   PRBS stimulus -> converted IBIS driver -> channel.sp -> 85 ohm load
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

* Supplies / enable
Vsupply vdd 0 DC 3.3
Ven     en_sig 0 DC 3.3

* Same PRBS waveform as the HSPICE bench, converted to an ngspice B-source.
.include 'prbs11_ngspice.inc'

* Converted pybis2spice output model with SPISim-style input edge control.
.include 'driver_OutputInput_Typical.sub'
XDRV  tx_out  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

* HSPICE B-element exposes dig_q. This mirrors its logical observation node.
Bdig  dig_q  0  V = (V(in_dig) > 1.4) ? 0.5 : 0
Rdig  dig_q  0  1k

* Same 10-section channel and termination as tb_exp1.sp.
.include 'channel.sp'
Rterm  n10b  0  85

.save V(tx_out) V(n10b) V(dig_q) V(in_dig) V(xdrv.ku) V(xdrv.kd)

.control
set filetype=ascii
tran 10p 2u uic
let lin-tstart = 0
let lin-tstop = 2u
let lin-tstep = 10p
linearize V(tx_out) V(n10b) V(dig_q) V(in_dig) V(xdrv.ku) V(xdrv.kd)
write tb_exp1_ngspice_pybis_inputdriven.raw V(tx_out) V(n10b) V(dig_q) V(in_dig) V(xdrv.ku) V(xdrv.kd)
.endc

.end
