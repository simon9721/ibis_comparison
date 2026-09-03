* Parallel delay-aware Cisco S-parameter macromodel
* Fitted for 50 ohm source/load transient waveform correlation.
.subckt s_equivalent p1 p2 p3 p4
Tdelay p1 0 ndelay 0 Z0=50 TD=13.9203145088n
Rdelay_term ndelay 0 50
Rleak_p2 p2 0 1e12
Rleak_p4 p4 0 1e12
Rsum sum 0 1
Ebrsrc1 brsrc1 0 ndelay 0 1
Rbr1 brsrc1 br1 1000
Cbr1 br1 0 1.12562822291e-13
Gsum1 0 sum br1 0 0.301769612445
Ebrsrc2 brsrc2 0 ndelay 0 1
Rbr2 brsrc2 br2 1000
Cbr2 br2 0 2.80436908566e-13
Gsum2 0 sum br2 0 0.40509949562
Ebrsrc3 brsrc3 0 ndelay 0 1
Rbr3 brsrc3 br3 1000
Cbr3 br3 0 6.64271027929e-13
Gsum3 0 sum br3 0 0.014232732604
Ebrsrc4 brsrc4 0 ndelay 0 1
Rbr4 brsrc4 br4 1000
Cbr4 br4 0 1.7237995722e-12
Gsum4 0 sum br4 0 0.172378645101
Eout outdrv 0 sum 0 2
Rout outdrv p3 50
.ends s_equivalent
