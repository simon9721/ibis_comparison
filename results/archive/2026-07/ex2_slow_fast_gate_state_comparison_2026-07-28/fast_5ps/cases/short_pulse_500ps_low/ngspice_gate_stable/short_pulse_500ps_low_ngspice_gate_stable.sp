* ex2 ngspice gate_stable
.title ex2 ngspice gate_stable short_pulse_500ps_low
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+ 0n 0
+ 5n 0
+ 5.001n 3.3
+ 10n 3.3
+ 10.001n 0
+ 10.5n 0
+ 10.501n 3.3
+ 17n 3.3 )

* The generated Output model inherits active-low enable; tie it active.
Ven en_sig 0 DC 0
Vdd vdd 0 DC 3.3
.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical
Rload pad 0 50.0
Cload pad 0 2.0p
.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget) V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kuleg) V(xdrv.kdleg)
.tran 0.002n 17n
.end
