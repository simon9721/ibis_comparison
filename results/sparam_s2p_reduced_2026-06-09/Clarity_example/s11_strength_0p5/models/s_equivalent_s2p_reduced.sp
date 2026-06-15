* 2-port delay-aware reduced S-parameter macromodel
* Fitted for the 50 ohm HSPICE audit bench.
.subckt s_equivalent p1 p2
* S11-like 50 ohm bench input correction.
Rtxsum txsum 0 1
Etxsrc1 txsrc1 0 pin 0 1
Rtx1 txsrc1 tx1 1000
Ctx1 tx1 0 2e-14
Gtx1 0 txsum tx1 0 0.0712328259511
Etxsrc2 txsrc2 0 pin 0 1
Rtx2 txsrc2 tx2 1000
Ctx2 tx2 0 8.94427191e-14
Gtx2 0 txsum tx2 0 0.0522096557951
Etxsrc3 txsrc3 0 pin 0 1
Rtx3 txsrc3 tx3 1000
Ctx3 tx3 0 4e-13
Gtx3 0 txsum tx3 0 -0.087975394295
Etxsrc4 txsrc4 0 pin 0 1
Rtx4 txsrc4 tx4 1000
Ctx4 tx4 0 1.788854382e-12
Gtx4 0 txsum tx4 0 -0.085492788341
Etxsrc5 txsrc5 0 pin 0 1
Rtx5 txsrc5 tx5 1000
Ctx5 tx5 0 8e-12
Gtx5 0 txsum tx5 0 0.0509668876343
Etxtailfsrc1 txtailfsrc1 0 pin 0 1
Rtxtailf1 txtailfsrc1 txtailf1 1000
Ctx_tailf1 txtailf1 0 5e-14
Gtxtailf1 0 txsum txtailf1 0 -0.157419356456
Etxtailssrc1 txtailssrc1 0 pin 0 1
Rtxtails1 txtailssrc1 txtails1 1000
Ctx_tails1 txtails1 0 2e-12
Gtxtails1 0 txsum txtails1 0 0.157419356456
Etxtailfsrc2 txtailfsrc2 0 pin 0 1
Rtxtailf2 txtailfsrc2 txtailf2 1000
Ctx_tailf2 txtailf2 0 1e-13
Gtxtailf2 0 txsum txtailf2 0 0.108496034247
Etxtailssrc2 txtailssrc2 0 pin 0 1
Rtxtails2 txtailssrc2 txtails2 1000
Ctx_tails2 txtails2 0 4e-12
Gtxtails2 0 txsum txtails2 0 -0.108496034247
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
Cringf1 ringf1 0 5e-15
Gringf1 0 sum ringf1 0 -1.92455870841
Eringssrc1 ringssrc1 0 ringbase1 0 1
Rrings1 ringssrc1 rings1 1000
Crings1 rings1 0 3e-14
Grings1 0 sum rings1 0 1.92455870841
Eringbase2 ringbase2 0 pin 0 1
Eringfsrc2 ringfsrc2 0 ringbase2 0 1
Rringf2 ringfsrc2 ringf2 1000
Cringf2 ringf2 0 1.5e-14
Gringf2 0 sum ringf2 0 1.31447238341
Eringssrc2 ringssrc2 0 ringbase2 0 1
Rrings2 ringssrc2 rings2 1000
Crings2 rings2 0 1e-13
Grings2 0 sum rings2 0 -1.31447238341
Eringbase3 ringbase3 0 pin 0 1
Eringfsrc3 ringfsrc3 0 ringbase3 0 1
Rringf3 ringfsrc3 ringf3 1000
Cringf3 ringf3 0 5e-14
Gringf3 0 sum ringf3 0 -0.220775065798
Eringssrc3 ringssrc3 0 ringbase3 0 1
Rrings3 ringssrc3 rings3 1000
Crings3 rings3 0 3.5e-13
Grings3 0 sum rings3 0 0.220775065798
Tringdelay4 pin 0 ringbase4 0 Z0=1e12 TD=0.04n
Rringdelay_term4 ringbase4 0 1e12
Eringfsrc4 ringfsrc4 0 ringbase4 0 1
Rringf4 ringfsrc4 ringf4 1000
Cringf4 ringf4 0 5e-15
Gringf4 0 sum ringf4 0 0.0325620118124
Eringssrc4 ringssrc4 0 ringbase4 0 1
Rrings4 ringssrc4 rings4 1000
Crings4 rings4 0 3e-14
Grings4 0 sum rings4 0 -0.0325620118124
Tringdelay5 pin 0 ringbase5 0 Z0=1e12 TD=0.04n
Rringdelay_term5 ringbase5 0 1e12
Eringfsrc5 ringfsrc5 0 ringbase5 0 1
Rringf5 ringfsrc5 ringf5 1000
Cringf5 ringf5 0 1.5e-14
Gringf5 0 sum ringf5 0 0.0283657434606
Eringssrc5 ringssrc5 0 ringbase5 0 1
Rrings5 ringssrc5 rings5 1000
Crings5 rings5 0 1e-13
Grings5 0 sum rings5 0 -0.0283657434606
Tringdelay6 pin 0 ringbase6 0 Z0=1e12 TD=0.04n
Rringdelay_term6 ringbase6 0 1e12
Eringfsrc6 ringfsrc6 0 ringbase6 0 1
Rringf6 ringfsrc6 ringf6 1000
Cringf6 ringf6 0 5e-14
Gringf6 0 sum ringf6 0 -0.0643969714579
Eringssrc6 ringssrc6 0 ringbase6 0 1
Rrings6 ringssrc6 rings6 1000
Crings6 rings6 0 3.5e-13
Grings6 0 sum rings6 0 0.0643969714579
Tringdelay7 pin 0 ringbase7 0 Z0=1e12 TD=0.08n
Rringdelay_term7 ringbase7 0 1e12
Eringfsrc7 ringfsrc7 0 ringbase7 0 1
Rringf7 ringfsrc7 ringf7 1000
Cringf7 ringf7 0 5e-15
Gringf7 0 sum ringf7 0 0.0051851599404
Eringssrc7 ringssrc7 0 ringbase7 0 1
Rrings7 ringssrc7 rings7 1000
Crings7 rings7 0 3e-14
Grings7 0 sum rings7 0 -0.0051851599404
Tringdelay8 pin 0 ringbase8 0 Z0=1e12 TD=0.08n
Rringdelay_term8 ringbase8 0 1e12
Eringfsrc8 ringfsrc8 0 ringbase8 0 1
Rringf8 ringfsrc8 ringf8 1000
Cringf8 ringf8 0 1.5e-14
Gringf8 0 sum ringf8 0 0.127894423125
Eringssrc8 ringssrc8 0 ringbase8 0 1
Rrings8 ringssrc8 rings8 1000
Crings8 rings8 0 1e-13
Grings8 0 sum rings8 0 -0.127894423125
Tringdelay9 pin 0 ringbase9 0 Z0=1e12 TD=0.08n
Rringdelay_term9 ringbase9 0 1e12
Eringfsrc9 ringfsrc9 0 ringbase9 0 1
Rringf9 ringfsrc9 ringf9 1000
Cringf9 ringf9 0 5e-14
Gringf9 0 sum ringf9 0 -0.522205814446
Eringssrc9 ringssrc9 0 ringbase9 0 1
Rrings9 ringssrc9 rings9 1000
Crings9 rings9 0 3.5e-13
Grings9 0 sum rings9 0 0.522205814446
Tringdelay10 pin 0 ringbase10 0 Z0=1e12 TD=0.14n
Rringdelay_term10 ringbase10 0 1e12
Eringfsrc10 ringfsrc10 0 ringbase10 0 1
Rringf10 ringfsrc10 ringf10 1000
Cringf10 ringf10 0 5e-15
Gringf10 0 sum ringf10 0 0.153725096499
Eringssrc10 ringssrc10 0 ringbase10 0 1
Rrings10 ringssrc10 rings10 1000
Crings10 rings10 0 3e-14
Grings10 0 sum rings10 0 -0.153725096499
Tringdelay11 pin 0 ringbase11 0 Z0=1e12 TD=0.14n
Rringdelay_term11 ringbase11 0 1e12
Eringfsrc11 ringfsrc11 0 ringbase11 0 1
Rringf11 ringfsrc11 ringf11 1000
Cringf11 ringf11 0 1.5e-14
Gringf11 0 sum ringf11 0 -0.384037695444
Eringssrc11 ringssrc11 0 ringbase11 0 1
Rrings11 ringssrc11 rings11 1000
Crings11 rings11 0 1e-13
Grings11 0 sum rings11 0 0.384037695444
Tringdelay12 pin 0 ringbase12 0 Z0=1e12 TD=0.14n
Rringdelay_term12 ringbase12 0 1e12
Eringfsrc12 ringfsrc12 0 ringbase12 0 1
Rringf12 ringfsrc12 ringf12 1000
Cringf12 ringf12 0 5e-14
Gringf12 0 sum ringf12 0 0.423620256113
Eringssrc12 ringssrc12 0 ringbase12 0 1
Rrings12 ringssrc12 rings12 1000
Crings12 rings12 0 3.5e-13
Grings12 0 sum rings12 0 -0.423620256113
Tringdelay13 pin 0 ringbase13 0 Z0=1e12 TD=0.22n
Rringdelay_term13 ringbase13 0 1e12
Eringfsrc13 ringfsrc13 0 ringbase13 0 1
Rringf13 ringfsrc13 ringf13 1000
Cringf13 ringf13 0 5e-15
Gringf13 0 sum ringf13 0 -0.139902807673
Eringssrc13 ringssrc13 0 ringbase13 0 1
Rrings13 ringssrc13 rings13 1000
Crings13 rings13 0 3e-14
Grings13 0 sum rings13 0 0.139902807673
Tringdelay14 pin 0 ringbase14 0 Z0=1e12 TD=0.22n
Rringdelay_term14 ringbase14 0 1e12
Eringfsrc14 ringfsrc14 0 ringbase14 0 1
Rringf14 ringfsrc14 ringf14 1000
Cringf14 ringf14 0 1.5e-14
Gringf14 0 sum ringf14 0 0.190557793349
Eringssrc14 ringssrc14 0 ringbase14 0 1
Rrings14 ringssrc14 rings14 1000
Crings14 rings14 0 1e-13
Grings14 0 sum rings14 0 -0.190557793349
Tringdelay15 pin 0 ringbase15 0 Z0=1e12 TD=0.22n
Rringdelay_term15 ringbase15 0 1e12
Eringfsrc15 ringfsrc15 0 ringbase15 0 1
Rringf15 ringfsrc15 ringf15 1000
Cringf15 ringf15 0 5e-14
Gringf15 0 sum ringf15 0 0.179205182523
Eringssrc15 ringssrc15 0 ringbase15 0 1
Rrings15 ringssrc15 rings15 1000
Crings15 rings15 0 3.5e-13
Grings15 0 sum rings15 0 -0.179205182523
Eout outdrv 0 sum 0 2
Rout outdrv p2 50
.ends s_equivalent
