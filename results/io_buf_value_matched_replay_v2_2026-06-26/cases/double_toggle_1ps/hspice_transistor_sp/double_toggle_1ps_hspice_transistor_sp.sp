* io_buf transistor-level HSPICE value-matched replay redo reference
* Sweep case: double_toggle_1ps
* 1 ps high then 1 ps low double toggle, 50 ohm + 2 pF
.title io_buf HSPICE transistor io_buf.sp pad reference double_toggle_1ps
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+     5.001n      3.3
+     5.001n      3.3
+     5.002n        0
+     5.002n        0
+     5.003n      3.3
+      12.5n      3.3 )

Vdd_src vdd_src 0 DC 3.3
Rvdd vdd_src vdd_ref 1
Cdec vdd_ref 0 10p
Voe_src oe_src 0 DC 3.3
Roe oe_src oe_ref 1

.include 'hspice_ngspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XSP in_dig oe_ref pad_sp in_sense_sp vdd_ref 0 SPICE_BUF
Rload pad_sp 0 50
Cload pad_sp 0 2p

.probe tran V(in_dig) V(pad_sp) V(in_sense_sp)
.tran 0.001n 12.5n
.end
