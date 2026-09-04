"""
Run old (pre-kukd) and new driver simulations for a short 20ns window,
then plot transient comparison (V(pad), V(tx_out)) old vs new.
"""
import subprocess
import struct
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NGSPICE = r'C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe'
OLD_SUB = r'C:\Users\simom\Desktop\IBIS_Comparison\results\ngspice_kukd_ab_context38_2026-05-11\driver_OutputInput_Typical_pre_kukd_3e0bf44.sub'
NEW_SUB = r'C:\Users\simom\Desktop\IBIS_Comparison\ngspice_pybis\driver_OutputInput_Typical.sub'
OUTDIR  = r'C:\Users\simom\Desktop\IBIS_Comparison\ngspice_pybis'

# PRBS7 context38, first 20ns (10 transitions), from the existing SP files
PRBS_PWL = """+ 2.000000000e-09  0.0000
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
+ 2.000000000e-08  0.0000"""

def make_sp(sub_path, raw_path, t_end='2e-8', label='sim'):
    sp_path = f'{OUTDIR}\\tmp_{label}.sp'
    content = f"""* PRBS7 context38 transient, {label}
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7
Vstim  in_dig  0  PWL(0.000000000e+00 0.0000
{PRBS_PWL})
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3
.include '{sub_path}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
RCH_TX  pad tx_out 1u
* Simple 50-ohm load (no channel, for clearest comparison)
RTERM   tx_out 0 50
.save V(in_dig) V(pad) V(tx_out)
.tran 5e-12 {t_end}
.end
"""
    with open(sp_path, 'w', encoding='ascii') as f:
        f.write(content)
    return sp_path

def run_sim(sp_path, raw_path, timeout=300):
    try:
        r = subprocess.run(
            [NGSPICE, '-b', '-r', raw_path, sp_path],
            capture_output=True, text=True, timeout=timeout
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        return -1, '', f'TIMEOUT after {timeout}s'

def read_raw(raw_path):
    """Read ngspice binary RAW file, return dict of arrays."""
    with open(raw_path, 'rb') as f:
        header = f.read(16384)
    text = header.decode('latin-1', errors='replace')
    nv_m = re.search(r'No\. Variables:\s+(\d+)', text)
    npts_m = re.search(r'No\. Points:\s+(\d+)', text)
    nv = int(nv_m.group(1)) if nv_m else None
    npts_hdr = int(npts_m.group(1)) if npts_m else 0

    # Get variable names
    vi = text.find('Variables:')
    bi_text = text.find('Binary:')
    var_lines = []
    if vi >= 0 and bi_text > vi:
        for line in text[vi:bi_text].splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2:
                var_lines.append(parts[1])  # name

    # Binary offset
    bi_bytes = header.find(b'Binary:\x0a') + 8
    if bi_bytes < 8:
        return None, None

    with open(raw_path, 'rb') as f:
        f.seek(0, 2)
        file_sz = f.tell()
    data_sz = file_sz - bi_bytes
    actual_rows = data_sz // (nv * 8) if nv else 0
    if actual_rows == 0:
        return None, None

    with open(raw_path, 'rb') as f:
        f.seek(bi_bytes)
        raw_data = f.read(actual_rows * nv * 8)

    arr = np.frombuffer(raw_data, dtype='<f8').reshape(actual_rows, nv)
    result = {}
    for i, name in enumerate(var_lines[:nv]):
        result[name] = arr[:, i]
    return result, var_lines

print("="*60)
print("Step 1: Creating SP files...")
old_sp = make_sp(OLD_SUB, f'{OUTDIR}\\tmp_old_20ns.raw', t_end='2e-8', label='old_20ns')
new_sp = make_sp(NEW_SUB, f'{OUTDIR}\\tmp_new_20ns.raw', t_end='2e-8', label='new_20ns')
old_raw = f'{OUTDIR}\\tmp_old_20ns.raw'
new_raw = f'{OUTDIR}\\tmp_new_20ns.raw'

print("Step 2: Running OLD driver (NI+N2 selector)...")
rc, out, err = run_sim(old_sp, old_raw, timeout=300)
print(f"  RC={rc} (timeout=-1 means stalled, which is expected for old driver)")
if err and 'TIMEOUT' in err:
    print("  OLD driver stalled (convergence failure) - using partial data")
elif err:
    print("  STDERR:", err[-300:])

print("Step 3: Running NEW driver (pure N2 selector)...")
rc2, out2, err2 = run_sim(new_sp, new_raw, timeout=60)
print(f"  RC={rc2}")
if err2:
    print("  STDERR:", err2[-300:])

print("Step 4: Reading RAW files...")
old_data, old_vars = read_raw(old_raw)
new_data, new_vars = read_raw(new_raw)

if old_data is None:
    print("ERROR: old simulation produced no data!")
    import sys; sys.exit(1)
if new_data is None:
    print("ERROR: new simulation produced no data!")
    import sys; sys.exit(1)

old_t_end = old_data['time'][-1] * 1e9 if 'time' in old_data else 0
new_t_end = new_data['time'][-1] * 1e9 if 'time' in new_data else 0
print(f"  Old: {len(old_data.get('time', []))} points, reached {old_t_end:.2f} ns (of 20 ns)")
print(f"  New: {len(new_data.get('time', []))} points, reached {new_t_end:.2f} ns (of 20 ns)")
old_stalled = old_t_end < 19.0  # stalled if didn't reach near end

print("Step 5: Plotting...")
fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
stall_label = f' (STALLED at {old_t_end:.1f} ns)' if old_stalled else ''
title_str = (f'IBIS Driver: Old (NI+N2 selector) vs New (pure N2 selector)\n'
             f'PRBS7 context38, first 20 ns, 50-ohm direct load\n'
             f'Old{stall_label}, New: completed {new_t_end:.1f}/20 ns')
fig.suptitle(title_str, fontsize=11, fontweight='bold')

old_label = f'OLD (NI+N2){stall_label}'
t_old = old_data['time'] * 1e9
t_new = new_data['time'] * 1e9

# Row 1: Digital input
ax = axes[0]
ax.plot(t_new, new_data.get('v(in_dig)', np.zeros_like(t_new)), 'gray', lw=1, label='Input')
ax.set_ylabel('V(IN_DIG) [V]')
ax.set_ylim(-0.3, 3.8)
ax.grid(True, alpha=0.3)
ax.legend(loc='upper right', fontsize=8)

# Row 2: PAD (driver output)
ax = axes[1]
ax.plot(t_old, old_data.get('v(pad)', np.zeros_like(t_old)), 'r-', lw=1.5, alpha=0.85, label=old_label)
ax.plot(t_new, new_data.get('v(pad)', np.zeros_like(t_new)), 'b-', lw=1.5, alpha=0.85, label='NEW (N2 only)')
if old_stalled:
    ax.axvline(x=old_t_end, color='red', lw=1, ls='--', label=f'OLD stalls at {old_t_end:.1f} ns')
ax.set_ylabel('V(PAD) [V]')
ax.set_ylim(-0.3, 3.8)
ax.grid(True, alpha=0.3)
ax.legend(loc='upper right', fontsize=8)

# Row 3: TX_OUT (channel output)
ax = axes[2]
ax.plot(t_old, old_data.get('v(tx_out)', np.zeros_like(t_old)), 'r-', lw=1.5, alpha=0.85, label=old_label)
ax.plot(t_new, new_data.get('v(tx_out)', np.zeros_like(t_new)), 'b-', lw=1.5, alpha=0.85, label='NEW (N2 only)')
if old_stalled:
    ax.axvline(x=old_t_end, color='red', lw=1, ls='--', label=f'OLD stalls at {old_t_end:.1f} ns')
ax.set_ylabel('V(TX_OUT) [V]')
ax.set_ylim(-0.3, 3.8)
ax.set_xlabel('Time [ns]')
ax.grid(True, alpha=0.3)
ax.legend(loc='upper right', fontsize=8)

plt.tight_layout()
out_png = f'{OUTDIR}\\prbs_old_vs_new_20ns.png'
plt.savefig(out_png, dpi=150, bbox_inches='tight')
print(f"Saved: {out_png}")
plt.close()
print("DONE.")
