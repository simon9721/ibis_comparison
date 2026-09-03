* Corrected io_buf HSPICE transistor reference
* Original HSPICE MOS card; ideal supply; 1 ps command; 50 ohm || 2 pF
.title corrected transistor reference short_pulse_2ns_high
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0.000000n 0.000000
+ 5.000000n 0.000000
+ 5.001000n 3.300000
+ 7.000000n 3.300000
+ 7.001000n 0.000000
+ 15.000000n 0.000000 )

Vdd_src vdd_ref 0 DC 3.3
Voe_src oe_ref 0 DC 3.3

.include 'hspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF

XBUF in_dig oe_ref pad in_sense vdd_ref 0 SPICE_BUF
Rload pad 0 50
Cload pad 0 2p

.probe tran V(in_dig) V(pad) V(xbuf.n2) V(xbuf.n3)
.tran 0.001n 15.000000n
.end
