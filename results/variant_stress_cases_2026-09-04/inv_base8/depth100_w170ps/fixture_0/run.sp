* variant stressed transistor
.title stressed transistor
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5n 0  5.001n 1.8  5.17n 1.8  5.171n 0  22n 0)
.OPTIONS METHOD=GEAR GSHUNT=1E-12
.PARAM vccr_typ=1.300V
.PARAM vccq_typ=1.800V
.PARAM vssq=0.000V
.PARAM vss=0.000V
.include 'invchain_base8_subckt_typ.sp'
Vdd vccq 0 DC 1.8
XDUT in_dig pad vccq 0 invchain
Vfix fix 0 DC 0
Rfix pad fix 50
.probe tran V(pad)
.tran 0.002n 22.0n
.end
