.lib 'HL18G-S3.7S.lib' tt_tn
.param Wn=1E-06
.param Wp=2E-06
.param Ln=1.8E-07
.param Lp=1.8E-07

.PARAM  vccq      = vccq_typ
.PARAM  vccr      = vccr_typ

.subckt invchain VIN VOUT8 vccq vssq

MPM_inv1 VOUT1 VIN vccq vccq pch_tn W=Wp L=Lp m=16
MNM_inv1 VOUT1 VIN vssq vssq nch_tn W=Wn L=Ln m=16

MPM_inv2 VOUT2 VOUT1 vccq vccq pch_tn W=Wp L=Lp m=32
MNM_inv2 VOUT2 VOUT1 vssq vssq nch_tn W=Wn L=Ln m=32

MPM_inv3 VOUT3 VOUT2 vccq vccq pch_tn W=Wp L=Lp m=64
MNM_inv3 VOUT3 VOUT2 vssq vssq nch_tn W=Wn L=Ln m=64

MPM_inv4 VOUT8 VOUT3 vccq vccq pch_tn W=Wp L=Lp m=128
MNM_inv4 VOUT8 VOUT3 vssq vssq nch_tn W=Wn L=Ln m=128

.ends
