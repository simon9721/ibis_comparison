VALIDATION FOR SPICE3F5 MODEL FROM IBIS MODEL(S) DQ_34_1066
********************************************************************************
*
* MODELING DATE: 20151215113012
* GENERAETD BY BPRO: http://www.spisim.com
*
********************************************************************************

.tran  5P 20N
.probe V(NINP) V(NOUT) V(NTST)
.INCLUDE Ibs2Spc_Ramp.lib

* INPUT
VINP NINP 0  PULSE(0 1 1ns 5ps 5ps 1.5ns 3ns)
VENB NENB 0  DC 1.0
VSS  NVSS 0  DC 0.0
VDD  NVDD 0  DC 1.425

* BUFFER
XIBIS NINP NOUT NVDD NVSS NENB DQ_34_1066_MIN

* TEST LOAD
T1 NOUT 0 NTST 0 Z0=50 Td=30p
R1 NTST 0 50

.END


