"""
Generate prbs7.pwl for NGspice V-source stimulus.
PRBS7 (period = 127 bits), 200 bits total, UI = 5 ns, tr/tf = 200 ps.

Usage: python scripts/gen_prbs7.py
Output: ngspice_pybis/prbs7.pwl  (symlinked to ngspice_refspice/prbs7.pwl)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def prbs7(n_bits):
    reg = [1] * 7
    bits = []
    for _ in range(n_bits):
        bit = reg[6] ^ reg[5]
        bits.append(reg[6])
        reg = [bit] + reg[:6]
    return bits

ui  = 5.0e-9    # 5 ns UI = 200 Mbps
tr  = 200e-12   # 200 ps rise/fall — matches actual buffer slew rate
vlo = 0.0
vhi = 3.3
n_bits = 200    # 200 bits = 1000 ns; covers >1 full PRBS7 period (127 bits)

bits = prbs7(n_bits)

rows = []
# Inverted mapping: PRBS bit=1 -> vlo (0V), bit=0 -> vhi (3.3V).
# This ensures the stimulus starts LOW (in_dig=0V at t=0), which matches
# the DC operating point for both the transistor-level and pybis models
# (nfet ON = valid GND path; Ku=0/Kd=1 = correct LOW state).  Without
# this, the HIGH-first start triggers a startup transient in the pybis
# B-source Ku/Kd expressions that produces millions of tiny timesteps.
v_prev = vlo if bits[0] == 1 else vhi
rows.append((0.0, v_prev))

for i, bit in enumerate(bits):
    v_next = vlo if bit == 1 else vhi
    t_start = i * ui
    if v_next != v_prev:
        if rows[-1][0] < t_start - 1e-15:
            rows.append((t_start, v_prev))
        rows.append((t_start + tr, v_next))
    else:
        if rows[-1][0] < t_start - 1e-15:
            rows.append((t_start, v_prev))
    v_prev = v_next

t_final = n_bits * ui
if rows[-1][0] < t_final - 1e-15:
    rows.append((t_final, v_prev))

def write_vstim_inc(path, node, rows, n_bits, ui, tr, vlo, vhi):
    """Write a V-source inline PWL .inc file.
    Using V-source (not B-source): ngspice queues PWL breakpoints as timestep
    events and steps directly to each one, avoiding sub-picosecond overhead.
    """
    with open(path, "w") as f:
        f.write(f"* PRBS7 V-source PWL stimulus\n")
        f.write(f"* {n_bits} bits, UI={ui*1e9:.1f}ns ({1/ui/1e6:.0f} Mbps), tr/tf={tr*1e12:.0f}ps, swing={vlo}-{vhi}V\n")
        f.write(f"* Missouri S&T EMC Lab IBIS comparison study\n")
        f.write(f"* NOTE: V-source PWL (not B-source) -- ngspice queues breakpoints as events\n")
        # First row must be on the same line as PWL(
        t0, v0 = rows[0]
        f.write(f"Vstim  {node}  0  PWL({t0:.9e} {v0:.4f}\n")
        for i, (t_val, v_val) in enumerate(rows[1:], 1):
            suffix = ")" if i == len(rows) - 1 else ""
            f.write(f"+ {t_val:.9e}  {v_val:.4f}{suffix}\n")


for folder, node in [("ngspice_pybis", "in_dig"), ("ngspice_refspice", "in_src")]:
    out = ROOT / folder / "prbs7_vstim.inc"
    write_vstim_inc(out, node, rows, n_bits, ui, tr, vlo, vhi)
    print(f"Written {len(rows)} rows -> {out}")

print(f"Total sim time: {rows[-1][0]*1e9:.1f} ns")
print(f"First 10 rows:")
for r in rows[:10]:
    print(f"  {r[0]*1e9:.4f} ns  {r[1]:.4f} V")
