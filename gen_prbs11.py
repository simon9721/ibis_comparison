import sys

def prbs11(n_bits):
    reg = [1]*11
    bits = []
    for _ in range(n_bits):
        bit = reg[10] ^ reg[8]
        bits.append(reg[10])
        reg = [bit] + reg[:10]
    return bits

ui = 5e-9      # 5 ns UI  →  200 Mbps
tr = 1e-12     # 1 ps — effectively instantaneous for the digital control input
vlo = 0.0
vhi = 3.3
n_bits = 400   # same — gives 2000 ns = 2 µs total, plenty of UIs

bits = prbs11(n_bits)

rows = []
t = 0.0

# Initial state: first bit value at t=0
v_prev = vhi if bits[0] == 1 else vlo
rows.append((0.0, v_prev))

for i, bit in enumerate(bits):
    v_next = vhi if bit == 1 else vlo
    t_start = i * ui
    t_end   = t_start + ui

    if v_next != v_prev:
        # transition: flat until tr starts, then ramp
        t_rise_start = t_start          # transition begins at bit boundary
        t_rise_end   = t_start + tr
        # only add flat point if not the very first row
        if rows[-1][0] < t_rise_start - 1e-15:
            rows.append((t_rise_start, v_prev))
        rows.append((t_rise_end, v_next))
    else:
        # no transition needed; just ensure we have a point at bit boundary
        if rows[-1][0] < t_start - 1e-15:
            rows.append((t_start, v_prev))

    v_prev = v_next

# Final point: hold last value to end of simulation
t_final = n_bits * ui
if rows[-1][0] < t_final - 1e-15:
    rows.append((t_final, v_prev))

# Write PWL file
with open('prbs11.pwl', 'w') as f:
    f.write('* PRBS11 PWL stimulus\n')
    f.write('* 400 bits, UI=123.5ps (8.1 Gbps HBR3), tr/tf=20ps, swing=0-3.3V\n')
    f.write('* Generated for Missouri S&T EMC Lab IBIS comparison study\n')
    f.write('* Shared across HSPICE, NGspice, and Xyce experiments\n')
    for t_val, v_val in rows:
        f.write(f'{t_val:.6e}  {v_val:.4f}\n')

print(f'Written {len(rows)} rows to prbs11.pwl')
print(f'Total sim time covered: {rows[-1][0]*1e9:.3f} ns')
print(f'First 10 bits: {bits[:10]}')
print(f'First 10 rows:')
for r in rows[:10]:
    print(f'  {r[0]*1e12:.3f} ps  {r[1]:.4f} V')
