* Touchstone-only reduced S-parameter macromodel
* Scope: matched 50 ohm transient channel qualification, not arbitrary termination replacement.
.subckt s_equivalent p1 p2 p3 p4
* Touchstone-derived input reflection correction.
Rtxsum txsum 0 1
Etxsrc1 txsrc1 0 pin 0 1
Rtx1 txsrc1 tx1 1000
Ctx1 tx1 0 1e-14
Gtx1 0 txsum tx1 0 0.817901772249
Etxsrc2 txsrc2 0 pin 0 1
Rtx2 txsrc2 tx2 1000
Ctx2 tx2 0 3e-14
Gtx2 0 txsum tx2 0 1.15470647813
Etxsrc3 txsrc3 0 pin 0 1
Rtx3 txsrc3 tx3 1000
Ctx3 tx3 0 8e-14
Gtx3 0 txsum tx3 0 0.777652718931
Etxsrc4 txsrc4 0 pin 0 1
Rtx4 txsrc4 tx4 1000
Ctx4 tx4 0 2e-13
Gtx4 0 txsum tx4 0 -1.64543755633
Etxsrc5 txsrc5 0 pin 0 1
Rtx5 txsrc5 tx5 1000
Ctx5 tx5 0 7e-13
Gtx5 0 txsum tx5 0 -1.05312513316
Etxtailfsrc1 txtailfsrc1 0 pin 0 1
Rtxtailf1 txtailfsrc1 txtailf1 1000
Ctx_tailf1 txtailf1 0 2e-14
Gtxtailf1 0 txsum txtailf1 0 -2.02615344278
Etxtailssrc1 txtailssrc1 0 pin 0 1
Rtxtails1 txtailssrc1 txtails1 1000
Ctx_tails1 txtails1 0 4e-13
Gtxtails1 0 txsum txtails1 0 2.02615344278
Etxtailfsrc2 txtailfsrc2 0 pin 0 1
Rtxtailf2 txtailfsrc2 txtailf2 1000
Ctx_tailf2 txtailf2 0 8e-14
Gtxtailf2 0 txsum txtailf2 0 -0.211682731766
Etxtailssrc2 txtailssrc2 0 pin 0 1
Rtxtails2 txtailssrc2 txtails2 1000
Ctx_tails2 txtails2 0 2e-12
Gtxtails2 0 txsum txtails2 0 0.211682731766
Etxport p1 pin txsum 0 1
Rpin_leak pin 0 1e12
Tdelay pin 0 ndelay 0 Z0=50 TD=8.60390943027n
Rdelay_term ndelay 0 50
Rleak_p2 p2 0 1e12
Rleak_p4 p4 0 1e12
Rsum sum 0 1
Ebrsrc1 brsrc1 0 ndelay 0 1
Rbr1 brsrc1 br1 1000
Cbr1 br1 0 3e-14
Gsum1 0 sum br1 0 -0.00387609250433
Ebrsrc2 brsrc2 0 ndelay 0 1
Rbr2 brsrc2 br2 1000
Cbr2 br2 0 8e-14
Gsum2 0 sum br2 0 0.00102962350814
Ebrsrc3 brsrc3 0 ndelay 0 1
Rbr3 brsrc3 br3 1000
Cbr3 br3 0 2e-13
Gsum3 0 sum br3 0 0.000147355399957
Ebrsrc4 brsrc4 0 ndelay 0 1
Rbr4 brsrc4 br4 1000
Cbr4 br4 0 7e-13
Gsum4 0 sum br4 0 -0.000464076488747
Ebrsrc5 brsrc5 0 ndelay 0 1
Rbr5 brsrc5 br5 1000
Cbr5 br5 0 2.5e-12
Gsum5 0 sum br5 0 0.000549455479895
Ebrsrc6 brsrc6 0 ndelay 0 1
Rbr6 brsrc6 br6 1000
Cbr6 br6 0 8e-12
Gsum6 0 sum br6 0 0.000106687839352
Etailfsrc1 tailfsrc1 0 ndelay 0 1
Rtailf1 tailfsrc1 tailf1 1000
Ctailf1 tailf1 0 5e-14
Gtailf1 0 sum tailf1 0 0.0016150185554
Etailssrc1 tailssrc1 0 ndelay 0 1
Rtails1 tailssrc1 tails1 1000
Ctails1 tails1 0 2e-12
Gtails1 0 sum tails1 0 -0.0016150185554
Etailfsrc2 tailfsrc2 0 ndelay 0 1
Rtailf2 tailfsrc2 tailf2 1000
Ctailf2 tailf2 0 2e-13
Gtailf2 0 sum tailf2 0 4.0667560584e-05
Etailssrc2 tailssrc2 0 ndelay 0 1
Rtails2 tailssrc2 tails2 1000
Ctails2 tails2 0 8e-12
Gtails2 0 sum tails2 0 -4.0667560584e-05
Eout outdrv 0 sum 0 2
Rout outdrv p3 50
.ends s_equivalent
