* variant stressed transistor
.title stressed transistor
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5n 0  5.001n 1.8  5.19n 1.8  5.191n 0  22n 0)
.OPTIONS METHOD=GEAR GSHUNT=1E-12
.PARAM vccr_typ=1.300V
.PARAM vccq_typ=1.800V
.PARAM vssq=0.000V
.PARAM vss=0.000V
.include 'invchain_skewp_subckt_typ.sp'
Vdd vccq 0 DC 1.8
XDUT in_dig pad vccq 0 invchain
Rload pad 0 50.0
Cload pad 0 2.0p
.probe tran V(pad)
.tran 0.002n 22.0n
.end
