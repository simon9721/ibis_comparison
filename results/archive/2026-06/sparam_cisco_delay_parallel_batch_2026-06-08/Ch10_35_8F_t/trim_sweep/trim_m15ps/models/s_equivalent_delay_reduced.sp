* Parallel delay-aware Cisco S-parameter macromodel
* Fitted for 50 ohm source/load transient waveform correlation.
.subckt s_equivalent p1 p2 p3 p4
Tdelay p1 0 ndelay 0 Z0=50 TD=13.885n
Rdelay_term ndelay 0 50
Rleak_p2 p2 0 1e12
Rleak_p4 p4 0 1e12
Rsum sum 0 1
Ebrsrc1 brsrc1 0 ndelay 0 1
Rbr1 brsrc1 br1 1000
Cbr1 br1 0 2.67921043698e-14
Gsum1 0 sum br1 0 -0.105488798726
Ebrsrc2 brsrc2 0 ndelay 0 1
Rbr2 brsrc2 br2 1000
Cbr2 br2 0 2.81355489909e-14
Gsum2 0 sum br2 0 -0.0496817669817
Ebrsrc3 brsrc3 0 ndelay 0 1
Rbr3 brsrc3 br3 1000
Cbr3 br3 0 1.36378721099e-13
Gsum3 0 sum br3 0 0.722030902063
Ebrsrc4 brsrc4 0 ndelay 0 1
Rbr4 brsrc4 br4 1000
Cbr4 br4 0 9.99697532144e-13
Gsum4 0 sum br4 0 0.320102288404
Etailfsrc1 tailfsrc1 0 ndelay 0 1
Rtailf1 tailfsrc1 tailf1 1000
Ctailf1 tailf1 0 8.31441379866e-14
Gtailf1 0 sum tailf1 0 -0.0623060150147
Etailssrc1 tailssrc1 0 ndelay 0 1
Rtails1 tailssrc1 tails1 1000
Ctails1 tails1 0 1.27649529575e-13
Gtails1 0 sum tails1 0 0.0623060150147
Eout outdrv 0 sum 0 2
Rout outdrv p3 50
.ends s_equivalent
