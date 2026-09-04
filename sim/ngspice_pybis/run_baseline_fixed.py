"""Fix baseline SP include path and run baseline simulation."""
import subprocess
import sys

old_path = r'c:\Users\simom\Desktop\IBIS_Comparison\results\ngspice_kukd_ab_context38_2026-05-11\runs\baseline_pre_kukd\ui2_len30cm_loss5_coarse10_baseline_pre_kukd.sp'
fixed_path = r'c:\Users\simom\Desktop\IBIS_Comparison\results\ngspice_kukd_ab_context38_2026-05-11\runs\baseline_pre_kukd\baseline_fixed_abs.sp'
raw_out = r'c:\Users\simom\Desktop\IBIS_Comparison\results\ngspice_kukd_ab_context38_2026-05-11\runs\baseline_pre_kukd\baseline_fixed_abs.raw'
abs_include = r'C:/Users/simom/Desktop/IBIS_Comparison/results/ngspice_kukd_ab_context38_2026-05-11/driver_OutputInput_Typical_pre_kukd_3e0bf44.sub'

sp = open(old_path, encoding='latin-1').read()
fixed = sp.replace("../../driver_OutputInput_Typical_pre_kukd_3e0bf44.sub", abs_include)
open(fixed_path, 'w', encoding='ascii').write(fixed)
print(f"Fixed SP written to: {fixed_path}")

ngspice = r'C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe'
log_path = r'c:\Users\simom\Desktop\IBIS_Comparison\ngspice_pybis\baseline_run_output.txt'
print(f"Running baseline simulation...")
result = subprocess.run(
    [ngspice, '-b', '-r', raw_out, fixed_path],
    capture_output=True, text=True, timeout=120
)
with open(log_path, 'w', encoding='utf-8') as lf:
    lf.write(f"Return code: {result.returncode}\n")
    lf.write(f"STDOUT:\n{result.stdout}\n")
    lf.write(f"STDERR:\n{result.stderr}\n")
print("Done. Log written to:", log_path)
print("Return code:", result.returncode)
