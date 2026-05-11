# Accepted PRBS/RLGC Regression Summary

Status: PASS

## Simulator Commands

- ngspice_refspice: rc=0, timeout=False, wall_s=4.30
- xyce_refspice: rc=0, timeout=False, wall_s=2.58
- clean_pybis_pair: rc=0, timeout=False, wall_s=12.98
- build_final_comparison: rc=0, timeout=False, wall_s=7.83

## Pairwise Error

- Xyce + io_buf.sp minus ngspice + io_buf.sp: RMSE=3.142 mV, max=23.970 mV
- Xyce + pybis edge15_flat4p2 minus ngspice + pybis: RMSE=26.643 mV, max=50.376 mV

## Completion

- ngspice + io_buf.sp: complete=True, t_end=1000.000 ns
- Xyce + io_buf.sp: complete=True, t_end=1000.000 ns
- ngspice + pybis: complete=True, t_end=1000.000 ns
- Xyce + pybis edge15_flat4p2: complete=True, t_end=1000.000 ns
