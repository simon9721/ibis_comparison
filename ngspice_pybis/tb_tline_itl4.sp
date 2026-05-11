* Test B1: PRBS7 + T-line + itl4=200
* Hypothesis: more Newton iterations per step allows the T-line reflection to converge
* Compare stall point against tb_pybis_prbs7_batch.sp (stalls at 210ns with itl4=50)
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=200 itl5=0 trtol=7

.include 'prbs7_vstim.inc'
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

T1  pad  0  ntst  0  Z0=50 Td=30p
R1  ntst 0  50

.save V(in_dig) V(pad) V(ntst)
.tran 10p 1000n
.end
