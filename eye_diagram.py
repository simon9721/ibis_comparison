"""
eye_diagram.py — IBIS Comparison Study
Missouri S&T EMC Lab — Signal Integrity Group — April 2026

Parses HSPICE ASCII .tr0 files (POST=2) and produces:
  - Eye diagram plot (PNG)
  - Transition waveform plot (PNG)
  - Printed metrics: eye height, eye width, rise time, fall time,
    overshoot, undershoot

Usage:
    python eye_diagram.py tb_exp1.tr0 --signal v(n10b) --ui 5e-9
    python eye_diagram.py tb_exp1.tr0 --signal v(n10b) --ui 5e-9 --skip_ui 10

Design notes:
  - Simulator-agnostic core: load_waveform / build_eye / measure_eye /
    measure_transitions / plot_eye are all pure numpy/matplotlib.
  - HSPICE-specific logic is isolated in parse_hspice_tr0().
  - To add NGspice or Xyce support later, add a parse_*() function and
    wire it into load_waveform() via the 'fmt' argument.
"""

import sys
import re
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional: import /eye/eye_tools for extra plot modes + richer metrics
# ---------------------------------------------------------------------------
_EYE_TOOLS_DIR = Path(__file__).resolve().parent.parent / 'eye'
if _EYE_TOOLS_DIR.is_dir() and str(_EYE_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_EYE_TOOLS_DIR))

try:
    from eye_tools import EyeDiagramGenerator, analyze_eye_opening as _eye_analyze
    _EYE_TOOLS_OK = True
except ImportError:
    _EYE_TOOLS_OK = False


# =============================================================================
# 1. HSPICE ASCII tr0 parser
# =============================================================================

def parse_hspice_tr0(filepath):
    """
    Parse a HSPICE ASCII .tr0 file (POST=2 / POST_VERSION=2001 or 9601).

    Returns
    -------
    dict  {signal_name: np.ndarray}  — all signals including 'time'
    """
    filepath = Path(filepath)
    raw = filepath.read_text(errors='replace')

    # ---- locate signal name block ----------------------------------------
    # Use str.find() to avoid regex issues with '$' metacharacter
    time_idx = raw.find('TIME')
    end_idx  = raw.find('$&%#')
    if time_idx == -1 or end_idx == -1 or end_idx < time_idx:
        raise ValueError("Could not find TIME / $&%# markers in header. "
                         "Is this a POST=2 ASCII .tr0 file?")

    name_block = raw[time_idx + 4 : end_idx]
    # HSPICE truncates names at 16 chars — closing ')' may be missing
    raw_names = [s.strip() for s in name_block.split() if s.strip()]
    def _fix_name(n):
        # Close unclosed parenthesis
        if '(' in n and not n.endswith(')'):
            n = n + ')'
        return n
    signal_names = ['time'] + [_fix_name(n) for n in raw_names]
    n_signals = len(signal_names)

    # ---- locate data block -----------------------------------------------
    data_start = end_idx + len('$&%#')
    data_text = raw[data_start:]

    # Each value is 14 characters wide, no delimiter, continuous stream.
    # Strip all whitespace/newlines to get a flat character stream.
    flat = re.sub(r'\s+', '', data_text)

    # Handle HSPICE sign convention: '-' can appear as first char of a field
    # but there are no spaces between fields.
    # Extract all 14-char tokens.
    field_width = 13
    n_chars = len(flat)
    n_values = n_chars // field_width

    values = []
    i = 0
    while i + field_width <= n_chars:
        token = flat[i:i + field_width]
        try:
            values.append(float(token))
        except ValueError:
            # Non-numeric token (trailing junk) — stop
            break
        i += field_width

    values = np.array(values, dtype=np.float64)

    # Reshape into (n_timepoints, n_signals)
    n_rows = len(values) // n_signals
    if n_rows == 0:
        raise ValueError("No data rows found after header.")

    values = values[:n_rows * n_signals].reshape(n_rows, n_signals)

    result = {}
    for idx, name in enumerate(signal_names):
        result[name] = values[:, idx]

    return result


# =============================================================================
# 2. Generic loader — extend here for NGspice / Xyce
# =============================================================================

def load_waveform(filepath, fmt='hspice'):
    """
    Load waveform data from a simulator output file.

    Parameters
    ----------
    filepath : str or Path
    fmt      : 'hspice'   — HSPICE ASCII .tr0 (POST=2)
               'ngspice'  — (future) NGspice .raw ASCII
               'xyce'     — (future) Xyce .prn CSV

    Returns
    -------
    dict  {signal_name_lower: np.ndarray}
    """
    fmt = fmt.lower()
    if fmt == 'hspice':
        data = parse_hspice_tr0(filepath)
    else:
        raise NotImplementedError(f"Format '{fmt}' not yet implemented. "
                                  "Add a parser and wire it in here.")
    # Normalise keys to lower-case
    return {k.lower(): v for k, v in data.items()}


# =============================================================================
# 3. Eye diagram builder
# =============================================================================

def build_eye(time, voltage, ui, skip_ui=5, n_interp=2000, n_ui=3):
    """
    Fold a waveform into an eye diagram.

    Parameters
    ----------
    time     : 1-D array, seconds
    voltage  : 1-D array, volts
    ui       : float, unit interval in seconds
    skip_ui  : int, number of UIs to skip at start (allow buffer to settle)
    n_interp : int, number of time points per UI in the output grid
    n_ui     : int, number of unit intervals to display (default: 3)

    Returns
    -------
    t_eye    : 1-D array, time axis 0 → n_ui*UI
    eye_slices : 2-D array (n_slices, n_interp*n_ui) — each row is one tiled slice
    """
    t_start = time[0] + skip_ui * ui
    t_end   = time[-1]

    # Common time grid for one UI (interpolated)
    t_ui = np.linspace(0, ui, n_interp, endpoint=False)

    slices = []
    t = t_start
    while t + ui <= t_end:
        # Extract one UI worth of data
        mask = (time >= t) & (time < t + ui)
        if mask.sum() < 2:
            t += ui
            continue
        t_seg = time[mask] - t          # normalise to 0
        v_seg = voltage[mask]
        # Interpolate onto uniform grid
        v_interp = np.interp(t_ui, t_seg, v_seg)
        slices.append(v_interp)
        t += ui

    if len(slices) == 0:
        raise ValueError("No complete UI slices found. "
                         "Check ui value and skip_ui.")

    eye_slices = np.array(slices)

    # n_ui eye: tile each slice n_ui times
    eye_slices_nui = np.tile(eye_slices, n_ui)
    t_eye = np.linspace(0, n_ui * ui, n_interp * n_ui, endpoint=False)

    return t_eye, eye_slices_nui


# =============================================================================
# 4. Eye metrics
# =============================================================================

def measure_eye(t_eye, eye_slices, vdd=3.3, threshold_pct=0.20, n_ui=3):
    """
    Measure eye height and eye width from a folded eye diagram.

    Eye height : at the horizontal centre (UI midpoint), the vertical gap
                 between the worst-case low '1' level and worst-case high '0'
                 level across all slices.
    Eye width  : at the vertical centre (Vdd/2), the horizontal span where
                 no slice crosses through the mid-level (i.e. the eye is open).

    Returns dict with keys: eye_height, eye_width, v_eye_high, v_eye_low
    """
    n_cols = eye_slices.shape[1]
    # Work on the centre UI only — generalised for any n_ui
    # For n_ui=2: 1/4 .. 3/4 (UI 0.5–1.5); for n_ui=3: 1/3 .. 2/3 (UI 1–2)
    centre_start = (n_ui - 1) * n_cols // (2 * n_ui)
    centre_end   = (n_ui + 1) * n_cols // (2 * n_ui)
    centre       = eye_slices[:, centre_start:centre_end]
    t_centre     = t_eye[centre_start:centre_end]

    v_min_per_col = np.min(centre, axis=0)
    v_max_per_col = np.max(centre, axis=0)

    # Eye height at horizontal centre column
    mid_col = centre.shape[1] // 2
    half = max(1, centre.shape[1] // 10)   # use middle 20% of centre
    mid_slice = centre[:, mid_col - half : mid_col + half]
    v_eye_high = float(np.min(np.max(mid_slice, axis=0)))
    v_eye_low  = float(np.max(np.min(mid_slice, axis=0)))
    eye_height = v_eye_high - v_eye_low

    # Eye width: columns where the eye is open
    # Open = v_min > 20%Vdd (all traces are high)
    #     OR v_max < 80%Vdd (all traces are low)
    # NOT open = some trace is in the transition band
    eye_open_high = v_min_per_col > vdd * threshold_pct
    eye_open_low  = v_max_per_col < vdd * (1.0 - threshold_pct)
    eye_open      = eye_open_high | eye_open_low

    dt = t_centre[1] - t_centre[0] if len(t_centre) > 1 else 0.0
    # Find the longest contiguous run of open columns
    max_run = 0
    cur_run = 0
    for val in eye_open:
        if val:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0
    eye_width = float(max_run * dt)

    return {
        'eye_height': float(eye_height),
        'eye_width':  float(eye_width),
        'v_eye_high': float(v_eye_high),
        'v_eye_low':  float(v_eye_low),
    }


# =============================================================================
# 5. Transition metrics
# =============================================================================

def measure_transitions(time, voltage, vdd=3.3, n_transitions=20):
    """
    Measure rise time, fall time, overshoot, undershoot.

    Uses the first n_transitions detected edges.

    Returns dict with keys:
        rise_time, fall_time, overshoot_abs, undershoot_abs,
        overshoot_pct, undershoot_pct
    """
    v_lo = 0.20 * vdd
    v_hi = 0.80 * vdd

    # Detect threshold crossings
    def find_crossings(t, v, level, direction):
        """Return times of threshold crossings."""
        above = v >= level
        if direction == 'rising':
            cross = (~above[:-1]) & above[1:]
        else:
            cross = above[:-1] & (~above[1:])
        idx = np.where(cross)[0]
        # Linear interpolation for precise crossing time
        times = []
        for i in idx:
            t0, t1 = t[i], t[i+1]
            v0, v1 = v[i], v[i+1]
            if v1 != v0:
                tc = t0 + (level - v0) * (t1 - t0) / (v1 - v0)
                times.append(tc)
        return np.array(times)

    rise_lo = find_crossings(time, voltage, v_lo, 'rising')
    rise_hi = find_crossings(time, voltage, v_hi, 'rising')
    fall_hi = find_crossings(time, voltage, v_hi, 'falling')
    fall_lo = find_crossings(time, voltage, v_lo, 'falling')

    rise_times = []
    for t_lo in rise_lo[:n_transitions]:
        # Find FIRST hi crossing after this lo crossing
        # but within 3x the expected UI to avoid counting ringing
        candidates = rise_hi[(rise_hi > t_lo)]
        if len(candidates):
            rise_times.append(candidates[0] - t_lo)

    fall_times = []
    for t_hi in fall_hi[:n_transitions]:
        # Find FIRST lo crossing after this hi crossing
        candidates = fall_lo[(fall_lo > t_hi)]
        if len(candidates):
            fall_times.append(candidates[0] - t_hi)

    # Filter out outliers > 3× median (caused by ringing re-crossings)
    def _filter_outliers(arr):
        if len(arr) < 3:
            return arr
        arr = np.array(arr)
        med = np.median(arr)
        return arr[arr < 3.0 * med].tolist()

    rise_times = _filter_outliers(rise_times)
    fall_times = _filter_outliers(fall_times)

    # Overshoot / undershoot
    overshoot_abs  = max(0.0, float(np.max(voltage)) - vdd)
    undershoot_abs = max(0.0, -float(np.min(voltage)))

    return {
        'rise_time':      float(np.median(rise_times))  if rise_times  else float('nan'),
        'fall_time':      float(np.median(fall_times))  if fall_times  else float('nan'),
        'overshoot_abs':  overshoot_abs,
        'undershoot_abs': undershoot_abs,
        'overshoot_pct':  100.0 * overshoot_abs  / vdd,
        'undershoot_pct': 100.0 * undershoot_abs / vdd,
    }


# =============================================================================
# 6. Plot: eye diagram
# =============================================================================

def plot_eye(t_eye, eye_slices, metrics, ui, title='Eye Diagram',
             outfile='eye.png', vdd=3.3, n_ui=3):
    """
    Render eye diagram as a heatmap density plot with metrics annotation.
    """
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    t_ns = t_eye * 1e9  # convert to ns for display

    # Density heatmap
    # Build 2-D histogram
    n_tbins = 300
    n_vbins = 300
    t_flat = np.tile(t_ns, eye_slices.shape[0])
    v_flat = eye_slices.flatten()

    h, xedges, yedges = np.histogram2d(
        t_flat, v_flat,
        bins=[n_tbins, n_vbins],
        range=[[t_ns[0], t_ns[-1]], [-0.5, vdd + 0.5]]
    )

    # Log scale for density
    h_log = np.log1p(h.T)

    ax.imshow(h_log, origin='lower', aspect='auto',
              extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
              cmap='plasma', interpolation='bilinear')

    # UI boundary lines (one per UI boundary, excluding t=0)
    ui_ns = ui * 1e9
    for k in range(1, n_ui + 1):
        ax.axvline(ui_ns * k, color='#00ff88', lw=0.8, ls='--', alpha=0.6)

    # Threshold lines
    ax.axhline(0.2 * vdd, color='#ff6b6b', lw=0.7, ls=':', alpha=0.7,
               label=f'20% Vdd = {0.2*vdd:.2f}V')
    ax.axhline(0.8 * vdd, color='#ff6b6b', lw=0.7, ls=':', alpha=0.7,
               label=f'80% Vdd = {0.8*vdd:.2f}V')

    # Metrics text box
    mtext = (
        f"Eye Height : {metrics['eye_height']*1000:.1f} mV\n"
        f"Eye Width  : {metrics['eye_width']*1e12:.1f} ps\n"
        f"V_high     : {metrics['v_eye_high']:.3f} V\n"
        f"V_low      : {metrics['v_eye_low']*1000:.1f} mV"
    )
    ax.text(0.02, 0.97, mtext, transform=ax.transAxes,
            fontsize=9, va='top', ha='left',
            color='#e0e0e0', fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a1a',
                      edgecolor='#444', alpha=0.85))

    ax.set_xlabel('Time (ns)', color='#cccccc', fontsize=11)
    ax.set_ylabel('Voltage (V)', color='#cccccc', fontsize=11)
    ax.set_title(title, color='#ffffff', fontsize=13, pad=12)
    ax.tick_params(colors='#aaaaaa')
    for spine in ax.spines.values():
        spine.set_edgecolor('#333333')
    ax.legend(fontsize=8, facecolor='#1a1a1a', edgecolor='#444',
              labelcolor='#cccccc', loc='upper right')

    plt.tight_layout()
    plt.savefig(outfile, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {outfile}")


# =============================================================================
# 7. Plot: transition waveform (zoomed)
# =============================================================================

def plot_transitions(time, voltage, ui, n_bits=6, title='Transitions',
                     outfile='transitions.png', vdd=3.3):
    """
    Plot a short window of the waveform showing individual transitions.
    Window starts after the first 20 UIs (settled region).
    """
    t_start = time[0] + 20 * ui
    t_end   = t_start + n_bits * ui
    mask    = (time >= t_start) & (time <= t_end)

    t_plot = time[mask] * 1e9   # ns
    v_plot = voltage[mask]

    fig, ax = plt.subplots(figsize=(12, 5), facecolor='#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    ax.plot(t_plot, v_plot, color='#00e5ff', lw=1.2)

    ax.axhline(0.8 * vdd, color='#ff6b6b', lw=0.7, ls='--', alpha=0.7,
               label=f'80% = {0.8*vdd:.2f}V')
    ax.axhline(0.2 * vdd, color='#ff6b6b', lw=0.7, ls='--', alpha=0.7,
               label=f'20% = {0.2*vdd:.2f}V')
    ax.axhline(vdd,       color='#888888', lw=0.5, ls=':', alpha=0.5)
    ax.axhline(0,         color='#888888', lw=0.5, ls=':', alpha=0.5)

    # UI tick marks
    for k in range(n_bits + 1):
        tc = (t_start + k * ui) * 1e9
        ax.axvline(tc, color='#333333', lw=0.5)

    ax.set_xlabel('Time (ns)', color='#cccccc', fontsize=11)
    ax.set_ylabel('Voltage (V)', color='#cccccc', fontsize=11)
    ax.set_title(title, color='#ffffff', fontsize=13, pad=12)
    ax.tick_params(colors='#aaaaaa')
    for spine in ax.spines.values():
        spine.set_edgecolor('#333333')
    ax.legend(fontsize=9, facecolor='#1a1a1a', edgecolor='#444',
              labelcolor='#cccccc')

    plt.tight_layout()
    plt.savefig(outfile, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {outfile}")


# =============================================================================
# 8. Extra plot modes via /eye/eye_tools (overlay and contour)
# =============================================================================

def _make_eye_generator(eye_slices):
    """
    Bridge build_eye() output → EyeDiagramGenerator.

    eye_slices  : (n_slices, n_interp*2) array from build_eye().
    After flattening, each window of length 2*n_interp corresponds to
    exactly one pre-aligned, interpolated UI slice.
    """
    n_interp = eye_slices.shape[1] // 2
    flat = eye_slices.flatten()
    return EyeDiagramGenerator(flat, samples_per_symbol=n_interp), n_interp


def plot_eye_overlay(eye_slices, title='Eye Diagram — Overlay',
                     outfile='eye_overlay.png'):
    """
    Overlay-style eye diagram (individual traces as lines).
    Requires /eye/eye_tools.py.  Each trace = one interpolated UI slice
    from the HSPICE simulation.
    """
    if not _EYE_TOOLS_OK:
        print("  WARNING: eye_tools not found — skipping overlay mode.")
        return
    gen, n_interp = _make_eye_generator(eye_slices)
    n_slices = eye_slices.shape[0]
    fig, ax = gen.plot_overlay(
        max_traces=min(n_slices, 500),
        color='#00e5ff', alpha=0.15,
        figsize=(10, 6)
    )
    ax.set_title(title, fontsize=13)
    ax.set_ylabel('Voltage (V)', fontsize=11)
    plt.tight_layout()
    fig.savefig(outfile, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {outfile}")


def plot_eye_contour(eye_slices, title='Eye Diagram — Contour',
                     outfile='eye_contour.png'):
    """
    Contour-density eye diagram.
    Requires /eye/eye_tools.py.
    """
    if not _EYE_TOOLS_OK:
        print("  WARNING: eye_tools not found — skipping contour mode.")
        return
    gen, _ = _make_eye_generator(eye_slices)
    fig, ax = gen.plot_contour(levels=20, cmap='plasma', figsize=(10, 6))
    ax.set_title(title, fontsize=13)
    ax.set_ylabel('Voltage (V)', fontsize=11)
    plt.tight_layout()
    fig.savefig(outfile, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {outfile}")


# =============================================================================
# 9. Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Eye diagram tool for IBIS comparison study '
                    '(Missouri S&T EMC Lab)')
    parser.add_argument('tr0file',
                        help='HSPICE ASCII .tr0 file (POST=2)')
    parser.add_argument('--signal', default='v(n10b)',
                        help='Signal name to analyse (default: v(n10b))')
    parser.add_argument('--ui', type=float, default=5e-9,
                        help='Unit interval in seconds (default: 5e-9)')
    parser.add_argument('--skip_ui', type=int, default=10,
                        help='UIs to skip at start for settling (default: 10)')
    parser.add_argument('--n_ui', type=int, default=3,
                        help='Number of unit intervals to display (default: 3)')
    parser.add_argument('--vdd', type=float, default=3.3,
                        help='Supply voltage (default: 3.3)')
    parser.add_argument('--fmt', default='hspice',
                        choices=['hspice'],
                        help='Simulator output format (default: hspice)')
    parser.add_argument('--mode', default='heatmap',
                        choices=['heatmap', 'overlay', 'contour', 'all'],
                        help='Eye diagram plot mode (default: heatmap). '
                             '"overlay" and "contour" require /eye/eye_tools.py. '
                             '"all" generates all three.')
    parser.add_argument('--outdir', default='.',
                        help='Output directory for PNG files (default: .)')
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    stem = Path(args.tr0file).stem
    sig_clean = args.signal.replace('(', '').replace(')', '').replace('/', '_')

    print(f"\n{'='*60}")
    print(f"  Eye Diagram Tool — Missouri S&T EMC Lab")
    print(f"{'='*60}")
    print(f"  File   : {args.tr0file}")
    print(f"  Signal : {args.signal}")
    print(f"  UI     : {args.ui*1e9:.2f} ns")
    print(f"  Vdd    : {args.vdd} V")
    print()

    # --- Load ---
    print("  Loading waveform...")
    data = load_waveform(args.tr0file, fmt=args.fmt)

    sig_key = args.signal.lower()
    if sig_key not in data:
        available = [k for k in data if k != 'time']
        print(f"  ERROR: Signal '{args.signal}' not found.")
        print(f"  Available signals: {available}")
        sys.exit(1)

    time    = data['time']
    voltage = data[sig_key]
    print(f"  Time range : {time[0]*1e9:.1f} ns → {time[-1]*1e9:.1f} ns")
    print(f"  Samples    : {len(time)}")
    print(f"  V range    : {voltage.min():.3f} V → {voltage.max():.3f} V")

    # --- Transition metrics ---
    print("\n  Computing transition metrics...")
    tm = measure_transitions(time, voltage, vdd=args.vdd)
    print(f"  Rise time (20-80%)  : {tm['rise_time']*1e12:.1f} ps")
    print(f"  Fall time (20-80%)  : {tm['fall_time']*1e12:.1f} ps")
    print(f"  Overshoot           : {tm['overshoot_abs']*1000:.1f} mV "
          f"({tm['overshoot_pct']:.1f}%)")
    print(f"  Undershoot          : {tm['undershoot_abs']*1000:.1f} mV "
          f"({tm['undershoot_pct']:.1f}%)")

    # --- Eye diagram ---
    print("\n  Building eye diagram...")
    t_eye, eye_slices = build_eye(
        time, voltage, args.ui,
        skip_ui=args.skip_ui, n_ui=args.n_ui
    )
    n_interp = eye_slices.shape[1] // args.n_ui
    print(f"  UI slices used : {eye_slices.shape[0]}  ({args.n_ui}-UI eye)")

    em = measure_eye(t_eye, eye_slices, vdd=args.vdd, n_ui=args.n_ui)
    print(f"  Eye height     : {em['eye_height']*1000:.1f} mV")
    print(f"  Eye width      : {em['eye_width']*1e12:.1f} ps")
    print(f"  V_eye_high     : {em['v_eye_high']:.3f} V")
    print(f"  V_eye_low      : {em['v_eye_low']*1000:.1f} mV")

    # Enhanced stats via /eye/ analyze_eye_opening (if available)
    if _EYE_TOOLS_OK:
        flat = eye_slices.flatten()
        es = _eye_analyze(flat, samples_per_symbol=n_interp)
        print(f"  Eye height(min): {es['eye_height_min']*1000:.1f} mV")
        print(f"  V_high  mean±σ : {es['high_level_mean']:.3f} V "
              f"± {es['high_level_std']*1000:.1f} mV")
        print(f"  V_low   mean±σ : {es['low_level_mean']*1000:.1f} mV "
              f"± {es['low_level_std']*1000:.1f} mV")

    # --- Plots ---
    print("\n  Generating plots...")
    modes = (['heatmap', 'overlay', 'contour']
             if args.mode == 'all' else [args.mode])

    eye_title = f"Eye Diagram — {stem} — {args.signal}"
    if 'heatmap' in modes:
        plot_eye(t_eye, eye_slices, em, args.ui,
                 title=eye_title,
                 outfile=str(outdir / f"{stem}_{sig_clean}_eye.png"),
                 vdd=args.vdd, n_ui=args.n_ui)

    if 'overlay' in modes:
        plot_eye_overlay(
            eye_slices,
            title=f"{eye_title} (Overlay)",
            outfile=str(outdir / f"{stem}_{sig_clean}_overlay.png"),
        )

    if 'contour' in modes:
        plot_eye_contour(
            eye_slices,
            title=f"{eye_title} (Contour)",
            outfile=str(outdir / f"{stem}_{sig_clean}_contour.png"),
        )

    trans_title = f"Transitions — {stem} — {args.signal}"
    plot_transitions(time, voltage, args.ui,
                     title=trans_title,
                     outfile=str(outdir / f"{stem}_{sig_clean}_trans.png"),
                     vdd=args.vdd)

    print(f"\n  Done.\n")

    print(f"\n  Done.\n")


if __name__ == '__main__':
    main()