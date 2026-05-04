**********************************************************
* SPIBPro Generated VT VALIDATION for v69adq using HSpice
* V68a.ibs may be download from Micron Technology
**********************************************************

.OPTION PROBE POST
.PROBE V(PAD) I(VCC) I(VSS)
.TRAN 5.0E-12 20e-09

* BUFFER POWER SUPPLY AND LOAD
RSPI_DIE PAD NSPI_DIEX 50
VSPI_DIE NSPI_DIEX 0 0.0
VSPI_ENB ENOUT  0 1.0
VIN NINP 0 PULSE(0 1 1NS 5PS 5PS 1.5nS 3NS )
VCC NVCC 0 1.425
VSS NVSS 0 0
VPU NVCC NVCCX 0
VPD NVSSX NVSS 0

B1IBIS NVCCX NVSSX PAD NINP NVCC NVSS
+ file  = 'v68a.ibs'
+ model = 'DQ_34_1066'
+ buffer=  2
+ typ   =  MIN
+ ramp_rwf = 2
+ ramp_fwf = 2
+ power    = off

.END
