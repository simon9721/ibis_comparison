* HSPICE native S-parameter audit: audit_amp1p5_edge500_r50
.option post=2 probe accurate
.temp 27
Vin   src  0  PWL(0 0 1n 0 1.5e-09 1.5 9n 1.5 9.5e-09 0)
Rsrc  src  p1  50
Schannel  p1  p2  p3  p4  0  MNAME=ch_model
Rnear_neg  p2  0  50
Rterm_pos  p3  0  50
Rterm_neg  p4  0  50
.MODEL ch_model S
+ TSTONEFILE='../../../../hspice/sparam/Cisco_Backplane_channel_data/8F/Ch7_28_8F_t.s4p'
+ Z0=50
+ RATIONAL_FUNC=1
+ INTERPOLATION=HYBRID
+ LOWPASS=1
+ HIGHPASS=3
+ PASSIVE=1
.probe tran V(p1) V(p2) V(p3) V(p4) V(src)
.tran 10p 3.5e-08
.end
