import re
lines = open('io_buf.ibs').readlines()

# Find falling waveform V_fixture=0 and show where the fast transition happens
for i, L in enumerate(lines):
    if '[Falling Waveform]' in L:
        vfix = [x.strip() for x in lines[i:i+6] if 'V_fixture' in x]
        if '= 0' not in (vfix[0] if vfix else ''):
            continue
        print(f'Falling Waveform V_fixture=0: looking for fast drop...')
        rows = []
        for j in range(i+5, min(i+1500, len(lines))):
            if lines[j].strip().startswith('['):
                break
            m = re.match(r'\s+([\d.]+)n\s+(\S+)', lines[j])
            if m:
                rows.append((float(m.group(1)), float(m.group(2))))
        # Find points where voltage drops more than 0.05V/step
        prev_v = rows[0][1]
        for t, v in rows[1:]:
            dv = v - prev_v
            if dv < -0.01:  # fast falling step
                print(f'  Fast drop at t={t:.4f}ns: V={prev_v:.4f} -> {v:.4f}  (dV={dv:.4f}V)')
            prev_v = v
        print(f'  Total: t=0 V={rows[0][1]:.4f}  t={rows[-1][0]:.4f}ns V={rows[-1][1]:.6f}')
        break

