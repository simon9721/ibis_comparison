.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12
Vin in_src 0 PULSE(0 3.3 50.0n 5p 5p 650.0n 2600.0n)
Rin in_src in_dig 1
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3
.include 'C:/Users/simom/Desktop/IBIS_Comparison/PIC18F1xQ20_LV_IBIS_Models/ccomp_fullzero_experiment_vqfn20/models/ptc_i3c_std-orig.sub'
.include 'C:/Users/simom/Desktop/IBIS_Comparison/PIC18F1xQ20_LV_IBIS_Models/ccomp_fullzero_experiment_vqfn20/models/ptc_i3c_std-runtime-zero.sub'
.include 'C:/Users/simom/Desktop/IBIS_Comparison/PIC18F1xQ20_LV_IBIS_Models/ccomp_fullzero_experiment_vqfn20/models/ptc_i3c_std-full-zero.sub'
XORIG pad_orig in_dig en_sig vdd 0 ptc_i3c_std_Orig
XRZERO pad_rzero in_dig en_sig vdd 0 ptc_i3c_std_RuntimeZero
XFZERO pad_fzero in_dig en_sig vdd 0 ptc_i3c_std_FullZero
Rload_orig pad_orig 0 50.0
Rload_rzero pad_rzero 0 50.0
Rload_fzero pad_fzero 0 50.0
.save V(in_dig) V(pad_orig) V(pad_rzero) V(pad_fzero)
.tran 100p 1300.0n
.end
