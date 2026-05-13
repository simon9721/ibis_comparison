"""Plot old vs new Ku/Kd driver from existing RAW files (no simulation)."""
import re, struct, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read_raw(path, max_rows=None):
    with open(path, 'rb') as f:
        raw_bytes = f.read(65536)
        f.seek(0, 2); sz = f.tell()
    text = raw_bytes.decode('latin-1', errors='replace')
    nv = int(re.search(r'No\. Variables:\s+(\d+)', text).group(1))
    # Extract variable names: lines like "  0  time  time"
    names = re.findall(r'^\s+\d+\s+(\S+)\s+\S+', text, re.MULTILINE)
    # Binary marker: handle \n or \r\n after "Binary:"
    bi_pos = raw_bytes.find(b'Binary:')
    if bi_pos < 0:
        raise RuntimeError("Binary marker not found")
    bi = bi_pos + 7
    if raw_bytes[bi:bi+2] == b'\r\n':
        bi += 2
    else:
        bi += 1  # skip \n
    rows = (sz - bi) // (nv * 8)
    if max_rows: rows = min(rows, max_rows)
    with open(path, 'rb') as f:
        f.seek(bi)
        data = np.frombuffer(f.read(rows * nv * 8), dtype='<f8').reshape(rows, nv)
    return {names[i].lower(): data[:, i] for i in range(min(len(names), nv))}

BASE = r'C:\Users\simom\Desktop\IBIS_Comparison\ngspice_pybis'
OLD  = os.path.join(BASE, 'tmp_old_20ns.raw')
NEW  = os.path.join(BASE, 'tmp_new_20ns.raw')

print(f"Reading OLD: {OLD}")
old = read_raw(OLD)
t_old = old['time'] * 1e9
t_stall = t_old[-1]
n_old = len(t_old)
print(f"  {n_old:,} points, reached {t_stall:.2f} ns (stalled)")

print(f"Reading NEW: {NEW}")
new = read_raw(NEW)
t_new = new['time'] * 1e9
t_end = t_new[-1]
print(f"  {len(t_new):,} points, {t_end:.2f} ns total")

fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True)
fig.suptitle(
    f'OLD driver (NI+N2 selector)  vs  NEW driver (pure N2 selector)\n'
    f'Same testbench: PRBS7, 2 ns UI, 50-ohm load, 20 ns total\n'
    f'OLD: {n_old:,} timesteps, stalls at {t_stall:.1f} ns     NEW: {len(t_new):,} timesteps, completes 20 ns',
    fontsize=10, fontweight='bold'
)

# Digital input — shared stimulus (same PWL in both SP files)
axes[0].plot(t_new, new['v(in_dig)'], color='gray', lw=1, label='IN_DIG (shared)')
axes[0].set_ylabel('IN_DIG (V)')
axes[0].set_ylim(-0.2, 3.7)
axes[0].legend(fontsize=8, loc='upper right')
axes[0].grid(True, alpha=0.3)

# PAD output
axes[1].plot(t_old, old['v(pad)'], 'r-', lw=0.8, alpha=0.85, label=f'OLD — stalls @{t_stall:.1f} ns ({n_old:,} pts)')
axes[1].plot(t_new, new['v(pad)'], 'b-', lw=1.2, alpha=0.9,  label=f'NEW — completes ({len(t_new):,} pts)')
axes[1].axvline(t_stall, color='red', lw=1.2, ls='--')
axes[1].annotate(f'OLD stalls\n{t_stall:.1f} ns', xy=(t_stall, 0.5), xytext=(t_stall+0.3, 1.0),
                  fontsize=8, color='red', arrowprops=dict(arrowstyle='->', color='red'))
axes[1].set_ylabel('V(PAD) (V)')
axes[1].set_ylim(-0.2, 3.7)
axes[1].legend(fontsize=8, loc='upper right')
axes[1].grid(True, alpha=0.3)

# TX_OUT
axes[2].plot(t_old, old['v(tx_out)'], 'r-', lw=0.8, alpha=0.85, label=f'OLD — stalls @{t_stall:.1f} ns')
axes[2].plot(t_new, new['v(tx_out)'], 'b-', lw=1.2, alpha=0.9,  label='NEW — completes')
axes[2].axvline(t_stall, color='red', lw=1.2, ls='--')
axes[2].set_ylabel('V(TX_OUT) (V)')
axes[2].set_ylim(-0.2, 3.7)
axes[2].set_xlabel('Time (ns)')
axes[2].legend(fontsize=8, loc='upper right')
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
out = os.path.join(BASE, 'prbs_old_vs_new_kukd.png')
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f"Saved: {out}")
