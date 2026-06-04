"""
eye_diagram.py — IBIS Comparison Study
Missouri S&T EMC Lab — Signal Integrity Group — April 2026

Parses HSPICE ASCII .tr0 files (POST=2) and produces:
  - Eye diagram plot (PNG)
  - Transition waveform plot (PNG)
  - Printed metrics: eye height, eye width, rise time, fall time,
    overshoot, undershoot

Usage:
    python scripts/eye_diagram.py tb_exp1.tr0 --signal v(n10b) --ui 5e-9
    python scripts/eye_diagram.py tb_exp1.tr0 --signal v(n10b) --ui 5e-9 --skip_ui 10

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
import csv
import struct
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional: import /eye/eye_tools for extra plot modes + richer metrics
# ---------------------------------------------------------------------------
_EYE_TOOLS_DIRS = [
    Path(__file__).resolve().parent / 'eye',
    Path(__file__).resolve().parent.parent / 'eye',
]
for _EYE_TOOLS_DIR in _EYE_TOOLS_DIRS:
    if _EYE_TOOLS_DIR.is_dir() and str(_EYE_TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(_EYE_TOOLS_DIR))
        break

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


def _unique_names(names):
    """Return lowercase column names, suffixing duplicates deterministically."""
    seen = {}
    out = []
    for idx, name in enumerate(names):
        key = (name or f"col{idx}").strip().lower()
        if not key:
            key = f"col{idx}"
        n = seen.get(key, 0)
        seen[key] = n + 1
        out.append(key if n == 0 else f"{key}_{n}")
    return out


def parse_ngspice_raw(filepath):
    """
    Parse an NGspice .raw file.

    Returns
    -------
    dict  {signal_name: np.ndarray}  — all signals including 'time'
    """
    filepath = Path(filepath)
    data = filepath.read_bytes()

    marker = b"Binary:"
    idx = data.find(marker)
    if idx < 0:
        return parse_ngspice_ascii_raw(filepath)

    header = data[:idx].decode('latin1')
    lines = header.splitlines()

    nvars = None
    npts = None
    variables = []
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

    if nvars is None or npts is None or len(variables) != nvars:
        raise ValueError("Could not parse ngspice raw header")

    payload_start = data.find(b"\n", idx)
    if payload_start < 0:
        raise ValueError("Could not locate ngspice binary payload")
    payload = data[payload_start + 1:]
    if npts == 0:
        npts = len(payload) // (8 * nvars)

    expected = 8 * nvars * npts
    if len(payload) < expected:
        raise ValueError(
            f"ngspice raw payload is shorter than expected: "
            f"{len(payload)} bytes < {expected} bytes"
        )

    values = struct.unpack("<" + "d" * (nvars * npts), payload[:expected])
    arr = np.asarray(values, dtype=np.float64).reshape((npts, nvars))

    result = {}
    for i, name in enumerate(variables):
        result[name] = arr[:, i]
    return result


def parse_ngspice_ascii_raw(filepath):
    """
    Parse an NGspice ASCII .raw file.

    Some Windows ngspice.exe batch runs emit a `Values:` raw file rather than
    the `Binary:` format used by the older local workflow.
    """
    filepath = Path(filepath)
    lines = filepath.read_text(encoding='latin1', errors='replace').splitlines()

    nvars = None
    npts = None
    variables = []
    values_idx = None
    reading_vars = False

    for idx, line in enumerate(lines):
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":", 1)[1])
        elif line.strip() == "Variables:":
            reading_vars = True
        elif line.strip() == "Values:":
            values_idx = idx + 1
            reading_vars = False
            break
        elif reading_vars and line.startswith("\t"):
            parts = line.split()
            if len(parts) >= 2:
                variables.append(parts[1])

    if nvars is None or values_idx is None or len(variables) != nvars:
        raise ValueError("Could not parse ngspice ASCII raw header")

    rows = []
    idx = values_idx
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if not line:
            continue

        parts = line.split()
        values = []
        start = 0
        if len(parts) >= 2:
            try:
                int(parts[0])
                start = 1
            except ValueError:
                start = 0
        values.extend(float(token) for token in parts[start:])

        while len(values) < nvars and idx < len(lines):
            cont = lines[idx].strip()
            idx += 1
            if cont:
                values.extend(float(token) for token in cont.split())

        if len(values) >= nvars:
            rows.append(values[:nvars])
        if npts is not None and len(rows) >= npts:
            break

    if not rows:
        raise ValueError("No numeric rows found in ngspice ASCII raw file")

    arr = np.asarray(rows, dtype=np.float64)
    result = {}
    for i, name in enumerate(variables):
        result[name] = arr[:, i]
    return result


def parse_xyce_csv(filepath):
    """
    Parse Xyce CSV/PRN output. Handles the CSV produced by:
        .print tran format=csv time V(...)

    Xyce CSV commonly repeats TIME when `time` is explicitly printed; the first
    TIME column is kept as 'time' and later duplicates are suffixed.
    """
    filepath = Path(filepath)
    with filepath.open('r', encoding='utf-8', errors='replace', newline='') as f:
        lines = [line for line in f if line.strip()]

    if not lines:
        raise ValueError(f"No rows found in Xyce output: {filepath}")

    comma_mode = ',' in lines[0]
    if comma_mode:
        reader = csv.reader(lines)
        header = next(reader)
        rows = []
        for row in reader:
            if len(row) != len(header):
                continue
            try:
                rows.append([float(x) for x in row])
            except ValueError:
                continue
    else:
        header = lines[0].split()
        rows = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) != len(header):
                continue
            try:
                rows.append([float(x) for x in parts])
            except ValueError:
                continue

    if not rows:
        raise ValueError(f"No numeric rows found in Xyce output: {filepath}")

    arr = np.asarray(rows, dtype=np.float64)
    names = _unique_names(header)
    result = {name: arr[:, i] for i, name in enumerate(names)}
    if 'time' not in result:
        result['time'] = arr[:, 0]
    return result


def infer_waveform_format(filepath):
    suffix = Path(filepath).suffix.lower()
    if suffix == '.tr0':
        return 'hspice'
    if suffix == '.raw':
        return 'ngspice'
    if suffix in ('.csv', '.prn'):
        return 'xyce'
    return 'hspice'


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
               'ngspice'  — NGspice binary .raw
               'xyce'     — (future) Xyce .prn CSV

    Returns
    -------
    dict  {signal_name_lower: np.ndarray}
    """
    fmt = fmt.lower()
    if fmt == 'auto':
        fmt = infer_waveform_format(filepath)
    if fmt == 'hspice':
        data = parse_hspice_tr0(filepath)
    elif fmt == 'ngspice':
        data = parse_ngspice_raw(filepath)
    elif fmt == 'xyce':
        data = parse_xyce_csv(filepath)
    else:
        raise NotImplementedError(f"Format '{fmt}' not yet implemented. "
                                  "Add a parser and wire it in here.")
    # Normalise keys to lower-case
    return {k.lower(): v for k, v in data.items()}


# =============================================================================
# 3. Eye diagram builder
# =============================================================================

def sanitize_waveform(time, voltage):
    """Sort a waveform and remove duplicate time samples for interpolation."""
    time = np.asarray(time, dtype=np.float64).ravel()
    voltage = np.asarray(voltage, dtype=np.float64).ravel()
    if time.shape != voltage.shape:
        raise ValueError("time and voltage arrays must have the same length")

    mask = np.isfinite(time) & np.isfinite(voltage)
    time = time[mask]
    voltage = voltage[mask]
    if len(time) < 2:
        raise ValueError("Need at least two finite waveform samples")

    order = np.argsort(time, kind='stable')
    time = time[order]
    voltage = voltage[order]

    unique_time, first_idx, counts = np.unique(
        time, return_index=True, return_counts=True
    )
    last_idx = first_idx + counts - 1
    return unique_time, voltage[last_idx]


def estimate_signal_levels(voltage):
    """Estimate low/high logic levels from waveform percentiles."""
    v = np.asarray(voltage, dtype=np.float64)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        raise ValueError("Cannot estimate signal levels from empty waveform")

    v_low = float(np.percentile(v, 1))
    v_high = float(np.percentile(v, 99))
    if v_high <= v_low:
        v_low = float(np.min(v))
        v_high = float(np.max(v))
    swing = v_high - v_low
    if swing <= 0:
        swing = max(abs(v_high), 1.0)
    return {
        'v_low': v_low,
        'v_high': v_high,
        'v_mid': v_low + 0.5 * swing,
        'v20': v_low + 0.2 * swing,
        'v80': v_low + 0.8 * swing,
        'swing': swing,
    }


def estimate_eye_phase(time, voltage, ui, levels=None, skip_ui=5):
    """Estimate one common fold phase in UI units from threshold crossings."""
    time, voltage = sanitize_waveform(time, voltage)
    levels = levels or estimate_signal_levels(voltage)
    threshold = levels['v_mid']
    start = time[0] + skip_ui * ui
    mask = time >= start
    t = time[mask]
    v = voltage[mask]
    if len(t) < 2:
        return 0.0

    above = v >= threshold
    idx = np.where(above[:-1] != above[1:])[0]
    phases = []
    for i in idx:
        t0, t1 = t[i], t[i + 1]
        v0, v1 = v[i], v[i + 1]
        if v1 == v0:
            continue
        tc = t0 + (threshold - v0) * (t1 - t0) / (v1 - v0)
        phases.append(((tc - time[0]) / ui) % 1.0)

    if not phases:
        return 0.0
    phases = np.asarray(phases, dtype=np.float64)
    angles = 2.0 * np.pi * phases
    phase = np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
    phase = (phase / (2.0 * np.pi)) % 1.0
    return float(phase)


def resolve_signal_key(data, requested):
    """Resolve v(node), node, and case differences to a data dictionary key."""
    key = requested.lower()
    if key in data:
        return key
    if not key.startswith('v('):
        vkey = f'v({key})'
        if vkey in data:
            return vkey
    if key.startswith('v(') and key.endswith(')'):
        node = key[2:-1]
        if node in data:
            return node
    raise KeyError(requested)


def build_eye(time, voltage, ui, skip_ui=5, n_interp=2000, n_ui=3, phase_ui=0.0):
    """
    Fold a waveform into a clock-referenced eye diagram.

    This preserves the transient waveform's timing. All slices are taken on a
    single UI-spaced time grid; rising and falling edges are not independently
    shifted or aligned.

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
    eye_slices : 2-D array (n_slices, n_interp*n_ui) — each row is one
                 interpolated n_ui-long waveform window
    """
    time, voltage = sanitize_waveform(time, voltage)

    t_start = time[0] + (skip_ui + phase_ui) * ui
    t_end   = time[-1]

    # Common time grid for n_ui UIs (interpolated)
    t_win = np.linspace(0, n_ui * ui, n_interp * n_ui, endpoint=False)

    slices = []
    t = t_start
    while t + n_ui * ui <= t_end:
        # Extract n_ui worth of data
        mask = (time >= t) & (time < t + n_ui * ui)
        if mask.sum() < 2:
            t += ui
            continue
        t_seg = time[mask] - t          # normalise to 0
        v_seg = voltage[mask]
        # Interpolate onto uniform grid
        v_interp = np.interp(t_win, t_seg, v_seg)
        slices.append(v_interp)
        t += ui

    if len(slices) == 0:
        raise ValueError("No complete UI slices found. "
                         "Check ui value and skip_ui.")

    eye_slices = np.array(slices)
    t_eye = np.linspace(0, n_ui * ui, n_interp * n_ui, endpoint=False)

    return t_eye, eye_slices

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

# Override the original width calculation above. The first implementation used
# an "all-high or all-low" test, which can report zero width for a visibly open
# PRBS eye. This version measures the gap between high/low clusters at each
# folded time column and tracks the open span around a UI centre.
def measure_eye(t_eye, eye_slices, vdd=3.3, threshold_pct=0.20,
                n_ui=3, levels=None):
    levels = levels or estimate_signal_levels(eye_slices)
    v_mid = levels['v_mid']
    min_gap = threshold_pct * levels['swing']

    n_cols = eye_slices.shape[1]
    samples_per_ui = n_cols // n_ui
    measure_ui = min(n_ui - 1, n_ui // 2)
    centre_col = int((measure_ui + 0.5) * samples_per_ui)
    half = max(1, samples_per_ui // 10)
    lo_col = max(0, centre_col - half)
    hi_col = min(n_cols, centre_col + half)
    centre_vals = eye_slices[:, lo_col:hi_col].reshape(-1)

    high_vals = centre_vals[centre_vals >= v_mid]
    low_vals = centre_vals[centre_vals < v_mid]
    if len(high_vals) and len(low_vals):
        v_eye_high = float(np.percentile(high_vals, 5))
        v_eye_low = float(np.percentile(low_vals, 95))
    else:
        v_eye_high = float(np.percentile(centre_vals, 95))
        v_eye_low = float(np.percentile(centre_vals, 5))
    eye_height = v_eye_high - v_eye_low

    scan_start = measure_ui * samples_per_ui
    scan_end = min(n_cols, (measure_ui + 1) * samples_per_ui)
    gap = np.full(scan_end - scan_start, np.nan)
    for out_i, col_i in enumerate(range(scan_start, scan_end)):
        vals = eye_slices[:, col_i]
        hi = vals[vals >= v_mid]
        lo = vals[vals < v_mid]
        if len(hi) and len(lo):
            gap[out_i] = np.percentile(hi, 5) - np.percentile(lo, 95)

    open_cols = np.isfinite(gap) & (gap > min_gap)
    local_centre = max(0, min(len(open_cols) - 1, centre_col - scan_start))
    left = local_centre
    while left > 0 and open_cols[left - 1]:
        left -= 1
    right = local_centre
    while right + 1 < len(open_cols) and open_cols[right + 1]:
        right += 1

    dt = t_eye[1] - t_eye[0] if len(t_eye) > 1 else 0.0
    eye_width = float((right - left + 1) * dt) if open_cols[local_centre] else 0.0

    return {
        'eye_height': float(eye_height),
        'eye_width': float(eye_width),
        'v_eye_high': float(v_eye_high),
        'v_eye_low': float(v_eye_low),
        'v_mid': float(v_mid),
    }

def measure_transitions(time, voltage, vdd=3.3, n_transitions=20, levels=None):
    """
    Measure rise time, fall time, overshoot, undershoot.

    Uses the first n_transitions detected edges.

    Returns dict with keys:
        rise_time, fall_time, overshoot_abs, undershoot_abs,
        overshoot_pct, undershoot_pct
    """
    time, voltage = sanitize_waveform(time, voltage)
    levels = levels or {
        'v_low': 0.0,
        'v_high': vdd,
        'v20': 0.20 * vdd,
        'v80': 0.80 * vdd,
        'swing': vdd,
    }
    v_lo = levels['v20']
    v_hi = levels['v80']

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
    overshoot_abs  = max(0.0, float(np.max(voltage)) - levels['v_high'])
    undershoot_abs = max(0.0, levels['v_low'] - float(np.min(voltage)))
    swing = max(levels.get('swing', vdd), 1e-30)

    return {
        'rise_time':      float(np.median(rise_times))  if rise_times  else float('nan'),
        'fall_time':      float(np.median(fall_times))  if fall_times  else float('nan'),
        'overshoot_abs':  overshoot_abs,
        'undershoot_abs': undershoot_abs,
        'overshoot_pct':  100.0 * overshoot_abs  / swing,
        'undershoot_pct': 100.0 * undershoot_abs / swing,
    }


# =============================================================================
# 6. Plot: eye diagram
# =============================================================================

def plot_eye(t_eye, eye_slices, metrics, ui, title='Eye Diagram',
             outfile='eye.png', vdd=3.3, n_ui=3, levels=None,
             x_offset=0.0):
    """
    Render eye diagram as a heatmap density plot with metrics annotation.
    """
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    t_ns = (t_eye - x_offset) * 1e9  # convert to ns for display
    levels = levels or estimate_signal_levels(eye_slices)
    y_pad = max(0.10, 0.25 * levels['swing'])
    y_min = levels['v_low'] - y_pad
    y_max = levels['v_high'] + y_pad

    # Density heatmap
    # Build 2-D histogram
    n_tbins = 300
    n_vbins = 300
    t_flat = np.tile(t_ns, eye_slices.shape[0])
    v_flat = eye_slices.flatten()

    h, xedges, yedges = np.histogram2d(
        t_flat, v_flat,
        bins=[n_tbins, n_vbins],
        range=[[t_ns[0], t_ns[-1]], [y_min, y_max]]
    )

    # Log scale for density
    h_log = np.log1p(h.T)

    ax.imshow(h_log, origin='lower', aspect='auto',
              extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
              cmap='plasma', interpolation='bilinear')

    # UI boundary lines (one per UI boundary, excluding t=0)
    ui_ns = ui * 1e9
    for k in range(1, n_ui + 1):
        ax.axvline(ui_ns * k - x_offset * 1e9,
                   color='#00ff88', lw=0.8, ls='--', alpha=0.45)
    if x_offset:
        ax.axvline(0, color='#00ff88', lw=1.0, ls='-', alpha=0.8)

    # Threshold lines
    ax.axhline(levels['v20'], color='#ff6b6b', lw=0.7, ls=':', alpha=0.7,
               label=f"20% swing = {levels['v20']:.2f}V")
    ax.axhline(levels['v80'], color='#ff6b6b', lw=0.7, ls=':', alpha=0.7,
               label=f"80% swing = {levels['v80']:.2f}V")

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
                     outfile='transitions.png', vdd=3.3, levels=None):
    """
    Plot a short window of the waveform showing individual transitions.
    Window starts after the first 20 UIs (settled region).
    """
    t_start = time[0] + 20 * ui
    t_end   = t_start + n_bits * ui
    mask    = (time >= t_start) & (time <= t_end)

    t_plot = time[mask] * 1e9   # ns
    v_plot = voltage[mask]
    levels = levels or estimate_signal_levels(voltage)

    fig, ax = plt.subplots(figsize=(12, 5), facecolor='#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    ax.plot(t_plot, v_plot, color='#00e5ff', lw=1.2)

    ax.axhline(levels['v80'], color='#ff6b6b', lw=0.7, ls='--', alpha=0.7,
               label=f"80% = {levels['v80']:.2f}V")
    ax.axhline(levels['v20'], color='#ff6b6b', lw=0.7, ls='--', alpha=0.7,
               label=f"20% = {levels['v20']:.2f}V")
    ax.axhline(levels['v_high'], color='#888888', lw=0.5, ls=':', alpha=0.5)
    ax.axhline(levels['v_low'],  color='#888888', lw=0.5, ls=':', alpha=0.5)

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

def _make_eye_generator(eye_slices, n_ui=3):
    """
    Bridge build_eye() output → EyeDiagramGenerator.

    eye_slices  : (n_slices, n_interp*n_ui) array from build_eye().
    After flattening, each window of length n_ui*n_interp corresponds to
    exactly one pre-aligned, interpolated UI slice.
    """
    n_interp = eye_slices.shape[1] // n_ui
    flat = eye_slices.flatten()
    return EyeDiagramGenerator(flat, samples_per_symbol=n_interp), n_interp


def plot_eye_overlay(eye_slices, title='Eye Diagram - Overlay',
                     outfile='eye_overlay.png'):
    """
    Overlay-style eye diagram (individual traces as lines).
    Requires /eye/eye_tools.py.  Each trace = one interpolated UI slice
    from the HSPICE simulation.
    """
    if not _EYE_TOOLS_OK:
        print("  WARNING: eye_tools not found - skipping overlay mode.")
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


def plot_eye_contour(eye_slices, title='Eye Diagram - Contour',
                     outfile='eye_contour.png'):
    """
    Contour-density eye diagram.
    Requires /eye/eye_tools.py.
    """
    if not _EYE_TOOLS_OK:
        print("  WARNING: eye_tools not found - skipping contour mode.")
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

def plot_eye_overlay(t_eye, eye_slices, title='Eye Diagram Overlay',
                     outfile='eye_overlay.png', vdd=3.3, n_ui=3,
                     levels=None, max_traces=500, x_offset=0.0):
    """
    Native overlay-style eye diagram. This does not require /eye/eye_tools.py.
    """
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    levels = levels or estimate_signal_levels(eye_slices)
    t_ns = (t_eye - x_offset) * 1e9
    n_slices = eye_slices.shape[0]
    step = max(1, int(np.ceil(n_slices / max_traces)))
    plotted = eye_slices[::step]
    # Adaptive opacity keeps short stressed runs from looking washed out while
    # long PRBS runs still build a readable density.
    trace_alpha = min(0.55, max(0.28, 40.0 / max(1, len(plotted))))
    for row in plotted:
        ax.plot(t_ns, row, color='#00f5ff', lw=0.65, alpha=trace_alpha)

    ui_ns = (t_eye[-1] - t_eye[0]) * 1e9 / n_ui
    for k in range(1, n_ui + 1):
        ax.axvline(ui_ns * k - x_offset * 1e9,
                   color='#00ff88', lw=0.9, ls='--', alpha=0.55)
    if x_offset:
        ax.axvline(0, color='#00ff88', lw=1.0, ls='-', alpha=0.8)

    ax.axhline(levels['v20'], color='#ff6b6b', lw=0.9, ls=':', alpha=0.9,
               label=f"20% swing = {levels['v20']:.2f}V")
    ax.axhline(levels['v80'], color='#ff6b6b', lw=0.9, ls=':', alpha=0.9,
               label=f"80% swing = {levels['v80']:.2f}V")

    y_pad = max(0.10, 0.25 * levels['swing'])
    ax.set_ylim(levels['v_low'] - y_pad, levels['v_high'] + y_pad)
    ax.set_xlim(t_ns[0], t_ns[-1])
    xlabel = 'Time relative to decision (ns)' if x_offset else 'Time (ns)'
    ax.set_xlabel(xlabel, color='#cccccc', fontsize=11)
    ax.set_ylabel('Voltage (V)', color='#cccccc', fontsize=11)
    ax.set_title(title, color='#ffffff', fontsize=13, pad=12)
    ax.tick_params(colors='#aaaaaa')
    for spine in ax.spines.values():
        spine.set_edgecolor('#333333')
    ax.legend(fontsize=8, facecolor='#1a1a1a', edgecolor='#444',
              labelcolor='#cccccc', loc='upper right')

    plt.tight_layout()
    plt.savefig(outfile, dpi=180, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {outfile}")


def plot_eye_contour(t_eye, eye_slices, title='Eye Diagram Contour',
                     outfile='eye_contour.png', vdd=3.3, n_ui=3,
                     levels=None, contour_levels=20, x_offset=0.0):
    """
    Native contour-density eye diagram for already folded eye slices.
    """
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    levels = levels or estimate_signal_levels(eye_slices)
    t_ns = (t_eye - x_offset) * 1e9
    y_pad = max(0.10, 0.25 * levels['swing'])
    y_min = levels['v_low'] - y_pad
    y_max = levels['v_high'] + y_pad

    t_flat = np.tile(t_ns, eye_slices.shape[0])
    v_flat = eye_slices.flatten()
    h, xedges, yedges = np.histogram2d(
        t_flat, v_flat,
        bins=[240, 240],
        range=[[t_ns[0], t_ns[-1]], [y_min, y_max]],
    )
    x = (xedges[:-1] + xedges[1:]) / 2.0
    y = (yedges[:-1] + yedges[1:]) / 2.0
    X, Y = np.meshgrid(x, y)
    contour = ax.contourf(X, Y, np.log1p(h.T), levels=contour_levels,
                          cmap='plasma')
    plt.colorbar(contour, ax=ax, label='log density')

    ui_ns = (t_eye[-1] - t_eye[0]) * 1e9 / n_ui
    for k in range(1, n_ui + 1):
        ax.axvline(ui_ns * k - x_offset * 1e9,
                   color='#00ff88', lw=0.8, ls='--', alpha=0.35)
    if x_offset:
        ax.axvline(0, color='#00ff88', lw=1.0, ls='-', alpha=0.8)

    ax.axhline(levels['v20'], color='#ff6b6b', lw=0.7, ls=':', alpha=0.7)
    ax.axhline(levels['v80'], color='#ff6b6b', lw=0.7, ls=':', alpha=0.7)
    ax.set_xlim(t_ns[0], t_ns[-1])
    ax.set_ylim(y_min, y_max)
    xlabel = 'Time relative to decision (ns)' if x_offset else 'Time (ns)'
    ax.set_xlabel(xlabel, color='#cccccc', fontsize=11)
    ax.set_ylabel('Voltage (V)', color='#cccccc', fontsize=11)
    ax.set_title(title, color='#ffffff', fontsize=13, pad=12)
    ax.tick_params(colors='#aaaaaa')
    for spine in ax.spines.values():
        spine.set_edgecolor('#333333')

    plt.tight_layout()
    plt.savefig(outfile, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {outfile}")

def main():
    parser = argparse.ArgumentParser(
        description='Eye diagram tool for IBIS comparison study '
                    '(Missouri S&T EMC Lab)')
    parser.add_argument('tr0file',
                        help='Waveform file (.tr0, ngspice .raw, or Xyce .csv/.prn)')
    parser.add_argument('--signal', default='v(n10b)',
                        help='Signal name to analyse (default: v(n10b))')
    parser.add_argument('--ui', type=float, default=5e-9,
                        help='Unit interval in seconds (default: 5e-9)')
    parser.add_argument('--skip_ui', type=int, default=10,
                        help='UIs to skip at start for settling (default: 10)')
    parser.add_argument('--n_ui', type=int, default=3,
                        help='Number of unit intervals to display (default: 3)')
    parser.add_argument('--n_interp', type=int, default=2000,
                        help='Interpolated samples per UI (default: 2000)')
    parser.add_argument('--phase_ui', type=float, default=0.0,
                        help='Common clock-fold phase offset in UI units '
                             '(default: 0.0)')
    parser.add_argument('--auto_phase', action='store_true',
                        help='Estimate one common clock-fold phase from signal '
                             'threshold crossings')
    parser.add_argument('--auto_phase_target', default='decision',
                        choices=['decision', 'crossing'],
                        help='With --auto_phase, place the eye opening at the plot center '
                             "('decision') or align the plot start to crossings ('crossing').")
    parser.add_argument('--center_x', action='store_true',
                        help='Center the x-axis around the decision point')
    parser.add_argument('--levels', default='auto',
                        choices=['auto', 'vdd'],
                        help='Threshold levels: auto signal swing or 0..Vdd (default: auto)')
    parser.add_argument('--vdd', type=float, default=3.3,
                        help='Supply voltage (default: 3.3)')
    parser.add_argument('--fmt', default='auto',
                        choices=['auto', 'hspice', 'ngspice', 'xyce'],
                        help='Simulator output format (default: auto)')
    parser.add_argument('--mode', default='heatmap',
                        choices=['heatmap', 'overlay', 'contour', 'all'],
                        help='Eye diagram plot mode (default: heatmap). '
                             '"overlay" is built in; "contour" requires /eye/eye_tools.py. '
                             '"all" generates all three.')
    parser.add_argument('--max_traces', type=int, default=500,
                        help='Maximum overlay traces to draw (default: 500)')
    parser.add_argument('--outdir', default='.',
                        help='Output directory for PNG files (default: .)')
    parser.add_argument('--eye-out', default='',
                        help='Explicit output path for the selected eye PNG. '
                             'Use only with a single --mode, not --mode all.')
    parser.add_argument('--no-transitions', action='store_true',
                        help='Do not write the transition zoom PNG.')
    parser.add_argument('--no-metrics', action='store_true',
                        help='Do not write the metrics CSV.')
    args = parser.parse_args()
    if args.eye_out and args.mode == 'all':
        parser.error('--eye-out cannot be used with --mode all')

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    stem = Path(args.tr0file).stem
    sig_clean = args.signal.replace('(', '').replace(')', '').replace('/', '_')

    print(f"\n{'='*60}")
    print(f"  Eye Diagram Tool - Missouri S&T EMC Lab")
    print(f"{'='*60}")
    print(f"  File   : {args.tr0file}")
    print(f"  Signal : {args.signal}")
    print(f"  UI     : {args.ui*1e9:.2f} ns")
    print(f"  Vdd    : {args.vdd} V")
    print()

    # --- Load ---
    print("  Loading waveform...")
    data = load_waveform(args.tr0file, fmt=args.fmt)

    try:
        sig_key = resolve_signal_key(data, args.signal)
    except KeyError:
        available = [k for k in data if k != 'time']
        print(f"  ERROR: Signal '{args.signal}' not found.")
        print(f"  Available signals: {available}")
        sys.exit(1)

    time    = data['time']
    voltage = data[sig_key]
    time, voltage = sanitize_waveform(time, voltage)
    if args.levels == 'auto':
        levels = estimate_signal_levels(voltage)
    else:
        levels = {
            'v_low': 0.0,
            'v_high': args.vdd,
            'v_mid': 0.5 * args.vdd,
            'v20': 0.2 * args.vdd,
            'v80': 0.8 * args.vdd,
            'swing': args.vdd,
        }
    print(f"  Time range : {time[0]*1e9:.1f} ns to {time[-1]*1e9:.1f} ns")
    print(f"  Samples    : {len(time)}")
    print(f"  V range    : {voltage.min():.3f} V to {voltage.max():.3f} V")
    print(f"  Levels     : low={levels['v_low']:.3f} V, high={levels['v_high']:.3f} V")

    # --- Transition metrics ---
    print("\n  Computing transition metrics...")
    tm = measure_transitions(time, voltage, vdd=args.vdd, levels=levels)
    print(f"  Rise time (20-80%)  : {tm['rise_time']*1e12:.1f} ps")
    print(f"  Fall time (20-80%)  : {tm['fall_time']*1e12:.1f} ps")
    print(f"  Overshoot           : {tm['overshoot_abs']*1000:.1f} mV "
          f"({tm['overshoot_pct']:.1f}%)")
    print(f"  Undershoot          : {tm['undershoot_abs']*1000:.1f} mV "
          f"({tm['undershoot_pct']:.1f}%)")

    # --- Eye diagram ---
    print("\n  Building eye diagram...")
    phase_ui = args.phase_ui
    crossing_phase_ui = ''
    if args.auto_phase:
        crossing_phase = estimate_eye_phase(time, voltage, args.ui,
                                            levels=levels,
                                            skip_ui=args.skip_ui)
        crossing_phase_ui = crossing_phase
        if args.auto_phase_target == 'decision':
            phase_ui = (crossing_phase - 0.5) % 1.0
        else:
            phase_ui = crossing_phase
        print(f"  Crossing phase : {crossing_phase:.4f} UI")
        print(f"  Fold start     : {phase_ui:.4f} UI ({args.auto_phase_target})")
        t_eye, eye_slices = build_eye(
            time, voltage, args.ui,
            skip_ui=args.skip_ui, n_interp=args.n_interp, n_ui=args.n_ui,
            phase_ui=phase_ui
        )
    else:
        t_eye, eye_slices = build_eye(
            time, voltage, args.ui,
            skip_ui=args.skip_ui, n_interp=args.n_interp, n_ui=args.n_ui,
            phase_ui=phase_ui
        )
    print("  Fold method   : clock/UI grid (no per-edge alignment)")
    n_interp = eye_slices.shape[1] // args.n_ui
    print(f"  UI slices used : {eye_slices.shape[0]}  ({args.n_ui}-UI eye)")

    em = measure_eye(t_eye, eye_slices, vdd=args.vdd, n_ui=args.n_ui,
                     levels=levels)
    print(f"  Eye height     : {em['eye_height']*1000:.1f} mV")
    print(f"  Eye width      : {em['eye_width']*1e12:.1f} ps")
    print(f"  V_eye_high     : {em['v_eye_high']:.3f} V")
    print(f"  V_eye_low      : {em['v_eye_low']*1000:.1f} mV")

    # The optional /eye analyzer expects a continuous fixed-sample stream.
    # Simulator data is parsed, phase-aligned, and folded here, so use the
    # native metrics above to avoid re-windowing already folded slices.

    # --- Plots ---
    print("\n  Generating plots...")
    modes = (['heatmap', 'overlay', 'contour']
             if args.mode == 'all' else [args.mode])
    x_offset = 0.5 * args.n_ui * args.ui if args.center_x else 0.0

    eye_title = f"Eye Diagram - {stem} - {args.signal}"
    if 'heatmap' in modes:
        heatmap_out = (Path(args.eye_out) if args.eye_out
                       else outdir / f"{stem}_{sig_clean}_eye.png")
        plot_eye(t_eye, eye_slices, em, args.ui,
                 title=eye_title,
                 outfile=str(heatmap_out),
                 vdd=args.vdd, n_ui=args.n_ui, levels=levels,
                 x_offset=x_offset)

    if 'overlay' in modes:
        overlay_out = (Path(args.eye_out) if args.eye_out
                       else outdir / f"{stem}_{sig_clean}_overlay.png")
        plot_eye_overlay(
            t_eye,
            eye_slices,
            title=f"{eye_title} (Overlay)",
            outfile=str(overlay_out),
            vdd=args.vdd,
            n_ui=args.n_ui,
            levels=levels,
            max_traces=args.max_traces,
            x_offset=x_offset,
        )

    if 'contour' in modes:
        contour_out = (Path(args.eye_out) if args.eye_out
                       else outdir / f"{stem}_{sig_clean}_contour.png")
        plot_eye_contour(
            t_eye,
            eye_slices,
            title=f"{eye_title} (Contour)",
            outfile=str(contour_out),
            vdd=args.vdd,
            n_ui=args.n_ui,
            levels=levels,
            x_offset=x_offset,
        )

    if not args.no_transitions:
        trans_title = f"Transitions - {stem} - {args.signal}"
        plot_transitions(time, voltage, args.ui,
                         title=trans_title,
                         outfile=str(outdir / f"{stem}_{sig_clean}_trans.png"),
                         vdd=args.vdd, levels=levels)

    if not args.no_metrics:
        metrics_out = outdir / f"{stem}_{sig_clean}_metrics.csv"
        with metrics_out.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'file', 'format', 'signal', 'samples', 't_start_ns', 't_end_ns',
                'v_min', 'v_max', 'level_low', 'level_high',
                'fold_mode', 'crossing_phase_ui', 'phase_ui',
                'auto_phase_target', 'center_x',
                'skip_ui', 'n_ui', 'ui_s', 'eye_slices',
                'eye_height_mV', 'eye_width_ps', 'v_eye_high', 'v_eye_low',
                'rise_time_ps', 'fall_time_ps', 'overshoot_mV',
                'undershoot_mV', 'overshoot_pct', 'undershoot_pct',
            ])
            writer.writeheader()
            writer.writerow({
                'file': str(args.tr0file),
                'format': args.fmt,
                'signal': args.signal,
                'samples': len(time),
                't_start_ns': time[0] * 1e9,
                't_end_ns': time[-1] * 1e9,
                'v_min': float(voltage.min()),
                'v_max': float(voltage.max()),
                'level_low': levels['v_low'],
                'level_high': levels['v_high'],
                'fold_mode': 'clock',
                'crossing_phase_ui': crossing_phase_ui,
                'phase_ui': phase_ui,
                'auto_phase_target': args.auto_phase_target if args.auto_phase else '',
                'center_x': args.center_x,
                'skip_ui': args.skip_ui,
                'n_ui': args.n_ui,
                'ui_s': args.ui,
                'eye_slices': eye_slices.shape[0],
                'eye_height_mV': em['eye_height'] * 1e3,
                'eye_width_ps': em['eye_width'] * 1e12,
                'v_eye_high': em['v_eye_high'],
                'v_eye_low': em['v_eye_low'],
                'rise_time_ps': tm['rise_time'] * 1e12,
                'fall_time_ps': tm['fall_time'] * 1e12,
                'overshoot_mV': tm['overshoot_abs'] * 1e3,
                'undershoot_mV': tm['undershoot_abs'] * 1e3,
                'overshoot_pct': tm['overshoot_pct'],
                'undershoot_pct': tm['undershoot_pct'],
            })
        print(f"  Saved: {metrics_out}")

    print(f"\n  Done.\n")


if __name__ == '__main__':
    main()
