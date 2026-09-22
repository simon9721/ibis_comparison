* base8 transistor
.title base8 transistor
.OPTIONS METHOD=GEAR GSHUNT=1E-12
.option post=2 probe accurate ingold=2
.temp 27
.PARAM  vccr_typ  = 1.300V
.PARAM  vccq_typ  = 1.800V
.PARAM  vssq      = 0.000V
.PARAM  vss       = 0.000V
.include 'invchain_base8_subckt_typ.sp'
Vdd vccq 0 DC 1.8
Vin in_dig 0 PWL(0n 0  5n 0  5.001n 1.8  15n 1.8  15.001n 0  22n 0)
XDUT in_dig pad vccq 0 invchain
Rload pad 0 50.0
Cload pad 0 2.0p
.probe tran V(pad)
.tran 0.0005n 22.0n
.end
