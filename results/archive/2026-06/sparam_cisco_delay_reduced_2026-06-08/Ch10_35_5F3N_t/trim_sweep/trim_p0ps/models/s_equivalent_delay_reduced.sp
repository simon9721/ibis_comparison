* Reduced delay-aware Cisco S-parameter macromodel
* Fitted for 50 ohm source/load transient waveform correlation.
.subckt s_equivalent p1 p2 p3 p4
Tdelay p1 0 ndelay 0 Z0=50 TD=13.8499999979n
Rdelay_term ndelay 0 50
Rleak_p2 p2 0 1e12
Rleak_p4 p4 0 1e12
Ebuf0 fsrc0 0 ndelay 0 1
Rlp1 fsrc0 f1 1000
Clp1 f1 0 1.28673584783e-14
Ebuf1 fsrc1 0 f1 0 1
Rlp2 fsrc1 f2 1000
Clp2 f2 0 1.31443304801e-14
Ebuf2 fsrc2 0 f2 0 1
Rlp3 fsrc2 f3 1000
Clp3 f3 0 1.33293653518e-14
Ebuf3 fsrc3 0 f3 0 1
Rlp4 fsrc3 f4 1000
Clp4 f4 0 3.91021429425e-13
Eout outdrv 0 f4 0 1.75604166722
Rout outdrv p3 50
.ends s_equivalent
