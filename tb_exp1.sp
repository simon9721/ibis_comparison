* ============================================================
* tb_exp1.sp  —  Experiment 1: HSPICE Native IBIS (Ground Truth)
* Missouri S&T EMC Lab — IBIS Comparison Study — April 2026
*
* Buffer : io_buf.ibs  |  Model : driver  (I/O, Active-High enable)
* Channel: channel.sp  (10-section RLGC ladder, 10 cm FR4)
* Stimulus: prbs11.pwl (400 bits, UI=5 ns / 200 Mbps, 0-3.3 V)
* ============================================================

.option post=2
.option accurate
.temp 27

* ---- Supply ----
Vsupply  vdd  0  DC 3.3

* ---- Enable: hold HIGH to keep I/O buffer in output (drive) mode ----
* Active-High enable — tied to vdd (3.3 V)
Ven  en_sig  0  DC 3.3

* ---- Stimulus: PRBS11 PWL, 0-3.3V swing ----
Vstim  in_dig  0  PWL PWLFILE='prbs11.pwl'

* ---- I/O buffer as output driver (B_IO, 8-node form) ----
* Node order: nd_pu  nd_pd  nd_out  nd_in  nd_en  nd_out_of_in  nd_pc  nd_gc
*
* nd_pu   : vcc_node  — HSPICE ties to 3.3V internally (power=on)
* nd_pd   : gnd_node  — HSPICE ties to 0V internally (power=on)
* nd_out  : tx_out    — analog output, drives channel input
* nd_in   : in_dig    — digital stimulus (PRBS11 PWL)
* nd_en   : en_sig    — enable held at 3.3V (Active-High, always enabled)
* nd_out_of_in: dig_q — digital output replica; weak pull-down, probe only
* nd_pc   : pc_node   — HSPICE ties to 3.3V internally (power=on)
* nd_gc   : gc_node   — HSPICE ties to 0V internally (power=on)
*
B_drv  vcc_node  gnd_node  tx_out  in_dig  en_sig  dig_q  pc_node  gc_node
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=on
+ ramp_rwf=2
+ ramp_fwf=2

* Weak pull-down on nd_out_of_in — gives it a DC path, probe-able
Rdig  dig_q  0  1k

* ---- Channel: 10-section RLGC ladder ----
* tx_out is ch_in (direct connection via shared node name)
* ch_out is n10b — connects to termination below
.include 'channel.sp'

* ---- Termination: 85 Ohm to GND at receiver end ----
Rterm  n10b  0  75

* ---- Analysis ----
.TRAN 10p 2u

* ---- Probes ----
.probe tran V(tx_out) V(n10b) V(dig_q)
* Optional supply rail checks (should be flat at 3.3V with power=on):
* .probe tran V(vcc_node) V(pc_node)

.end
