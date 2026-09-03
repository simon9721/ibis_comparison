.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12
Vin in_src 0 PULSE(0 3.3 50.0n 5p 5p 650.0n 2600.0n)
Rin in_src in_dig 1
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3
.include 'C:/Users/simom/Desktop/IBIS_Comparison/PIC18F1xQ20_LV_IBIS_Models/ccomp_zero_experiment_vqfn20/models/ptc_i3c_std-Output-Typical.sub'
.include 'C:/Users/simom/Desktop/IBIS_Comparison/PIC18F1xQ20_LV_IBIS_Models/ccomp_zero_experiment_vqfn20/models/ptc_i3c_std-Output-Typical-CComp0.sub'
XBASE pad_base in_dig en_sig vdd 0 ptc_i3c_std_OutputInput_Typical
XZERO pad_zero in_dig en_sig vdd 0 ptc_i3c_std_OutputInput_Typical_CComp0
Rload_base pad_base 0 50.0
Rload_zero pad_zero 0 50.0
.save V(in_dig) V(pad_base) V(pad_zero)
.tran 100p 1300.0n
.end
