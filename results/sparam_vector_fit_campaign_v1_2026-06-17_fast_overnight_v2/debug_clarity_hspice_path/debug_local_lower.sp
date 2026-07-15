* HSPICE Clarity path debug
.option post=2 probe accurate
.temp 27
Vin src 0 PWL(0 0 1n 0 1.05n 1.5 9n 1.5 9.05n 0)
Rsrc src p1 50
Schannel p1 p2 0 MNAME=ch_model
Rterm p2 0 50
.MODEL ch_model S
+ TSTONEFILE='clarity_example.s2p'
+ Z0=50
+ RATIONAL_FUNC=1
+ INTERPOLATION=HYBRID
+ LOWPASS=1
+ HIGHPASS=3
+ PASSIVE=1
.probe tran V(p1) V(p2) V(src)
.tran 10p 35n
.end
