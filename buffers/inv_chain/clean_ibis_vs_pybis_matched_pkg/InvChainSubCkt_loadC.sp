*** Inverter Chain***

.lib 'HL18G-S3.7S.lib' tt_tn
.param Wn=1u
.param Wp=2u
.param Ln=180n
.param Lp=180n

.TEMP 27
.PARAM SPIVCCX = 1.70000

.subckt invchain VIN VOUT8 vdd vss

MPM_inv1 VOUT1 VIN vdd vdd pch_tn W=Wp L=Lp m=1
MNM_inv1 VOUT1 VIN vss vss nch_tn W=Wn L=Ln m=1

MPM_inv2 VOUT2 VOUT1 vdd vdd pch_tn W=Wp L=Lp m=2
MNM_inv2 VOUT2 VOUT1 vss vss nch_tn W=Wn L=Ln m=2

MPM_inv3 VOUT3 VOUT2 vdd vdd pch_tn W=Wp L=Lp m=4
MNM_inv3 VOUT3 VOUT2 vss vss nch_tn W=Wn L=Ln m=4

MPM_inv4 VOUT4 VOUT3 vdd vdd pch_tn W=Wp L=Lp m=8
MNM_inv4 VOUT4 VOUT3 vss vss nch_tn W=Wn L=Ln m=8

MPM_inv5 VOUT5 VOUT4 vdd vdd pch_tn W=Wp L=Lp m=16
MNM_inv5 VOUT5 VOUT4 vss vss nch_tn W=Wn L=Ln m=16

MPM_inv6 VOUT6 VOUT5 vdd vdd pch_tn W=Wp L=Lp m=32
MNM_inv6 VOUT6 VOUT5 vss vss nch_tn W=Wn L=Ln m=32

MPM_inv7 VOUT7 VOUT6 vdd vdd pch_tn W=Wp L=Lp m=64
MNM_inv7 VOUT7 VOUT6 vss vss nch_tn W=Wn L=Ln m=64

MPM_inv8 VOUT8 VOUT7 vdd vdd pch_tn W=Wp L=Lp m=128
MNM_inv8 VOUT8 VOUT7 vss vss nch_tn W=Wn L=Ln m=128

.ends

.OPTIONS LIST NODE POST
.PROBE V(VOUT8) I(VSPI_VCC)
.TRAN 2.0E-12 4E-09 Sweep SPIVCCX POI 3 1.7 1.8 1.9
.PRINT TRAN V(VOUT8)  I(VOUT8) I(VSPI_VCC)
CPSI_DIE VOUT8 NSPI_DIEX 2p

* BUFFER CONTROL SOURCES
VSPI_VCC vdd 0 'SPIVCCX'
VSPI_VSS vss 0 0.0V
VSPI_DIE NSPI_DIEX 0 0.0
VSPI_INP VIN 0 PULSE(0 1.8 0n 5p 5p 1.5n 3n)


* TOP-LEVEL BUFFER INSTANCE
XSPI_BUFFER VIN VOUT8 vdd vss invchain

.END