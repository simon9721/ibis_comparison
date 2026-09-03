* reproduce s2ibispy waveform characterization timing
.title io_buf direct transistor t0 edge
.option post=2 probe accurate
.option ingold=2
.temp 27
Vin in_dig 0 PULSE(0 3.3 0 5p 5p 12n 24.01n)
Vdd_src vdd_ref 0 DC 3.3
Voe_src oe_ref 0 DC 3.3
.include 'hspice.mod'
.subckt SPICE_BUF in oe out in_sense vdd vss
.include 'io_buf.sp'
.ends SPICE_BUF
XBUF in_dig oe_ref pad in_sense vdd_ref 0 SPICE_BUF
Rload pad 0 50
Cload pad 0 0.001p
.probe tran V(in_dig) V(pad) V(xbuf.n2) V(xbuf.n3)
.tran 0.001n 6n
.end
