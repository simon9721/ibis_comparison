* Parallel delay-aware Cisco S-parameter macromodel
* Fitted for 50 ohm source/load transient waveform correlation.
.subckt s_equivalent p1 p2 p3 p4
* S11-like input reflection correction for the 50 ohm audit bench.
Rtxsum txsum 0 1
Etxsrc1 txsrc1 0 pin 0 1
Rtx1 txsrc1 tx1 1000
Ctx1 tx1 0 2e-14
Gtx1 0 txsum tx1 0 -0.0668618762889
Etxsrc2 txsrc2 0 pin 0 1
Rtx2 txsrc2 tx2 1000
Ctx2 tx2 0 1.47361259946e-13
Gtx2 0 txsum tx2 0 -0.089937283081
Etxsrc3 txsrc3 0 pin 0 1
Rtx3 txsrc3 tx3 1000
Ctx3 tx3 0 1.08576704664e-12
Gtx3 0 txsum tx3 0 0.135962133338
Etxsrc4 txsrc4 0 pin 0 1
Rtx4 txsrc4 tx4 1000
Ctx4 tx4 0 8e-12
Gtx4 0 txsum tx4 0 0.0671684897216
Etxtailfsrc1 txtailfsrc1 0 pin 0 1
Rtxtailf1 txtailfsrc1 txtailf1 1000
Ctx_tailf1 txtailf1 0 5e-14
Gtxtailf1 0 txsum txtailf1 0 0.112541841966
Etxtailssrc1 txtailssrc1 0 pin 0 1
Rtxtails1 txtailssrc1 txtails1 1000
Ctx_tails1 txtails1 0 2e-12
Gtxtails1 0 txsum txtails1 0 -0.112541841966
Etxport p1 pin txsum 0 1
Rpin_leak pin 0 1e12
Tdelay pin 0 ndelay 0 Z0=50 TD=12.4399775476n
Rdelay_term ndelay 0 50
Rleak_p2 p2 0 1e12
Rleak_p4 p4 0 1e12
Rsum sum 0 1
Ebrsrc1 brsrc1 0 ndelay 0 1
Rbr1 brsrc1 br1 1000
Cbr1 br1 0 6.15234219784e-14
Gsum1 0 sum br1 0 0.386835070947
Ebrsrc2 brsrc2 0 ndelay 0 1
Rbr2 brsrc2 br2 1000
Cbr2 br2 0 1.91641697705e-13
Gsum2 0 sum br2 0 0.758313964618
Ebrsrc3 brsrc3 0 ndelay 0 1
Rbr3 brsrc3 br3 1000
Cbr3 br3 0 3.01851382258e-13
Gsum3 0 sum br3 0 -0.421735231323
Ebrsrc4 brsrc4 0 ndelay 0 1
Rbr4 brsrc4 br4 1000
Cbr4 br4 0 3.52142109851e-13
Gsum4 0 sum br4 0 0.177677958381
Etailfsrc1 tailfsrc1 0 ndelay 0 1
Rtailf1 tailfsrc1 tailf1 1000
Ctailf1 tailf1 0 3.50171621291e-14
Gtailf1 0 sum tailf1 0 -0.262692353085
Etailssrc1 tailssrc1 0 ndelay 0 1
Rtails1 tailssrc1 tails1 1000
Ctails1 tails1 0 1.02266936534e-12
Gtails1 0 sum tails1 0 0.262692353085
Eout outdrv 0 sum 0 2
Rout outdrv p3 50
.ends s_equivalent
