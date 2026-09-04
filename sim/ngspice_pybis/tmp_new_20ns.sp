* PRBS7 context38 transient, new_20ns
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7
Vstim  in_dig  0  PWL(0.000000000e+00 0.0000
+ 2.000000000e-09  0.0000
+ 4.000000000e-09  0.0000
+ 6.000000000e-09  0.0000
+ 8.000000000e-09  0.0000
+ 8.200000000e-09  3.3000
+ 1.000000000e-08  3.3000
+ 1.020000000e-08  0.0000
+ 1.200000000e-08  0.0000
+ 1.400000000e-08  0.0000
+ 1.420000000e-08  3.3000
+ 1.600000000e-08  3.3000
+ 1.800000000e-08  3.3000
+ 1.820000000e-08  0.0000
+ 2.000000000e-08  0.0000)
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3
.include 'C:\Users\simom\Desktop\IBIS_Comparison\ngspice_pybis\driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
RCH_TX  pad tx_out 1u
* Simple 50-ohm load (no channel, for clearest comparison)
RTERM   tx_out 0 50
.save V(in_dig) V(pad) V(tx_out)
.tran 5e-12 2e-8
.end
