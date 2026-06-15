* 2-port delay-aware reduced S-parameter macromodel
* Fitted for the 50 ohm HSPICE audit bench.
.subckt s_equivalent p1 p2
* S11-like 50 ohm bench input correction.
Rtxsum txsum 0 1
Etxsrc1 txsrc1 0 pin 0 1
Rtx1 txsrc1 tx1 1000
Ctx1 tx1 0 2e-14
Gtx1 0 txsum tx1 0 0.0356164129755
Etxsrc2 txsrc2 0 pin 0 1
Rtx2 txsrc2 tx2 1000
Ctx2 tx2 0 8.94427191e-14
Gtx2 0 txsum tx2 0 0.0261048278976
Etxsrc3 txsrc3 0 pin 0 1
Rtx3 txsrc3 tx3 1000
Ctx3 tx3 0 4e-13
Gtx3 0 txsum tx3 0 -0.0439876971475
Etxsrc4 txsrc4 0 pin 0 1
Rtx4 txsrc4 tx4 1000
Ctx4 tx4 0 1.788854382e-12
Gtx4 0 txsum tx4 0 -0.0427463941705
Etxsrc5 txsrc5 0 pin 0 1
Rtx5 txsrc5 tx5 1000
Ctx5 tx5 0 8e-12
Gtx5 0 txsum tx5 0 0.0254834438171
Etxtailfsrc1 txtailfsrc1 0 pin 0 1
Rtxtailf1 txtailfsrc1 txtailf1 1000
Ctx_tailf1 txtailf1 0 5e-14
Gtxtailf1 0 txsum txtailf1 0 -0.0787096782281
Etxtailssrc1 txtailssrc1 0 pin 0 1
Rtxtails1 txtailssrc1 txtails1 1000
Ctx_tails1 txtails1 0 2e-12
Gtxtails1 0 txsum txtails1 0 0.0787096782281
Etxtailfsrc2 txtailfsrc2 0 pin 0 1
Rtxtailf2 txtailfsrc2 txtailf2 1000
Ctx_tailf2 txtailf2 0 1e-13
Gtxtailf2 0 txsum txtailf2 0 0.0542480171236
Etxtailssrc2 txtailssrc2 0 pin 0 1
Rtxtails2 txtailssrc2 txtails2 1000
Ctx_tails2 txtails2 0 4e-12
Gtxtails2 0 txsum txtails2 0 -0.0542480171236
Etxport p1 pin txsum 0 1
Rpin_leak pin 0 1e12
Tdelay pin 0 ndelay 0 Z0=50 TD=0.287070472192n
Rdelay_term ndelay 0 50
Rsum sum 0 1
Ebrsrc1 brsrc1 0 ndelay 0 1
Rbr1 brsrc1 br1 1000
Cbr1 br1 0 7.97081355817e-14
Gsum1 0 sum br1 0 -0.725419999086
Ebrsrc2 brsrc2 0 ndelay 0 1
Rbr2 brsrc2 br2 1000
Cbr2 br2 0 9.1365848155e-14
Gsum2 0 sum br2 0 1.88684291279
Ebrsrc3 brsrc3 0 ndelay 0 1
Rbr3 brsrc3 br3 1000
Cbr3 br3 0 4.00293740717e-13
Gsum3 0 sum br3 0 -0.184577287499
Ebrsrc4 brsrc4 0 ndelay 0 1
Rbr4 brsrc4 br4 1000
Cbr4 br4 0 1.93189443751e-11
Gsum4 0 sum br4 0 0.0486086202912
Etailfsrc1 tailfsrc1 0 ndelay 0 1
Rtailf1 tailfsrc1 tailf1 1000
Ctailf1 tailf1 0 2.08726256114e-13
Gtailf1 0 sum tailf1 0 -1.1787450507
Etailssrc1 tailssrc1 0 ndelay 0 1
Rtails1 tailssrc1 tails1 1000
Ctails1 tails1 0 2.19400674439e-13
Gtails1 0 sum tails1 0 1.1787450507
Eringbase1 ringbase1 0 pin 0 1
Eringfsrc1 ringfsrc1 0 ringbase1 0 1
Rringf1 ringfsrc1 ringf1 1000
Cringf1 ringf1 0 3e-15
Gringf1 0 sum ringf1 0 -0.487495782364
Eringssrc1 ringssrc1 0 ringbase1 0 1
Rrings1 ringssrc1 rings1 1000
Crings1 rings1 0 2e-14
Grings1 0 sum rings1 0 0.487495782364
Eringbase2 ringbase2 0 pin 0 1
Eringfsrc2 ringfsrc2 0 ringbase2 0 1
Rringf2 ringfsrc2 ringf2 1000
Cringf2 ringf2 0 8e-15
Gringf2 0 sum ringf2 0 -3.93649258537
Eringssrc2 ringssrc2 0 ringbase2 0 1
Rrings2 ringssrc2 rings2 1000
Crings2 rings2 0 4e-14
Grings2 0 sum rings2 0 3.93649258537
Eringbase3 ringbase3 0 pin 0 1
Eringfsrc3 ringfsrc3 0 ringbase3 0 1
Rringf3 ringfsrc3 ringf3 1000
Cringf3 ringf3 0 2e-14
Gringf3 0 sum ringf3 0 9.99999947518
Eringssrc3 ringssrc3 0 ringbase3 0 1
Rrings3 ringssrc3 rings3 1000
Crings3 rings3 0 1.2e-13
Grings3 0 sum rings3 0 -9.99999947518
Eringbase4 ringbase4 0 pin 0 1
Eringfsrc4 ringfsrc4 0 ringbase4 0 1
Rringf4 ringfsrc4 ringf4 1000
Cringf4 ringf4 0 5e-14
Gringf4 0 sum ringf4 0 -9.99999999749
Eringssrc4 ringssrc4 0 ringbase4 0 1
Rrings4 ringssrc4 rings4 1000
Crings4 rings4 0 4e-13
Grings4 0 sum rings4 0 9.99999999749
Tringdelay5 pin 0 ringbase5 0 Z0=1e12 TD=0.02n
Rringdelay_term5 ringbase5 0 1e12
Eringfsrc5 ringfsrc5 0 ringbase5 0 1
Rringf5 ringfsrc5 ringf5 1000
Cringf5 ringf5 0 3e-15
Gringf5 0 sum ringf5 0 0.0313686644903
Eringssrc5 ringssrc5 0 ringbase5 0 1
Rrings5 ringssrc5 rings5 1000
Crings5 rings5 0 2e-14
Grings5 0 sum rings5 0 -0.0313686644903
Tringdelay6 pin 0 ringbase6 0 Z0=1e12 TD=0.02n
Rringdelay_term6 ringbase6 0 1e12
Eringfsrc6 ringfsrc6 0 ringbase6 0 1
Rringf6 ringfsrc6 ringf6 1000
Cringf6 ringf6 0 8e-15
Gringf6 0 sum ringf6 0 -2.99773742081
Eringssrc6 ringssrc6 0 ringbase6 0 1
Rrings6 ringssrc6 rings6 1000
Crings6 rings6 0 4e-14
Grings6 0 sum rings6 0 2.99773742081
Tringdelay7 pin 0 ringbase7 0 Z0=1e12 TD=0.02n
Rringdelay_term7 ringbase7 0 1e12
Eringfsrc7 ringfsrc7 0 ringbase7 0 1
Rringf7 ringfsrc7 ringf7 1000
Cringf7 ringf7 0 2e-14
Gringf7 0 sum ringf7 0 9.99915496292
Eringssrc7 ringssrc7 0 ringbase7 0 1
Rrings7 ringssrc7 rings7 1000
Crings7 rings7 0 1.2e-13
Grings7 0 sum rings7 0 -9.99915496292
Tringdelay8 pin 0 ringbase8 0 Z0=1e12 TD=0.02n
Rringdelay_term8 ringbase8 0 1e12
Eringfsrc8 ringfsrc8 0 ringbase8 0 1
Rringf8 ringfsrc8 ringf8 1000
Cringf8 ringf8 0 5e-14
Gringf8 0 sum ringf8 0 -9.99999937098
Eringssrc8 ringssrc8 0 ringbase8 0 1
Rrings8 ringssrc8 rings8 1000
Crings8 rings8 0 4e-13
Grings8 0 sum rings8 0 9.99999937098
Tringdelay9 pin 0 ringbase9 0 Z0=1e12 TD=0.04n
Rringdelay_term9 ringbase9 0 1e12
Eringfsrc9 ringfsrc9 0 ringbase9 0 1
Rringf9 ringfsrc9 ringf9 1000
Cringf9 ringf9 0 3e-15
Gringf9 0 sum ringf9 0 -0.630362643654
Eringssrc9 ringssrc9 0 ringbase9 0 1
Rrings9 ringssrc9 rings9 1000
Crings9 rings9 0 2e-14
Grings9 0 sum rings9 0 0.630362643654
Tringdelay10 pin 0 ringbase10 0 Z0=1e12 TD=0.04n
Rringdelay_term10 ringbase10 0 1e12
Eringfsrc10 ringfsrc10 0 ringbase10 0 1
Rringf10 ringfsrc10 ringf10 1000
Cringf10 ringf10 0 8e-15
Gringf10 0 sum ringf10 0 -2.22282290136
Eringssrc10 ringssrc10 0 ringbase10 0 1
Rrings10 ringssrc10 rings10 1000
Crings10 rings10 0 4e-14
Grings10 0 sum rings10 0 2.22282290136
Tringdelay11 pin 0 ringbase11 0 Z0=1e12 TD=0.04n
Rringdelay_term11 ringbase11 0 1e12
Eringfsrc11 ringfsrc11 0 ringbase11 0 1
Rringf11 ringfsrc11 ringf11 1000
Cringf11 ringf11 0 2e-14
Gringf11 0 sum ringf11 0 9.99999999904
Eringssrc11 ringssrc11 0 ringbase11 0 1
Rrings11 ringssrc11 rings11 1000
Crings11 rings11 0 1.2e-13
Grings11 0 sum rings11 0 -9.99999999904
Tringdelay12 pin 0 ringbase12 0 Z0=1e12 TD=0.04n
Rringdelay_term12 ringbase12 0 1e12
Eringfsrc12 ringfsrc12 0 ringbase12 0 1
Rringf12 ringfsrc12 ringf12 1000
Cringf12 ringf12 0 5e-14
Gringf12 0 sum ringf12 0 -8.19288177128
Eringssrc12 ringssrc12 0 ringbase12 0 1
Rrings12 ringssrc12 rings12 1000
Crings12 rings12 0 4e-13
Grings12 0 sum rings12 0 8.19288177128
Tringdelay13 pin 0 ringbase13 0 Z0=1e12 TD=0.06n
Rringdelay_term13 ringbase13 0 1e12
Eringfsrc13 ringfsrc13 0 ringbase13 0 1
Rringf13 ringfsrc13 ringf13 1000
Cringf13 ringf13 0 3e-15
Gringf13 0 sum ringf13 0 3.42986128225
Eringssrc13 ringssrc13 0 ringbase13 0 1
Rrings13 ringssrc13 rings13 1000
Crings13 rings13 0 2e-14
Grings13 0 sum rings13 0 -3.42986128225
Tringdelay14 pin 0 ringbase14 0 Z0=1e12 TD=0.06n
Rringdelay_term14 ringbase14 0 1e12
Eringfsrc14 ringfsrc14 0 ringbase14 0 1
Rringf14 ringfsrc14 ringf14 1000
Cringf14 ringf14 0 8e-15
Gringf14 0 sum ringf14 0 -9.98386504219
Eringssrc14 ringssrc14 0 ringbase14 0 1
Rrings14 ringssrc14 rings14 1000
Crings14 rings14 0 4e-14
Grings14 0 sum rings14 0 9.98386504219
Tringdelay15 pin 0 ringbase15 0 Z0=1e12 TD=0.06n
Rringdelay_term15 ringbase15 0 1e12
Eringfsrc15 ringfsrc15 0 ringbase15 0 1
Rringf15 ringfsrc15 ringf15 1000
Cringf15 ringf15 0 2e-14
Gringf15 0 sum ringf15 0 9.90981495347
Eringssrc15 ringssrc15 0 ringbase15 0 1
Rrings15 ringssrc15 rings15 1000
Crings15 rings15 0 1.2e-13
Grings15 0 sum rings15 0 -9.90981495347
Tringdelay16 pin 0 ringbase16 0 Z0=1e12 TD=0.06n
Rringdelay_term16 ringbase16 0 1e12
Eringfsrc16 ringfsrc16 0 ringbase16 0 1
Rringf16 ringfsrc16 ringf16 1000
Cringf16 ringf16 0 5e-14
Gringf16 0 sum ringf16 0 2.87083867827
Eringssrc16 ringssrc16 0 ringbase16 0 1
Rrings16 ringssrc16 rings16 1000
Crings16 rings16 0 4e-13
Grings16 0 sum rings16 0 -2.87083867827
Tringdelay17 pin 0 ringbase17 0 Z0=1e12 TD=0.08n
Rringdelay_term17 ringbase17 0 1e12
Eringfsrc17 ringfsrc17 0 ringbase17 0 1
Rringf17 ringfsrc17 ringf17 1000
Cringf17 ringf17 0 3e-15
Gringf17 0 sum ringf17 0 0.298826795617
Eringssrc17 ringssrc17 0 ringbase17 0 1
Rrings17 ringssrc17 rings17 1000
Crings17 rings17 0 2e-14
Grings17 0 sum rings17 0 -0.298826795617
Tringdelay18 pin 0 ringbase18 0 Z0=1e12 TD=0.08n
Rringdelay_term18 ringbase18 0 1e12
Eringfsrc18 ringfsrc18 0 ringbase18 0 1
Rringf18 ringfsrc18 ringf18 1000
Cringf18 ringf18 0 8e-15
Gringf18 0 sum ringf18 0 0.378978380433
Eringssrc18 ringssrc18 0 ringbase18 0 1
Rrings18 ringssrc18 rings18 1000
Crings18 rings18 0 4e-14
Grings18 0 sum rings18 0 -0.378978380433
Tringdelay19 pin 0 ringbase19 0 Z0=1e12 TD=0.08n
Rringdelay_term19 ringbase19 0 1e12
Eringfsrc19 ringfsrc19 0 ringbase19 0 1
Rringf19 ringfsrc19 ringf19 1000
Cringf19 ringf19 0 2e-14
Gringf19 0 sum ringf19 0 -6.70464191656
Eringssrc19 ringssrc19 0 ringbase19 0 1
Rrings19 ringssrc19 rings19 1000
Crings19 rings19 0 1.2e-13
Grings19 0 sum rings19 0 6.70464191656
Tringdelay20 pin 0 ringbase20 0 Z0=1e12 TD=0.08n
Rringdelay_term20 ringbase20 0 1e12
Eringfsrc20 ringfsrc20 0 ringbase20 0 1
Rringf20 ringfsrc20 ringf20 1000
Cringf20 ringf20 0 5e-14
Gringf20 0 sum ringf20 0 9.99999930728
Eringssrc20 ringssrc20 0 ringbase20 0 1
Rrings20 ringssrc20 rings20 1000
Crings20 rings20 0 4e-13
Grings20 0 sum rings20 0 -9.99999930728
Tringdelay21 pin 0 ringbase21 0 Z0=1e12 TD=0.12n
Rringdelay_term21 ringbase21 0 1e12
Eringfsrc21 ringfsrc21 0 ringbase21 0 1
Rringf21 ringfsrc21 ringf21 1000
Cringf21 ringf21 0 3e-15
Gringf21 0 sum ringf21 0 -0.308189299216
Eringssrc21 ringssrc21 0 ringbase21 0 1
Rrings21 ringssrc21 rings21 1000
Crings21 rings21 0 2e-14
Grings21 0 sum rings21 0 0.308189299216
Tringdelay22 pin 0 ringbase22 0 Z0=1e12 TD=0.12n
Rringdelay_term22 ringbase22 0 1e12
Eringfsrc22 ringfsrc22 0 ringbase22 0 1
Rringf22 ringfsrc22 ringf22 1000
Cringf22 ringf22 0 8e-15
Gringf22 0 sum ringf22 0 1.23845062064
Eringssrc22 ringssrc22 0 ringbase22 0 1
Rrings22 ringssrc22 rings22 1000
Crings22 rings22 0 4e-14
Grings22 0 sum rings22 0 -1.23845062064
Tringdelay23 pin 0 ringbase23 0 Z0=1e12 TD=0.12n
Rringdelay_term23 ringbase23 0 1e12
Eringfsrc23 ringfsrc23 0 ringbase23 0 1
Rringf23 ringfsrc23 ringf23 1000
Cringf23 ringf23 0 2e-14
Gringf23 0 sum ringf23 0 -3.67113306752
Eringssrc23 ringssrc23 0 ringbase23 0 1
Rrings23 ringssrc23 rings23 1000
Crings23 rings23 0 1.2e-13
Grings23 0 sum rings23 0 3.67113306752
Tringdelay24 pin 0 ringbase24 0 Z0=1e12 TD=0.12n
Rringdelay_term24 ringbase24 0 1e12
Eringfsrc24 ringfsrc24 0 ringbase24 0 1
Rringf24 ringfsrc24 ringf24 1000
Cringf24 ringf24 0 5e-14
Gringf24 0 sum ringf24 0 5.06704617118
Eringssrc24 ringssrc24 0 ringbase24 0 1
Rrings24 ringssrc24 rings24 1000
Crings24 rings24 0 4e-13
Grings24 0 sum rings24 0 -5.06704617118
Tringdelay25 pin 0 ringbase25 0 Z0=1e12 TD=0.18n
Rringdelay_term25 ringbase25 0 1e12
Eringfsrc25 ringfsrc25 0 ringbase25 0 1
Rringf25 ringfsrc25 ringf25 1000
Cringf25 ringf25 0 3e-15
Gringf25 0 sum ringf25 0 -0.328112840249
Eringssrc25 ringssrc25 0 ringbase25 0 1
Rrings25 ringssrc25 rings25 1000
Crings25 rings25 0 2e-14
Grings25 0 sum rings25 0 0.328112840249
Tringdelay26 pin 0 ringbase26 0 Z0=1e12 TD=0.18n
Rringdelay_term26 ringbase26 0 1e12
Eringfsrc26 ringfsrc26 0 ringbase26 0 1
Rringf26 ringfsrc26 ringf26 1000
Cringf26 ringf26 0 8e-15
Gringf26 0 sum ringf26 0 1.061077163
Eringssrc26 ringssrc26 0 ringbase26 0 1
Rrings26 ringssrc26 rings26 1000
Crings26 rings26 0 4e-14
Grings26 0 sum rings26 0 -1.061077163
Tringdelay27 pin 0 ringbase27 0 Z0=1e12 TD=0.18n
Rringdelay_term27 ringbase27 0 1e12
Eringfsrc27 ringfsrc27 0 ringbase27 0 1
Rringf27 ringfsrc27 ringf27 1000
Cringf27 ringf27 0 2e-14
Gringf27 0 sum ringf27 0 -2.48866719964
Eringssrc27 ringssrc27 0 ringbase27 0 1
Rrings27 ringssrc27 rings27 1000
Crings27 rings27 0 1.2e-13
Grings27 0 sum rings27 0 2.48866719964
Tringdelay28 pin 0 ringbase28 0 Z0=1e12 TD=0.18n
Rringdelay_term28 ringbase28 0 1e12
Eringfsrc28 ringfsrc28 0 ringbase28 0 1
Rringf28 ringfsrc28 ringf28 1000
Cringf28 ringf28 0 5e-14
Gringf28 0 sum ringf28 0 3.06881247033
Eringssrc28 ringssrc28 0 ringbase28 0 1
Rrings28 ringssrc28 rings28 1000
Crings28 rings28 0 4e-13
Grings28 0 sum rings28 0 -3.06881247033
Tringdelay29 pin 0 ringbase29 0 Z0=1e12 TD=0.25n
Rringdelay_term29 ringbase29 0 1e12
Eringfsrc29 ringfsrc29 0 ringbase29 0 1
Rringf29 ringfsrc29 ringf29 1000
Cringf29 ringf29 0 3e-15
Gringf29 0 sum ringf29 0 -1.08350795446
Eringssrc29 ringssrc29 0 ringbase29 0 1
Rrings29 ringssrc29 rings29 1000
Crings29 rings29 0 2e-14
Grings29 0 sum rings29 0 1.08350795446
Tringdelay30 pin 0 ringbase30 0 Z0=1e12 TD=0.25n
Rringdelay_term30 ringbase30 0 1e12
Eringfsrc30 ringfsrc30 0 ringbase30 0 1
Rringf30 ringfsrc30 ringf30 1000
Cringf30 ringf30 0 8e-15
Gringf30 0 sum ringf30 0 2.01830210536
Eringssrc30 ringssrc30 0 ringbase30 0 1
Rrings30 ringssrc30 rings30 1000
Crings30 rings30 0 4e-14
Grings30 0 sum rings30 0 -2.01830210536
Tringdelay31 pin 0 ringbase31 0 Z0=1e12 TD=0.25n
Rringdelay_term31 ringbase31 0 1e12
Eringfsrc31 ringfsrc31 0 ringbase31 0 1
Rringf31 ringfsrc31 ringf31 1000
Cringf31 ringf31 0 2e-14
Gringf31 0 sum ringf31 0 -1.780722755
Eringssrc31 ringssrc31 0 ringbase31 0 1
Rrings31 ringssrc31 rings31 1000
Crings31 rings31 0 1.2e-13
Grings31 0 sum rings31 0 1.780722755
Tringdelay32 pin 0 ringbase32 0 Z0=1e12 TD=0.25n
Rringdelay_term32 ringbase32 0 1e12
Eringfsrc32 ringfsrc32 0 ringbase32 0 1
Rringf32 ringfsrc32 ringf32 1000
Cringf32 ringf32 0 5e-14
Gringf32 0 sum ringf32 0 1.23584294008
Eringssrc32 ringssrc32 0 ringbase32 0 1
Rrings32 ringssrc32 rings32 1000
Crings32 rings32 0 4e-13
Grings32 0 sum rings32 0 -1.23584294008
Eout outdrv 0 sum 0 2
Rout outdrv p2 50
.ends s_equivalent
