"""
analyze_ku_kd.py — Parse pybis PRBS7 Rload raw file and analyze Ku/Kd vs input stream.

Usage:
    python analyze_ku_kd.py [rawfile]   (default: tb_pybis_prbs7_rload.raw)

Outputs:
  - Console table: for each PRBS7 bit edge, the Ku/Kd values and NX at mid-bit
  - Plots: Ku/Kd/NX vs time overlaid with V(in_dig), saved as ku_kd_analysis.png
"""

import struct
import re
import sys
import os
import numpy as np

RAW_FILE = sys.argv[1] if len(sys.argv) > 1 else "tb_pybis_prbs7_rload.raw"
UI_NS = 5.0          # bit period (ns)
TR_NS = 0.2          # rise/fall time (ns)
V_THRESHOLD = 1.65   # input threshold for edge detection (V)

# ---------------------------------------------------------------------------
# 1. Parse ngspice binary raw file
# ---------------------------------------------------------------------------
def parse_raw(path):
    with open(path, "rb") as f:
        header_bytes = f.read(4096)

    # Decode header (Latin-1 safe)
    hdr = header_bytes.decode("latin-1", errors="replace")

    nvars = int(re.search(r"No\. Variables:\s+(\d+)", hdr).group(1))

    var_section = re.search(r"Variables:(.*?)(?:Binary|Values)", hdr, re.DOTALL)
    var_names = []
    for line in var_section.group(1).strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            var_names.append(parts[1].lower())

    bi = header_bytes.find(b"Binary:\x0a") + 8
    with open(path, "rb") as f:
        f.seek(0, 2)
        file_size = f.tell()
        nrows = (file_size - bi) // (nvars * 8)
        f.seek(bi)
        data = np.frombuffer(f.read(nrows * nvars * 8), dtype="<f8")

    data = data.reshape(nrows, nvars)
    result = {name: data[:, i] for i, name in enumerate(var_names)}
    return result


# ---------------------------------------------------------------------------
# 2. Load and extract signals
# ---------------------------------------------------------------------------
print(f"Loading {RAW_FILE} ...")
try:
    sig = parse_raw(RAW_FILE)
except FileNotFoundError:
    print(f"ERROR: {RAW_FILE} not found. Run the simulation first:\n"
          "  ngspice_con.exe -b -r tb_pybis_prbs7_rload.raw tb_pybis_prbs7_rload.sp")
    sys.exit(1)

t    = sig["time"] * 1e9          # ns
vin  = sig.get("v(in_dig)", None)
vpad = sig.get("v(pad)", None)
ku   = sig.get("v(xdrv.ku)", None)
kd   = sig.get("v(xdrv.kd)", None)
nx   = sig.get("v(xdrv.nx)", None)
ni   = sig.get("v(xdrv.ni)", None)

if ku is None or kd is None:
    print("ERROR: Ku/Kd not found in raw file. Check .save directives.")
    sys.exit(1)

t_end = t[-1]
n_bits = int(t_end / UI_NS)
print(f"Simulation time: {t_end:.1f} ns  ({n_bits} bits @ {UI_NS} ns UI)")
print(f"Variables found: {list(sig.keys())}")

# ---------------------------------------------------------------------------
# 3. Per-bit mid-point analysis
# ---------------------------------------------------------------------------
print()
print(f"{'Bit':>4}  {'t_mid_ns':>9}  {'V(in_dig)':>10}  {'Ku':>8}  {'Kd':>8}  "
      f"{'NX':>8}  {'NI':>8}  Direction")
print("-" * 80)

bit_rows = []
for b in range(n_bits):
    t_mid = (b + 0.5) * UI_NS        # centre of bit window
    idx = np.searchsorted(t, t_mid)
    if idx >= len(t):
        break
    ku_v  = ku[idx]
    kd_v  = kd[idx]
    nx_v  = nx[idx] if nx is not None else float("nan")
    ni_v  = ni[idx] if ni is not None else float("nan")
    vin_v = vin[idx] if vin is not None else float("nan")

    # Determine expected direction at bit start
    t_start = b * UI_NS
    idx_s = np.searchsorted(t, t_start)
    vin_s = vin[max(0, idx_s - 1)] if vin is not None else 0.0
    vin_e = vin[min(len(vin)-1, idx_s + 1)] if vin is not None else 0.0
    direction = "RISE" if vin_e > vin_s else ("FALL" if vin_e < vin_s else "HOLD")

    row = dict(bit=b, t_mid=t_mid, vin=vin_v, ku=ku_v, kd=kd_v,
               nx=nx_v, ni=ni_v, direction=direction)
    bit_rows.append(row)

    print(f"{b:>4}  {t_mid:>9.2f}  {vin_v:>10.4f}  {ku_v:>8.4f}  {kd_v:>8.4f}  "
          f"{nx_v:>8.4f}  {ni_v:>8.4f}  {direction}")

# ---------------------------------------------------------------------------
# 4. Alignment check — Ku/Kd should be near 0/1 or 1/0 at steady state
# ---------------------------------------------------------------------------
print()
print("=== Alignment check ===")
errors = []
for r in bit_rows:
    # Mid-bit: NX should be near 5.96 (saturated = steady state)
    # Ku ~= 1 for HIGH, ~= 0 for LOW; Kd ~= 0 for HIGH, ~= 1 for LOW
    b_high = r["vin"] > V_THRESHOLD
    ku_ok  = (r["ku"] > 0.9) if b_high else (r["ku"] < 0.1)
    kd_ok  = (r["kd"] < 0.1) if b_high else (r["kd"] > 0.9)
    nx_sat = r["nx"] > 5.0  # should be near 5.96 at mid-bit

    status = "OK"
    if not ku_ok:
        status = f"KU_MISMATCH (ku={r['ku']:.3f}, expected {'~1' if b_high else '~0'})"
    elif not kd_ok:
        status = f"KD_MISMATCH (kd={r['kd']:.3f}, expected {'~0' if b_high else '~1'})"
    elif not nx_sat:
        status = f"NX_LOW (nx={r['nx']:.3f}, edge not complete at mid-bit)"

    if status != "OK":
        errors.append((r["bit"], r["t_mid"], status))
        print(f"  bit {r['bit']:>3} @ {r['t_mid']:>6.1f}ns: {status}")

if not errors:
    print("  All bits: Ku/Kd correctly tracking input HIGH/LOW.")
print()

# ---------------------------------------------------------------------------
# 5. Optional plot (requires matplotlib)
# ---------------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(4, 1, hspace=0.35)

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax4 = fig.add_subplot(gs[3], sharex=ax1)

    # Panel 1: Input & output
    ax1.plot(t, vin,  "b",  lw=0.8, label="V(in_dig)")
    ax1.plot(t, vpad, "g",  lw=0.8, label="V(pad)")
    ax1.set_ylabel("Voltage (V)")
    ax1.set_title("pybis PRBS7 — Ku/Kd runtime analysis")
    ax1.legend(loc="upper right", fontsize=7)
    ax1.grid(True, alpha=0.3)

    # Panel 2: Ku and Kd
    ax2.plot(t, ku, "r",    lw=0.8, label="Ku (pullup coeff)")
    ax2.plot(t, kd, "navy", lw=0.8, label="Kd (pulldown coeff)")
    ax2.set_ylabel("K value")
    ax2.legend(loc="upper right", fontsize=7)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(-0.1, 1.1)

    # Panel 3: NX (elapsed ns since last edge)
    if nx is not None:
        ax3.plot(t, nx, "purple", lw=0.8, label="NX (elapsed ns)")
        ax3.axhline(5.96, color="gray", lw=0.7, ls="--", label="NX cap (5.96)")
        ax3.set_ylabel("NX (ns)")
        ax3.legend(loc="upper right", fontsize=7)
        ax3.grid(True, alpha=0.3)

    # Panel 4: NI (normalised input, shows +/-0.5 for HIGH/LOW)
    if ni is not None:
        ax4.plot(t, ni, "darkorange", lw=0.8, label="NI (norm input)")
        ax4.axhline(0, color="gray", lw=0.7, ls="--")
        ax4.set_ylabel("NI")
        ax4.legend(loc="upper right", fontsize=7)
        ax4.grid(True, alpha=0.3)

    ax4.set_xlabel("Time (ns)")
    plt.savefig("ku_kd_analysis.png", dpi=150, bbox_inches="tight")
    print("Plot saved: ku_kd_analysis.png")

except ImportError:
    print("matplotlib not available — skipping plot.")
