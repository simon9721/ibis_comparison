* io_buf coefficient-state pybis/ngspice switching coefficient extraction
* Sweep case: edge_2ns_50r_2pf
* 2 ns rise/fall, 50 ohm + 2 pF
.title io_buf ngspice coefficient-state pybis Ku/Kd extraction edge_2ns_50r_2pf
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+         0n        0
+         5n        0
+         7n      3.3
+        15n      3.3
+        17n        0
+        30n        0 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd) V(xdrv.kutarget) V(xdrv.kdtarget)
.tran 0.001n 30n
.end
