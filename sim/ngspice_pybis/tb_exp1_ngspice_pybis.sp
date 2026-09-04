* ============================================================
* tb_exp1_ngspice_pybis.sp - Experiment 1 ngspice/pybis2spice bench
* Matches tb_exp1.sp topology: PRBS -> IO driver -> 10-section RLGC -> 85 ohm
*
* Difference from HSPICE ground truth:
*   HSPICE uses native IBIS B_IO with file='io_buf.ibs'.
*   This bench uses pybis2spice-derived SPICE tables in
*   driver_Output_Typical_ext.sub. The pybis2spice output oscillator is
*   replaced by external Ku/Kd controls driven by the same PRBS input.
* ============================================================

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

* ---- Supply / enable placeholders to mirror HSPICE bench nodes ----
Vsupply  vdd     0  DC 3.3
Ven      en_sig  0  DC 3.3

* ---- Stimulus: same PRBS11 waveform as tb_exp1.sp ----
.include 'prbs11_ngspice.inc'

* ---- pybis2spice-derived output driver with external digital input ----
* Node order: OUT IN
.include 'driver_Output_Typical_ext.sub'
XDRV  tx_out  in_dig  driver_Output_Typical_ext

* Digital replica probe node, for naming parity with HSPICE bench.
Bdig  dig_q  0  V = (V(in_dig) > 1.65) ? 0.5 : 0
Rdig  dig_q  0  1k

* ---- Channel: same 10-section RLGC ladder ----
.include 'channel.sp'

* ---- Termination: same 85 ohm to ground at receiver end ----
Rterm  n10b  0  85

* ---- Save only the comparable signals ----
.save V(tx_out) V(n10b) V(dig_q) V(in_dig)

.control
set filetype=ascii
tran 10p 2u uic
write tb_exp1_ngspice_pybis.raw V(tx_out) V(n10b) V(dig_q) V(in_dig)
.endc

.end
