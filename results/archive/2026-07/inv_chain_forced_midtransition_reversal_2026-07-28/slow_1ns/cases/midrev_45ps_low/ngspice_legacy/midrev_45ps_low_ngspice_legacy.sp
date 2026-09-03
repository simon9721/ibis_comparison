* inv_chain ngspice legacy
* case: midrev_45ps_low
.title inv_chain ngspice legacy midrev_45ps_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 1.8
+ 10n 1.8
+ 10.001n 0
+ 10.045n 0
+ 10.046n 1.8
+ 14n 1.8 )

Ven en_sig 0 DC 1.8
Vdd vdd 0 DC 1.8
.include 'driver2_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver2_OutputInput_Typical

Rload pad 0 50.0
Cload pad 0 2.0p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 0.001n 14n
.end
