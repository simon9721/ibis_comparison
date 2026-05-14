* Short 10101 pybis internal-state probe.
* Purpose: inspect edge detector vs elapsed-time/table state around the
* fast rise/fall/rise/fall pattern that produces the stressed-case spike.
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

* Shifted copy of the local stressed pattern around 48-58 ns:
* high, fall, low, rise, high, fall, low, rise.
* UI=2 ns, input transition time=200 ps, threshold crossing at +100 ps.
Vstim  in_dig  0  PWL(
+ 0.000000000e+00  3.3000
+ 2.000000000e-09  3.3000
+ 2.200000000e-09  0.0000
+ 4.000000000e-09  0.0000
+ 4.200000000e-09  3.3000
+ 6.000000000e-09  3.3000
+ 6.200000000e-09  0.0000
+ 8.000000000e-09  0.0000
+ 8.200000000e-09  3.3000
+ 1.200000000e-08  3.3000)

Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include 'C:/Users/simom/Desktop/IBIS_Comparison/results/stressed_edge50_corrected_crossflow_2026-05-12_clean/models/driver_OutputInput_Typical_relaxed92_edge50_tailflat4p2_ngspice_syntax.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

RLOAD pad 0 50

.save V(in_dig) V(pad)
.save V(xdrv.ni) V(xdrv.n2) V(xdrv.n3) V(xdrv.n4) V(xdrv.n6) V(xdrv.n8) V(xdrv.nx)
.save V(xdrv.kur0) V(xdrv.kdr0) V(xdrv.kuf0) V(xdrv.kdf0)
.save V(xdrv.nkur) V(xdrv.nkdr) V(xdrv.nkuf) V(xdrv.nkdf)
.save V(xdrv.ku) V(xdrv.kd)
.tran 1p 12n
.end
