* stage4 transistor reference
.title stage4 transistor
.OPTIONS LIST NODE POST
.OPTIONS METHOD=GEAR
.OPTIONS GSHUNT=1E-12
.option post=2 probe accurate ingold=2
.temp 27

.PARAM  vccr_typ  = 1.300V
.PARAM  vccr_min  = 1.250V
.PARAM  vccr_max  = 1.350V
.PARAM  vccq_typ  = 1.800V
.PARAM  vccq_min  = 1.700V
.PARAM  vccq_max  = 1.900V
.PARAM  gnd       = 0.000V
.PARAM  vssq      = 0.000V
.PARAM  vss       = 0.000V

.include 'invchain_stage4_subckt_typ.sp'

Vdd vccq 0 DC 1.8
Vin in_dig 0 PWL(0n 0  5.0n 0  5.001n 1.8  15.0n 1.8  15.001n 0  22.0n 0)
XDUT in_dig pad_sp vccq 0 invchain
Rload pad_sp 0 50.0
Cload pad_sp 0 2.0p

.probe tran V(in_dig) V(pad_sp)
.tran 0.001n 22.0n
.end
