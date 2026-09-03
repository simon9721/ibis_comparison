* ex2 ngspice legacy
.title ex2 ngspice legacy short_pulse_2ns_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 3.3
+ 10n 3.3
+ 10.001n 0
+ 12n 0
+ 12.001n 3.3
+ 19n 3.3 )

* The generated Output model inherits active-low enable; tie it active.
Ven en_sig 0 DC 0
Vdd vdd 0 DC 3.3
.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical
Rload pad 0 50.0
Cload pad 0 2.0p
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 0.002n 19n
.end
