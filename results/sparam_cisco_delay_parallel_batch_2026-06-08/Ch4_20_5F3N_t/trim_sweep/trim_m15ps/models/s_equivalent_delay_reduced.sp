* Parallel delay-aware Cisco S-parameter macromodel
* Fitted for 50 ohm source/load transient waveform correlation.
.subckt s_equivalent p1 p2 p3 p4
Tdelay p1 0 ndelay 0 Z0=50 TD=8.92310771658n
Rdelay_term ndelay 0 50
Rleak_p2 p2 0 1e12
Rleak_p4 p4 0 1e12
Rsum sum 0 1
Ebrsrc1 brsrc1 0 ndelay 0 1
Rbr1 brsrc1 br1 1000
Cbr1 br1 0 3.0351122773e-14
Gsum1 0 sum br1 0 -0.127044506756
Ebrsrc2 brsrc2 0 ndelay 0 1
Rbr2 brsrc2 br2 1000
Cbr2 br2 0 7.74982451314e-14
Gsum2 0 sum br2 0 0.935813330875
Ebrsrc3 brsrc3 0 ndelay 0 1
Rbr3 brsrc3 br3 1000
Cbr3 br3 0 1.01219578097e-12
Gsum3 0 sum br3 0 0.146579166173
Ebrsrc4 brsrc4 0 ndelay 0 1
Rbr4 brsrc4 br4 1000
Cbr4 br4 0 2.41045768746e-12
Gsum4 0 sum br4 0 -0.0136705195908
Etailfsrc1 tailfsrc1 0 ndelay 0 1
Rtailf1 tailfsrc1 tailf1 1000
Ctailf1 tailf1 0 1.65295010216e-14
Gtailf1 0 sum tailf1 0 -0.0423542004226
Etailssrc1 tailssrc1 0 ndelay 0 1
Rtails1 tailssrc1 tails1 1000
Ctails1 tails1 0 6.61578052251e-13
Gtails1 0 sum tails1 0 0.0423542004226
Eout outdrv 0 sum 0 2
Rout outdrv p3 50
.ends s_equivalent
