.temp 27
.options method=gear maxord=2 reltol=1e-3 abstol=1e-9 vntol=1e-6 gmin=1e-12
Vin in_src 0 PULSE(0 3.3 50.0n 5p 5p 650.0n 2600.0n)
Rin in_src in_dig 1
Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3
.include 'C:/Users/simom/Desktop/IBIS_Comparison/PIC18F1xQ20_LV_IBIS_Models/converted_inputdriven_typical/PIC18F1xQ20_pdip20_LV/Output/io_vrefh8_std-Output-Typical.sub'
XDRV pad in_dig en_sig vdd 0 io_vrefh8_std_OutputInput_Typical
Rload pad 0 50.0
.save V(in_dig) V(pad)
.tran 100p 1300.0n
.end
