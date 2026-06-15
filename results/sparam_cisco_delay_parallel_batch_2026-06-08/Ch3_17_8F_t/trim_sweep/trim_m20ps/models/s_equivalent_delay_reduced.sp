* Parallel delay-aware Cisco S-parameter macromodel
* Fitted for 50 ohm source/load transient waveform correlation.
.subckt s_equivalent p1 p2 p3 p4
Tdelay p1 0 ndelay 0 Z0=50 TD=4.38858771089n
Rdelay_term ndelay 0 50
Rleak_p2 p2 0 1e12
Rleak_p4 p4 0 1e12
Rsum sum 0 1
Ebrsrc1 brsrc1 0 ndelay 0 1
Rbr1 brsrc1 br1 1000
Cbr1 br1 0 6.97571327213e-14
Gsum1 0 sum br1 0 0.535800430468
Ebrsrc2 brsrc2 0 ndelay 0 1
Rbr2 brsrc2 br2 1000
Cbr2 br2 0 4.05686928428e-13
Gsum2 0 sum br2 0 0.0487082821226
Ebrsrc3 brsrc3 0 ndelay 0 1
Rbr3 brsrc3 br3 1000
Cbr3 br3 0 5.30983759984e-13
Gsum3 0 sum br3 0 0.157402698655
Ebrsrc4 brsrc4 0 ndelay 0 1
Rbr4 brsrc4 br4 1000
Cbr4 br4 0 1.82003491371e-12
Gsum4 0 sum br4 0 0.0585096402792
Etailfsrc1 tailfsrc1 0 ndelay 0 1
Rtailf1 tailfsrc1 tailf1 1000
Ctailf1 tailf1 0 5.95840029783e-14
Gtailf1 0 sum tailf1 0 0.156420232774
Etailssrc1 tailssrc1 0 ndelay 0 1
Rtails1 tailssrc1 tails1 1000
Ctails1 tails1 0 1.17956265536e-11
Gtails1 0 sum tails1 0 -0.156420232774
Eout outdrv 0 sum 0 2
Rout outdrv p3 50
.ends s_equivalent
