"""Eye diagram comparison: transistor-level refspice vs pybis2spice.

Inputs:
  ngspice_refspice/tb_refspice_prbs7_batch.raw  -> V(ntst_ref)
  ngspice_pybis/tb_pybis_prbs7_batch.raw        -> V(ntst)

UI = 5 ns (200 Mbps).  Bits decoded from V(in_dig) / V(pad_ref) threshold.

Outputs (plots/validation/):
  eye_comparison_ntst.png  -- overlaid eye diagram, both models, load-side node
  eye_metrics.txt          -- eye height, width, rise/fall 20-80%, overshoot
"""

from pathlib import Path
import struct

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
REF_DIR  = ROOT / "ngspice_refspice"
PYB_DIR  = ROOT / "ngspice_pybis"
OUT_DIR  = ROOT / "plots" / "validation"

UI_S   = 5e-9       # 5 ns unit interval (200 Mbps)
VDD    = 3.3
VLOW   = 0.0
VMID   = VDD / 2    # 1.65 V crossing threshold

# Eye window: centre 1 UI, ±0.5 UI; normalise to [-0.5, 0.5] in time
EYE_HALF = 1.0      # half-window in UI (use 2 UI for context)


# ── raw file parser (same as plot_validation_results.py) ─────────────────────

def parse_ngspice_raw(path: Path):
    data = path.read_bytes()
    marker = b"Binary:\n"
    idx = data.find(marker)
    if idx < 0:
        raise RuntimeError(f"Binary marker not found in {path}")
    header = data[:idx].decode("latin1")
    lines  = header.splitlines()

    nvars = npts = None
    variables   = []
    reading_vars = False
    for line in lines:
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":", 1)[1])
        elif line.strip() == "Variables:":
            reading_vars = True
        elif reading_vars and line.startswith("\t"):
            variables.append(line.split()[1])

    payload = data[idx + len(marker):]
    if npts == 0:
        npts = len(payload) // (8 * nvars)
    values = struct.unpack("<" + "d" * (nvars * npts), payload[: 8 * nvars * npts])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))
    return {name: arr[:, i] for i, name in enumerate(variables)}


# ── eye diagram builder ───────────────────────────────────────────────────────

def build_eye(time: np.ndarray, voltage: np.ndarray,
              ui: float = UI_S,
              n_ui_window: float = 2.0,
              skip_uis: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """Fold waveform into eye diagram.

    Returns (t_eye, v_eye) arrays, each a flat concatenation of NaN-separated
    UI-length segments so plt.plot draws them as separate traces.

    skip_uis: skip the first N UIs (startup transient).
    """
    half   = n_ui_window / 2 * ui      # half-window in seconds
    t_min  = skip_uis * ui
    t_max  = time[-1]

    segs_t = []
    segs_v = []

    t0 = t_min
    while t0 + 2 * half <= t_max:
        t1 = t0 + 2 * half
        mask = (time >= t0) & (time < t1)
        if mask.sum() > 1:
            t_seg = ((time[mask] - t0) - half) / ui   # normalise to UI
            v_seg = voltage[mask]
            segs_t.append(t_seg)
            segs_t.append(np.array([np.nan]))
            segs_v.append(v_seg)
            segs_v.append(np.array([np.nan]))
        t0 += ui

    if not segs_t:
        return np.array([]), np.array([])
    return np.concatenate(segs_t), np.concatenate(segs_v)


# ── metrics ───────────────────────────────────────────────────────────────────

def eye_metrics(time: np.ndarray, voltage: np.ndarray,
                ui: float = UI_S,
                skip_uis: int = 2,
                vdd: float = VDD) -> dict:
    """Compute eye height, width, rise/fall 20-80% from a PRBS waveform.

    Strategy:
      - Estimate actual HIGH/LOW signal levels from percentiles (adaptive).
      - At the centre of each UI (+-10% window) collect voltages -> eye opening
      - At transitions, fit 20-80% crossing times -> rise/fall
      - Eye width from mid-crossing histogram
    """
    t_start = skip_uis * ui
    mask    = time >= t_start
    t       = time[mask]
    v       = voltage[mask]

    # ── Adaptive signal levels (robust to non-uniform sampling density) ──────
    # Use p1/p99 instead of p5/p95 so that highly non-uniform step-size
    # distributions (e.g. pybis: tiny steps in LOW, larger steps in HIGH)
    # don't push the upper estimate near 0V.
    v_lo_est  = np.percentile(v, 1)   # representative LOW level
    v_hi_est  = np.percentile(v, 99)  # representative HIGH level
    vmid_sig  = (v_lo_est + v_hi_est) / 2
    swing     = v_hi_est - v_lo_est

    v20 = v_lo_est + 0.20 * swing
    v50 = vmid_sig
    v80 = v_lo_est + 0.80 * swing

    # ── eye height: sample near centre of each UI ──────────────────────────
    v_high_samples = []
    v_low_samples  = []

    t0 = t_start
    while t0 + ui <= t[-1]:
        t_centre = t0 + 0.5 * ui
        win = 0.1 * ui
        mid_mask = (t >= t_centre - win) & (t <= t_centre + win)
        if mid_mask.sum() > 0:
            vmid_samp = v[mid_mask].mean()
            if vmid_samp > vmid_sig:
                v_high_samples.append(vmid_samp)
            else:
                v_low_samples.append(vmid_samp)
        t0 += ui

    eye_high = np.percentile(v_high_samples, 5)  if v_high_samples else np.nan
    eye_low  = np.percentile(v_low_samples,  95) if v_low_samples  else np.nan
    eye_height = eye_high - eye_low

    rise_times  = []
    fall_times  = []
    cross50_rel = []   # crossing time relative to nearest UI edge (in UI)

    # detect crossings by sign change of (v - threshold)
    for vth, direction in [(v50, None)]:
        signs = np.sign(v - vth)
        for i in range(len(signs) - 1):
            if signs[i] == 0 or signs[i + 1] == 0:
                continue
            if signs[i] != signs[i + 1]:
                # linear interpolation for exact crossing time
                t_cross = t[i] + (vth - v[i]) / (v[i + 1] - v[i]) * (t[i + 1] - t[i])
                cross_dir = "rise" if signs[i] < 0 else "fall"
                # phase relative to nearest UI edge (in UI)
                ui_edge  = round(t_cross / ui) * ui
                phase_ui = (t_cross - ui_edge) / ui
                cross50_rel.append((phase_ui, cross_dir))

    # rise/fall: look for pairs of 20% and 80% crossings
    v_signs20 = np.sign(v - v20)
    v_signs80 = np.sign(v - v80)

    for i in range(len(v_signs20) - 1):
        if v_signs20[i] < 0 and v_signs20[i + 1] > 0:   # rising through 20%
            t20 = t[i] + (v20 - v[i]) / (v[i + 1] - v[i]) * (t[i + 1] - t[i])
            # find next 80% rising crossing
            for j in range(i + 1, min(i + 200, len(v_signs80) - 1)):
                if v_signs80[j] < 0 and v_signs80[j + 1] > 0:
                    t80 = t[j] + (v80 - v[j]) / (v[j + 1] - v[j]) * (t[j + 1] - t[j])
                    tr = t80 - t20
                    if 0 < tr < ui:
                        rise_times.append(tr)
                    break

        if v_signs80[i] > 0 and v_signs80[i + 1] < 0:   # falling through 80%
            t80 = t[i] + (v80 - v[i]) / (v[i + 1] - v[i]) * (t[i + 1] - t[i])
            for j in range(i + 1, min(i + 200, len(v_signs20) - 1)):
                if v_signs20[j] > 0 and v_signs20[j + 1] < 0:
                    t20 = t[j] + (v20 - v[j]) / (v[j + 1] - v[j]) * (t[j + 1] - t[j])
                    tf = t20 - t80   # t80 < t20 on a falling edge
                    if 0 < tf < ui:
                        fall_times.append(tf)
                    break

    # overshoot / undershoot relative to actual signal swing
    overshoot  = (v.max() - v_hi_est) / swing * 100 if swing > 0 else np.nan
    undershoot = (v_lo_est - v.min()) / swing * 100 if swing > 0 else np.nan

    # eye width: from 50% crossing spread
    if cross50_rel:
        phases_rise = [p for (p, d) in cross50_rel if d == "rise"]
        phases_fall = [p for (p, d) in cross50_rel if d == "fall"]
        # eye width = 1 UI - (spread of rise crossings) - (spread of fall crossings)
        rise_jitter = (np.percentile(phases_rise, 95) - np.percentile(phases_rise, 5)) if len(phases_rise) > 2 else np.nan
        fall_jitter = (np.percentile(phases_fall, 95) - np.percentile(phases_fall, 5)) if len(phases_fall) > 2 else np.nan
        eye_width_ui = 1.0 - rise_jitter - fall_jitter if not (np.isnan(rise_jitter) or np.isnan(fall_jitter)) else np.nan
    else:
        eye_width_ui = np.nan

    return {
        "eye_height_V"   : eye_height,
        "eye_high_V"     : eye_high,
        "eye_low_V"      : eye_low,
        "eye_width_UI"   : eye_width_ui,
        "rise_time_ps"   : np.median(rise_times)  * 1e12 if rise_times  else np.nan,
        "fall_time_ps"   : np.median(fall_times)  * 1e12 if fall_times  else np.nan,
        "overshoot_pct"  : overshoot,
        "undershoot_pct" : undershoot,
        "n_rise"         : len(rise_times),
        "n_fall"         : len(fall_times),
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading refspice raw...")
    ref = parse_ngspice_raw(REF_DIR / "tb_refspice_prbs7_batch.raw")
    print(f"  {len(ref['time'])} points, t_max={ref['time'][-1]*1e9:.1f} ns")
    v_r = ref["v(ntst_ref)"]
    print(f"  v(ntst_ref): min={v_r.min():.3f}V  max={v_r.max():.3f}V  "
          f"p1={np.percentile(v_r,1):.3f}V  p99={np.percentile(v_r,99):.3f}V")

    print("Loading pybis raw...")
    pyb = parse_ngspice_raw(PYB_DIR / "tb_pybis_prbs7_batch.raw")
    print(f"  {len(pyb['time'])} points, t_max={pyb['time'][-1]*1e9:.1f} ns")
    v_p = pyb["v(ntst)"]
    print(f"  v(ntst):     min={v_p.min():.3f}V  max={v_p.max():.3f}V  "
          f"p1={np.percentile(v_p,1):.3f}V  p99={np.percentile(v_p,99):.3f}V")

    # ── eye diagram plot ────────────────────────────────────────────────────
    N_UI_WIN = 2.0   # show 2 UI window
    t_ref, v_ref = build_eye(ref["time"], ref["v(ntst_ref)"], n_ui_window=N_UI_WIN)
    t_pyb, v_pyb = build_eye(pyb["time"], pyb["v(ntst)"],    n_ui_window=N_UI_WIN)

    plt.rcParams.update({
        "figure.figsize": (8, 5),
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    fig, ax = plt.subplots()
    ax.plot(t_ref, v_ref, color="steelblue",   alpha=0.15, lw=0.5, label="Transistor-level (refspice)")
    ax.plot(t_pyb, v_pyb, color="darkorange",  alpha=0.15, lw=0.5, label="pybis2spice")

    ax.axhline(VDD,  color="gray", ls="--", lw=0.8, alpha=0.5)
    ax.axhline(0.0,  color="gray", ls="--", lw=0.8, alpha=0.5)
    ax.axhline(VMID, color="gray", ls=":",  lw=0.8, alpha=0.5, label=f"{VMID:.2f} V midpoint")
    ax.axvline(0,    color="gray", ls="-",  lw=0.5, alpha=0.3)

    ax.set_xlim(-N_UI_WIN / 2, N_UI_WIN / 2)
    ax.set_ylim(-0.3, VDD + 0.3)
    ax.set_xlabel("Time (UI)")
    ax.set_ylabel("Voltage (V)")
    t_max_ref = ref["time"][-1] * 1e9
    t_max_pyb = pyb["time"][-1] * 1e9
    ax.set_title(
        f"Eye Diagram — Load Node (50 ohm)  |  PRBS7 @ 200 Mbps\n"
        f"refspice: {t_max_ref:.0f} ns  |  pybis: {t_max_pyb:.0f} ns (partial)"
    )

    # deduplicate legend entries (NaN-separated traces give one per draw call)
    handles, labels = ax.get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, labels):
        if l not in seen:
            seen[l] = h
    ax.legend(list(seen.values()), list(seen.keys()), loc="upper right")

    fig.tight_layout()
    out = OUT_DIR / "eye_comparison_ntst.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")

    # ── metrics ─────────────────────────────────────────────────────────────
    print("\nComputing metrics...")
    m_ref = eye_metrics(ref["time"], ref["v(ntst_ref)"])
    m_pyb = eye_metrics(pyb["time"], pyb["v(ntst)"])

    lines = [
        "Eye Diagram Metrics  --  PRBS7 @ 200 Mbps, 50-ohm load, ngspice",
        f"  refspice: {t_max_ref:.0f} ns full run  |  pybis: {t_max_pyb:.0f} ns (partial, ~21 UI)",
        "=" * 60,
        f"{'Metric':<22}  {'Transistor-level':>18}  {'pybis2spice':>14}",
        "-" * 60,
    ]
    keys = [
        ("eye_height_V",   "Eye Height (V)",        ".3f",  1),
        ("eye_high_V",     "Eye High (V)",           ".3f",  1),
        ("eye_low_V",      "Eye Low (V)",            ".3f",  1),
        ("eye_width_UI",   "Eye Width (UI)",         ".3f",  1),
        ("rise_time_ps",   "Rise Time 20-80% (ps)",  ".1f",  1),
        ("fall_time_ps",   "Fall Time 80-20% (ps)",  ".1f",  1),
        ("overshoot_pct",  "Overshoot (%Vswing)",    ".1f",  1),
        ("undershoot_pct", "Undershoot (%Vswing)",   ".1f",  1),
    ]
    for key, label, fmt, _ in keys:
        vr = m_ref[key]
        vp = m_pyb[key]
        fr = f"{vr:{fmt}}" if not np.isnan(vr) else "n/a"
        fp = f"{vp:{fmt}}" if not np.isnan(vp) else "n/a"
        lines.append(f"{label:<22}  {fr:>18}  {fp:>14}")

    lines.append("=" * 60)
    report = "\n".join(lines)
    print(report)

    txt_out = OUT_DIR / "eye_metrics.txt"
    txt_out.write_text(report + "\n", encoding="utf-8")
    print(f"Saved: {txt_out}")


if __name__ == "__main__":
    main()
