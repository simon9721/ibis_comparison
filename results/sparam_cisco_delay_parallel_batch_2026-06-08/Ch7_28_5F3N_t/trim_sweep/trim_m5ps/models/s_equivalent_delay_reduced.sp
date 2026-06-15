* Parallel delay-aware Cisco S-parameter macromodel
* Fitted for 50 ohm source/load transient waveform correlation.
.subckt s_equivalent p1 p2 p3 p4
Tdelay p1 0 ndelay 0 Z0=50 TD=7.39257517685n
Rdelay_term ndelay 0 50
Rleak_p2 p2 0 1e12
Rleak_p4 p4 0 1e12
Rsum sum 0 1
Ebrsrc1 brsrc1 0 ndelay 0 1
Rbr1 brsrc1 br1 1000
Cbr1 br1 0 6.95380116145e-14
Gsum1 0 sum br1 0 0.278440734434
Ebrsrc2 brsrc2 0 ndelay 0 1
Rbr2 brsrc2 br2 1000
Cbr2 br2 0 1.54323828862e-13
Gsum2 0 sum br2 0 0.0661332581691
Ebrsrc3 brsrc3 0 ndelay 0 1
Rbr3 brsrc3 br3 1000
Cbr3 br3 0 2.31395906147e-13
Gsum3 0 sum br3 0 0.437027175153
Ebrsrc4 brsrc4 0 ndelay 0 1
Rbr4 brsrc4 br4 1000
Cbr4 br4 0 1.28161754535e-12
Gsum4 0 sum br4 0 0.0909822150945
Etailfsrc1 tailfsrc1 0 ndelay 0 1
Rtailf1 tailfsrc1 tailf1 1000
Ctailf1 tailf1 0 8.75052665472e-13
Gtailf1 0 sum tailf1 0 0.0261652261795
Etailssrc1 tailssrc1 0 ndelay 0 1
Rtails1 tailssrc1 tails1 1000
Ctails1 tails1 0 2.21005600003e-12
Gtails1 0 sum tails1 0 -0.0261652261795
Eout outdrv 0 sum 0 2
Rout outdrv p3 50
.ends s_equivalent
