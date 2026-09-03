"""Simulator-agnostic transient waveform plotting utility.

This is the shared plotting tool for future IBIS comparison experiments.  It
loads HSPICE ASCII .tr0, ngspice binary .raw, and Xyce CSV/PRN outputs through
the parser layer in eye_diagram.py, then generates single-trace plots, overlays,
zoom-window plots, and optional difference metrics.

Examples
--------
List signals:

    python scripts/transient_plot.py --list-signals hspice/native_ibis_exp1/tb_exp1.tr0

Single transient:

    python scripts/transient_plot.py \
      --trace "ngspice_pybis/tb_pybis_prbs7_new50ohm.raw|v(n10b)|ngspice pybis" \
      --window 0ns 120ns --out results/example_single.png

Overlay with zooms and delta panels:

    python scripts/transient_plot.py \
      --trace "ngspice_pybis/tb_pybis_prbs7_new50ohm.raw|v(n10b)|ngspice pybis" \
      --trace "xyce_refspice/tb_refspice_prbs7_new50ohm_xyce.cir.csv|v(n10b)|Xyce refspice" \
      --include-full --window 50ns 62ns --diff-to 0 \
      --out results/example_overlay.png --metrics-out results/example_overlay_metrics.csv

Trace syntax is:

    path|signal|label|fmt

Only path is mandatory if --signal supplies a default signal.  The fmt field is
optional and can be auto, hspice, ngspice, or xyce.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from eye_diagram import (
    infer_waveform_format,
    load_waveform,
    resolve_signal_key,
    sanitize_waveform,
)


TIME_UNITS = {
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
    "ps": 1e-12,
    "fs": 1e-15,
}

TIME_LABELS = {
    "s": "Time (s)",
    "ms": "Time (ms)",
    "us": "Time (us)",
    "ns": "Time (ns)",
    "ps": "Time (ps)",
    "fs": "Time (fs)",
}

STYLE_CYCLE = [
    "-",
    "--",
    "-.",
    ":",
]


@dataclass(frozen=True)
class TraceSpec:
    path: Path
    signal: str
    label: str
    fmt: str


@dataclass
class LoadedTrace:
    spec: TraceSpec
    resolved_signal: str
    time: np.ndarray
    voltage: np.ndarray


@dataclass(frozen=True)
class Window:
    start: float | None
    end: float | None
    label: str


def parse_time(value: str) -> float:
    """Parse a time string like 57ns, 2e-9, 0.2us into seconds."""
    text = value.strip().lower()
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)\s*([a-z]*)", text)
    if not match:
        raise argparse.ArgumentTypeError(f"Invalid time value: {value!r}")
    number = float(match.group(1))
    unit = match.group(2) or "s"
    if unit not in TIME_UNITS:
        raise argparse.ArgumentTypeError(
            f"Invalid time unit {unit!r}; use one of {', '.join(TIME_UNITS)}"
        )
    return number * TIME_UNITS[unit]


def format_time_for_name(value: float | None) -> str:
    if value is None:
        return "full"
    if value == 0:
        return "0s"
    abs_value = abs(value)
    for unit in ["s", "ms", "us", "ns", "ps", "fs"]:
        scaled = value / TIME_UNITS[unit]
        if 1 <= abs_value / TIME_UNITS[unit] < 1000:
            return f"{scaled:g}{unit}".replace(".", "p").replace("-", "m")
    return f"{value:.3e}s".replace(".", "p").replace("-", "m")


def parse_trace_spec(text: str, default_signal: str | None, default_fmt: str) -> TraceSpec:
    parts = [part.strip() for part in text.split("|")]
    if len(parts) > 4:
        raise argparse.ArgumentTypeError(
            f"Trace spec has too many fields: {text!r}; expected path|signal|label|fmt"
        )
    parts += [""] * (4 - len(parts))
    path_text, signal, label, fmt = parts
    if not path_text:
        raise argparse.ArgumentTypeError("Trace spec is missing path")
    if not signal:
        if not default_signal:
            raise argparse.ArgumentTypeError(
                f"Trace spec {text!r} is missing signal and --signal was not supplied"
            )
        signal = default_signal
    path = Path(path_text)
    if not label:
        label = path.stem
    fmt = (fmt or default_fmt).lower()
    if fmt not in {"auto", "hspice", "ngspice", "xyce"}:
        raise argparse.ArgumentTypeError(
            f"Invalid trace format {fmt!r}; use auto, hspice, ngspice, or xyce"
        )
    return TraceSpec(path=path, signal=signal, label=label, fmt=fmt)


def resolve_path(path: Path, base_dir: Path) -> Path:
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def load_trace(spec: TraceSpec, base_dir: Path) -> LoadedTrace:
    path = resolve_path(spec.path, base_dir)
    if not path.exists():
        raise FileNotFoundError(path)
    data = load_waveform(path, fmt=spec.fmt)
    if "time" not in data:
        raise KeyError(f"No time vector found in {path}")
    resolved = resolve_signal_key(data, spec.signal)
    time, voltage = sanitize_waveform(data["time"], data[resolved])
    return LoadedTrace(
        spec=TraceSpec(path=path, signal=spec.signal, label=spec.label, fmt=spec.fmt),
        resolved_signal=resolved,
        time=time,
        voltage=voltage,
    )


def list_signals(path: Path, fmt: str, base_dir: Path) -> int:
    full_path = resolve_path(path, base_dir)
    data = load_waveform(full_path, fmt=fmt)
    print(f"{full_path}")
    print(f"format: {fmt if fmt != 'auto' else infer_waveform_format(full_path)}")
    print(f"signals: {len(data)}")
    for key in sorted(data.keys()):
        arr = np.asarray(data[key])
        print(f"  {key:<32s} samples={len(arr)}")
    return 0


def clip_window(time: np.ndarray, voltage: np.ndarray, window: Window) -> tuple[np.ndarray, np.ndarray]:
    start = time[0] if window.start is None else window.start
    end = time[-1] if window.end is None else window.end
    if end <= start:
        raise ValueError(f"Window end must be greater than start: {window}")
    mask = (time >= start) & (time <= end)
    if not np.any(mask):
        return np.asarray([], dtype=np.float64), np.asarray([], dtype=np.float64)
    return time[mask], voltage[mask]


def envelope_decimate(
    time: np.ndarray,
    voltage: np.ndarray,
    max_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Decimate while preserving local min/max excursions such as spikes."""
    n = len(time)
    if n <= max_points or max_points <= 0:
        return time, voltage
    n_bins = max(2, max_points // 2)
    edges = np.linspace(0, n, n_bins + 1, dtype=int)
    keep: list[int] = [0, n - 1]
    for start, end in zip(edges[:-1], edges[1:]):
        if end <= start:
            continue
        segment = voltage[start:end]
        if len(segment) == 0:
            continue
        keep.append(start + int(np.argmin(segment)))
        keep.append(start + int(np.argmax(segment)))
    keep_unique = np.array(sorted(set(keep)), dtype=int)
    return time[keep_unique], voltage[keep_unique]


def choose_time_unit(windows: list[Window], traces: list[LoadedTrace], requested: str) -> str:
    if requested != "auto":
        return requested
    spans = []
    for window in windows:
        for trace in traces:
            start = trace.time[0] if window.start is None else window.start
            end = trace.time[-1] if window.end is None else window.end
            if end > start:
                spans.append(end - start)
    span = max(spans) if spans else max(t.time[-1] - t.time[0] for t in traces)
    if span >= 1:
        return "s"
    if span >= 1e-3:
        return "ms"
    if span >= 1e-6:
        return "us"
    if span >= 1e-9:
        return "ns"
    if span >= 1e-12:
        return "ps"
    return "fs"


def make_windows(args: argparse.Namespace) -> list[Window]:
    windows: list[Window] = []
    if args.include_full:
        windows.append(Window(None, None, "full transient"))
    for idx, pair in enumerate(args.window or [], 1):
        start, end = pair
        label = f"{format_time_for_name(start)} to {format_time_for_name(end)}"
        windows.append(Window(start, end, label))
    if not windows:
        windows.append(Window(None, None, "full transient"))
    return windows


def parse_markers(items: Iterable[str] | None) -> list[tuple[float, str]]:
    markers: list[tuple[float, str]] = []
    for item in items or []:
        if ":" in item:
            time_text, label = item.split(":", 1)
        else:
            time_text, label = item, ""
        markers.append((parse_time(time_text), label.strip()))
    return markers


def common_grid_for_window(
    ref_time: np.ndarray,
    other_time: np.ndarray,
    window: Window,
    max_points: int,
) -> np.ndarray:
    start = max(ref_time[0], other_time[0])
    end = min(ref_time[-1], other_time[-1])
    if window.start is not None:
        start = max(start, window.start)
    if window.end is not None:
        end = min(end, window.end)
    if end <= start:
        return np.asarray([], dtype=np.float64)

    def median_dt(time: np.ndarray) -> float:
        clipped = time[(time >= start) & (time <= end)]
        if len(clipped) < 2:
            return math.nan
        return float(np.median(np.diff(clipped)))

    ref_dt = median_dt(ref_time)
    other_dt = median_dt(other_time)
    candidates = [x for x in [ref_dt, other_dt] if np.isfinite(x) and x > 0]
    if candidates:
        dt = max(min(candidates), (end - start) / max_points)
    else:
        dt = (end - start) / max_points
    count = int(math.floor((end - start) / dt)) + 1
    count = max(2, min(count, max_points))
    return np.linspace(start, end, count)


def finite_stats(time: np.ndarray, voltage: np.ndarray) -> dict[str, float]:
    if len(time) == 0:
        return {
            "samples": 0,
            "t_start_s": math.nan,
            "t_end_s": math.nan,
            "v_min": math.nan,
            "v_max": math.nan,
            "v_mean": math.nan,
        }
    return {
        "samples": len(time),
        "t_start_s": float(time[0]),
        "t_end_s": float(time[-1]),
        "v_min": float(np.min(voltage)),
        "v_max": float(np.max(voltage)),
        "v_mean": float(np.mean(voltage)),
    }


def metric_rows(
    traces: list[LoadedTrace],
    windows: list[Window],
    diff_to: int | None,
    max_points: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for w_idx, window in enumerate(windows):
        for t_idx, trace in enumerate(traces):
            t_clip, v_clip = clip_window(trace.time, trace.voltage, window)
            stats = finite_stats(t_clip, v_clip)
            row: dict[str, object] = {
                "window_index": w_idx,
                "window_label": window.label,
                "trace_index": t_idx,
                "label": trace.spec.label,
                "path": str(trace.spec.path),
                "requested_signal": trace.spec.signal,
                "resolved_signal": trace.resolved_signal,
                **stats,
            }
            if diff_to is not None and t_idx != diff_to:
                ref = traces[diff_to]
                grid = common_grid_for_window(ref.time, trace.time, window, max_points)
                if len(grid) >= 2:
                    ref_y = np.interp(grid, ref.time, ref.voltage)
                    y = np.interp(grid, trace.time, trace.voltage)
                    diff = y - ref_y
                    j = int(np.argmax(np.abs(diff)))
                    row.update(
                        {
                            "diff_ref_index": diff_to,
                            "diff_ref_label": ref.spec.label,
                            "diff_samples": len(grid),
                            "diff_rmse_v": float(np.sqrt(np.mean(diff * diff))),
                            "diff_maxabs_v": float(np.max(np.abs(diff))),
                            "diff_signed_at_maxabs_v": float(diff[j]),
                            "diff_maxabs_t_s": float(grid[j]),
                        }
                    )
            rows.append(row)
    return rows


def write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_transients(
    traces: list[LoadedTrace],
    windows: list[Window],
    out_path: Path,
    args: argparse.Namespace,
) -> None:
    if args.diff_to is not None and not (0 <= args.diff_to < len(traces)):
        raise ValueError(f"--diff-to index {args.diff_to} is out of range")

    time_unit = choose_time_unit(windows, traces, args.time_unit)
    time_scale = TIME_UNITS[time_unit]
    markers = parse_markers(args.marker)
    n_rows = len(windows) * (2 if args.diff_to is not None and len(traces) > 1 else 1)
    height = max(4.2, 3.2 * n_rows)
    fig, axes = plt.subplots(n_rows, 1, figsize=(args.width, height), squeeze=False)
    axes_flat = list(axes.ravel())
    axis_idx = 0

    for w_idx, window in enumerate(windows):
        ax = axes_flat[axis_idx]
        axis_idx += 1
        for t_idx, trace in enumerate(traces):
            t_clip, v_clip = clip_window(trace.time, trace.voltage, window)
            if len(t_clip) == 0:
                continue
            t_plot, v_plot = envelope_decimate(t_clip, v_clip, args.max_points)
            style = STYLE_CYCLE[t_idx % len(STYLE_CYCLE)]
            ax.plot(
                t_plot / time_scale,
                v_plot,
                linestyle=style,
                linewidth=args.linewidth,
                alpha=args.alpha,
                label=trace.spec.label,
            )
        for marker_t, marker_label in markers:
            if (window.start is None or marker_t >= window.start) and (
                window.end is None or marker_t <= window.end
            ):
                ax.axvline(marker_t / time_scale, color="0.25", linestyle=":", linewidth=0.9)
                if marker_label:
                    ax.text(
                        marker_t / time_scale,
                        0.98,
                        marker_label,
                        transform=ax.get_xaxis_transform(),
                        rotation=90,
                        va="top",
                        ha="right",
                        fontsize=8,
                    )
        if args.ylim:
            ax.set_ylim(args.ylim[0], args.ylim[1])
        ax.set_ylabel(args.ylabel)
        ax.grid(True, alpha=0.25)
        title = args.title if w_idx == 0 and args.title else window.label
        if args.title and len(windows) > 1:
            title = f"{args.title} - {window.label}"
        ax.set_title(title)
        ax.legend(loc="best", fontsize=8)

        if args.diff_to is not None and len(traces) > 1:
            diff_ax = axes_flat[axis_idx]
            axis_idx += 1
            ref = traces[args.diff_to]
            for t_idx, trace in enumerate(traces):
                if t_idx == args.diff_to:
                    continue
                grid = common_grid_for_window(ref.time, trace.time, window, args.max_points)
                if len(grid) < 2:
                    continue
                ref_y = np.interp(grid, ref.time, ref.voltage)
                y = np.interp(grid, trace.time, trace.voltage)
                diff_mv = (y - ref_y) * 1e3
                t_plot, diff_plot = envelope_decimate(grid, diff_mv, args.max_points)
                style = STYLE_CYCLE[t_idx % len(STYLE_CYCLE)]
                diff_ax.plot(
                    t_plot / time_scale,
                    diff_plot,
                    linestyle=style,
                    linewidth=args.linewidth,
                    alpha=args.alpha,
                    label=f"{trace.spec.label} - {ref.spec.label}",
                )
            diff_ax.axhline(0, color="0.25", linewidth=0.8)
            diff_ax.set_ylabel("Delta (mV)")
            diff_ax.grid(True, alpha=0.25)
            diff_ax.legend(loc="best", fontsize=8)

    for ax in axes_flat:
        ax.set_xlabel(TIME_LABELS[time_unit])

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=args.dpi)
    plt.close(fig)


def print_summary(traces: list[LoadedTrace], rows: list[dict[str, object]]) -> None:
    print("Loaded traces:")
    for idx, trace in enumerate(traces):
        print(
            f"  [{idx}] {trace.spec.label}: {trace.resolved_signal} from "
            f"{trace.spec.path} ({len(trace.time)} samples, "
            f"{trace.time[0]:.6e}s to {trace.time[-1]:.6e}s)"
        )
    print("Metrics:")
    for row in rows:
        base = (
            f"  window={row['window_label']} trace={row['label']} "
            f"vmin={float(row['v_min']):.6g} vmax={float(row['v_max']):.6g}"
        )
        if "diff_rmse_v" in row:
            base += (
                f" rmse_vs_ref={float(row['diff_rmse_v']) * 1e3:.3f}mV"
                f" maxabs_vs_ref={float(row['diff_maxabs_v']) * 1e3:.3f}mV"
            )
        print(base)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot transient waveforms from HSPICE, ngspice, and Xyce outputs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--trace",
        action="append",
        default=[],
        help="Trace spec: path|signal|label|fmt. Repeat for overlays.",
    )
    parser.add_argument("--signal", help="Default signal for trace specs that omit it.")
    parser.add_argument(
        "--fmt",
        default="auto",
        choices=["auto", "hspice", "ngspice", "xyce"],
        help="Default input format for trace specs that omit it.",
    )
    parser.add_argument(
        "--list-signals",
        metavar="FILE",
        help="List signals in FILE and exit.",
    )
    parser.add_argument(
        "--window",
        nargs=2,
        action="append",
        type=parse_time,
        metavar=("START", "END"),
        help="Plot a time window. Repeat for multiple zoom panels. Units: s, ms, us, ns, ps, fs.",
    )
    parser.add_argument(
        "--include-full",
        action="store_true",
        help="Include a full-transient panel before requested zoom windows.",
    )
    parser.add_argument("--out", type=Path, default=Path("transient_plot.png"), help="Output PNG path.")
    parser.add_argument("--metrics-out", type=Path, help="Optional CSV metrics path.")
    parser.add_argument(
        "--diff-to",
        type=int,
        help="Trace index to use as reference for delta panels and difference metrics.",
    )
    parser.add_argument(
        "--marker",
        action="append",
        help="Vertical marker as time or time:label, e.g. 56.7ns:spike. Repeatable.",
    )
    parser.add_argument(
        "--time-unit",
        default="ns",
        choices=["auto", "s", "ms", "us", "ns", "ps", "fs"],
        help="Time unit for the x axis.",
    )
    parser.add_argument("--title", help="Plot title.")
    parser.add_argument("--ylabel", default="Voltage (V)", help="Y-axis label for waveform panels.")
    parser.add_argument("--ylim", nargs=2, type=float, metavar=("YMIN", "YMAX"), help="Y-axis limits.")
    parser.add_argument("--width", type=float, default=12.0, help="Figure width in inches.")
    parser.add_argument("--dpi", type=int, default=180, help="Output image DPI.")
    parser.add_argument("--linewidth", type=float, default=1.35, help="Trace linewidth.")
    parser.add_argument("--alpha", type=float, default=0.92, help="Trace alpha.")
    parser.add_argument(
        "--max-points",
        type=int,
        default=6000,
        help="Maximum plotted/interpolated points per trace per panel.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress console summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    base_dir = Path.cwd()

    if args.list_signals:
        return list_signals(Path(args.list_signals), args.fmt, base_dir)

    if not args.trace:
        parser.error("At least one --trace is required unless --list-signals is used.")

    specs = [parse_trace_spec(text, args.signal, args.fmt) for text in args.trace]
    traces = [load_trace(spec, base_dir) for spec in specs]
    windows = make_windows(args)
    rows = metric_rows(traces, windows, args.diff_to, args.max_points)
    plot_transients(traces, windows, args.out, args)
    if args.metrics_out:
        write_metrics(args.metrics_out, rows)
    if not args.quiet:
        print_summary(traces, rows)
        print(f"Wrote plot: {args.out}")
        if args.metrics_out:
            print(f"Wrote metrics: {args.metrics_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
