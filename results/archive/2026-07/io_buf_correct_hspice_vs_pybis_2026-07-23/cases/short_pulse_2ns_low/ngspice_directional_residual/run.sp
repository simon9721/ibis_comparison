* Corrected-reference pybis comparison
* Model generated from regenerated 5 ps io_buf.ibs
* Variant: InputDrivenTwoStateGateDirectionalResidualFull
.title corrected HSPICE versus pybis short_pulse_2ns_low directional_residual
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+ 0.000000n 0.000000
+ 5.000000n 0.000000
+ 5.001000n 3.300000
+ 10.000000n 3.300000
+ 10.001000n 0.000000
+ 12.000000n 0.000000
+ 12.001000n 3.300000
+ 18.000000n 3.300000 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.gup) V(xdrv.gdn) V(xdrv.guptarget) V(xdrv.gdntarget) V(xdrv.kugate) V(xdrv.kdgate) V(xdrv.kdres) V(xdrv.gdnrate)
.tran 0.001n 18.000000n
.end
