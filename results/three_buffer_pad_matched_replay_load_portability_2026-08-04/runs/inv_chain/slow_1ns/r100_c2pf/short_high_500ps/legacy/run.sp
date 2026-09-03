* Three-buffer pad-match replay study
.title inv_chain legacy short_high_500ps
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12
Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.05n 1.8
+ 5.5n 1.8
+ 5.55n 0
+ 22n 0 )
Ven en_sig 0 DC 1.8
Vdd vdd 0 DC 1.8
.include 'driver2_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver2_OutputInput_Typical
Rload pad 0 100
Cload pad 0 2p
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 2p 22n
.end
