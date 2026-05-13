"""Generate Ku/Kd review plots for the normal and stressed pybis cases.

The accepted review RAW for ngspice pybis did not save the internal Ku/Kd
nodes, so this script reruns only the two ngspice pybis decks with those nodes
enabled.  Xyce already saved Ku/Kd/NX in the review CSVs.
"""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from eye_diagram import load_waveform, resolve_signal_key, sanitize_waveform


ROOT = Path(__file__).resolve().parent.parent
NGSPICE = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")
REVIEW_DIR = ROOT / "results" / "transient_review_plots_2026-05-13"
NORMAL_DIR = REVIEW_DIR / "normal_prbs_channel"
STRESSED_DIR = REVIEW_DIR / "stressed_edge50_prbs80_channel"


@dataclass(frozen=True)
class Flow:
    label: str
    path: Path
    fmt: str
    n10b_signal: str
    ku_signal: str
    kd_signal: str


@dataclass(frozen=True)
class CaseConfig:
    name: str
    title: str
    out_dir: Path
    full_window_ns: tuple[float, float]
    zoom_window_ns: tuple[float, float]
    marker_ns: float | None
    marker_label: str
    ngspice_source_deck: Path
    ngspice_review_deck: Path
    ngspice_review_raw: Path
    xyce_csv: Path
    include_replacements: dict[str, Path]


def posix(path: Path) -> str:
    return path.resolve().as_posix()


def replace_include(text: str, include_target: str, absolute_path: Path) -> str:
    pattern = re.compile(rf"(?im)^(\.include\s+)['\"]?{re.escape(include_target)}['\"]?\s*$")
    replacement = rf"\1'{posix(absolute_path)}'"
    text, count = pattern.subn(replacement, text)
    if count != 1:
        raise RuntimeError(f"Expected one include for {include_target!r}, replaced {count}")
    return text


def add_kukd_save(text: str) -> str:
    save_line = ".save V(in_dig) V(pad) V(tx_out) V(n10b) V(xdrv.ku) V(xdrv.kd) V(xdrv.nx)"
    text, count = re.subn(r"(?im)^\.save\s+.*$", save_line, text, count=1)
    if count != 1:
        raise RuntimeError("Expected one .save line")
    return text


def prepare_ngspice_deck(case: CaseConfig) -> None:
    text = case.ngspice_source_deck.read_text(encoding="utf-8")
    for include_target, absolute_path in case.include_replacements.items():
        text = replace_include(text, include_target, absolute_path)
    text = add_kukd_save(text)
    if case.name == "normal_prbs_channel":
        text, count = re.subn(r"(?im)^\.tran\s+10p\s+1000n\s*$", ".tran 10p 75n", text)
        if count != 1:
            raise RuntimeError("Expected one normal-case .tran line to shorten for Ku/Kd review")
    case.ngspice_review_deck.parent.mkdir(parents=True, exist_ok=True)
    case.ngspice_review_deck.write_text(text, encoding="ascii")


def ngspice_raw_has_kukd(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = load_waveform(path, fmt="ngspice")
        resolve_signal_key(data, "v(xdrv.ku)")
        resolve_signal_key(data, "v(xdrv.kd)")
        return True
    except Exception:
        return False


def run_ngspice_if_needed(case: CaseConfig) -> None:
    if ngspice_raw_has_kukd(case.ngspice_review_raw):
        return
    if not NGSPICE.exists():
        raise FileNotFoundError(NGSPICE)
    prepare_ngspice_deck(case)
    case.ngspice_review_raw.unlink(missing_ok=True)
    log_path = case.ngspice_review_raw.with_suffix(".log")
    try:
        proc = subprocess.run(
            [str(NGSPICE), "-b", "-r", case.ngspice_review_raw.name, case.ngspice_review_deck.name],
            cwd=case.ngspice_review_deck.parent,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(
            "COMMAND: "
            + " ".join(
                [str(NGSPICE), "-b", "-r", case.ngspice_review_raw.name, case.ngspice_review_deck.name]
            )
            + "\n\nRETURN_CODE: TIMEOUT\n\n"
            + f"STDOUT:\n{exc.stdout or ''}\n\nSTDERR:\n{exc.stderr or ''}",
            encoding="utf-8",
        )
        case.ngspice_review_raw.unlink(missing_ok=True)
        raise RuntimeError(f"ngspice timed out for {case.name}; see {log_path}") from exc
    log_path.write_text(
        "COMMAND: "
        + " ".join([str(NGSPICE), "-b", "-r", case.ngspice_review_raw.name, case.ngspice_review_deck.name])
        + "\n\n"
        + f"RETURN_CODE: {proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}",
        encoding="utf-8",
    )
    if proc.returncode != 0 or not case.ngspice_review_raw.exists():
        raise RuntimeError(f"ngspice failed for {case.name}; see {log_path}")


def load_flow(flow: Flow) -> dict[str, np.ndarray]:
    data = load_waveform(flow.path, fmt=flow.fmt)
    out: dict[str, np.ndarray] = {}
    time = data["time"]
    for name, requested in [
        ("n10b", flow.n10b_signal),
        ("ku", flow.ku_signal),
        ("kd", flow.kd_signal),
    ]:
        key = resolve_signal_key(data, requested)
        t, y = sanitize_waveform(time, data[key])
        if "time" not in out:
            out["time"] = t
        out[name] = y
    return out


def clip(t_ns: np.ndarray, y: np.ndarray, window: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    mask = (t_ns >= window[0]) & (t_ns <= window[1])
    return t_ns[mask], y[mask]


def envelope_decimate(t: np.ndarray, y: np.ndarray, max_points: int = 7000) -> tuple[np.ndarray, np.ndarray]:
    if len(t) <= max_points:
        return t, y
    bins = max(2, max_points // 2)
    edges = np.linspace(0, len(t), bins + 1, dtype=int)
    keep: list[int] = [0, len(t) - 1]
    for start, end in zip(edges[:-1], edges[1:]):
        if end <= start:
            continue
        seg = y[start:end]
        keep.append(start + int(np.argmin(seg)))
        keep.append(start + int(np.argmax(seg)))
    idx = np.array(sorted(set(keep)), dtype=int)
    return t[idx], y[idx]


def add_marker(ax: plt.Axes, marker_ns: float | None, label: str) -> None:
    if marker_ns is None:
        return
    xmin, xmax = ax.get_xlim()
    if xmin <= marker_ns <= xmax:
        ax.axvline(marker_ns, color="0.2", linestyle=":", linewidth=1.0)
        ax.text(
            marker_ns,
            0.98,
            label,
            transform=ax.get_xaxis_transform(),
            rotation=90,
            va="top",
            ha="right",
            fontsize=8,
        )


def style_axis(ax: plt.Axes, xlabel: bool = False) -> None:
    ax.grid(True, alpha=0.25)
    if xlabel:
        ax.set_xlabel("Time (ns)")


def plot_individual(case: CaseConfig, flow: Flow, data: dict[str, np.ndarray], out_path: Path) -> None:
    t_ns = data["time"] * 1e9
    windows = [case.full_window_ns, case.zoom_window_ns]
    window_names = ["full transient", "diagnostic zoom"]

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 7.8), sharex=False)
    for col, (window, name) in enumerate(zip(windows, window_names)):
        ax_v = axes[0, col]
        ax_k = axes[1, col]
        tx, vx = clip(t_ns, data["n10b"], window)
        tx, vx = envelope_decimate(tx, vx)
        ax_v.plot(tx, vx, color="#1f77b4", linewidth=1.25, label="V(n10b)")
        ax_v.set_title(f"{flow.label} - {name}")
        ax_v.set_ylabel("V(n10b) (V)")
        ax_v.legend(loc="best", fontsize=8)
        ax_v.set_xlim(*window)
        style_axis(ax_v)
        add_marker(ax_v, case.marker_ns, case.marker_label)

        for y, color, label in [
            (data["ku"], "#0072B2", "Ku"),
            (data["kd"], "#D55E00", "Kd"),
        ]:
            tk, yk = clip(t_ns, y, window)
            tk, yk = envelope_decimate(tk, yk)
            ax_k.plot(tk, yk, color=color, linewidth=1.35, label=label)
        ax_k.set_ylabel("Coefficient")
        ax_k.set_xlim(*window)
        ax_k.legend(loc="best", fontsize=8)
        style_axis(ax_k, xlabel=True)
        add_marker(ax_k, case.marker_ns, case.marker_label)

    fig.suptitle(f"{case.title}: pybis Ku/Kd Diagnostic", fontsize=14)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_overlay(
    case: CaseConfig,
    ng_data: dict[str, np.ndarray],
    xy_data: dict[str, np.ndarray],
    out_path: Path,
) -> None:
    windows = [case.full_window_ns, case.zoom_window_ns]
    window_names = ["full transient", "diagnostic zoom"]
    series = [
        ("n10b", "V(n10b) (V)", "V(n10b)"),
        ("ku", "Ku", "Ku"),
        ("kd", "Kd", "Kd"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(13.5, 10.2), sharex=False)
    for col, (window, name) in enumerate(zip(windows, window_names)):
        for row, (key, ylabel, title) in enumerate(series):
            ax = axes[row, col]
            for data, color, label, linestyle in [
                (ng_data, "#0072B2", "ngspice pybis", "-"),
                (xy_data, "#D55E00", "Xyce pybis", "--"),
            ]:
                t_ns = data["time"] * 1e9
                tx, yx = clip(t_ns, data[key], window)
                tx, yx = envelope_decimate(tx, yx)
                ax.plot(tx, yx, color=color, linestyle=linestyle, linewidth=1.25, label=label)
            ax.set_xlim(*window)
            ax.set_ylabel(ylabel)
            if row == 0:
                ax.set_title(f"{title} - {name}")
            if row == 2:
                style_axis(ax, xlabel=True)
            else:
                style_axis(ax)
            ax.legend(loc="best", fontsize=8)
            add_marker(ax, case.marker_ns, case.marker_label)
    fig.suptitle(f"{case.title}: ngspice vs Xyce pybis Ku/Kd", fontsize=14)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def summarize(case: CaseConfig, label: str, data: dict[str, np.ndarray]) -> list[dict[str, object]]:
    rows = []
    t_ns = data["time"] * 1e9
    for name, window in [("full", case.full_window_ns), ("zoom", case.zoom_window_ns)]:
        row: dict[str, object] = {
            "case": case.name,
            "flow": label,
            "window": name,
            "t_start_ns": window[0],
            "t_end_ns": window[1],
        }
        mask = (t_ns >= window[0]) & (t_ns <= window[1])
        for key in ["n10b", "ku", "kd"]:
            y = data[key][mask]
            row[f"{key}_min"] = float(np.min(y))
            row[f"{key}_max"] = float(np.max(y))
            row[f"{key}_mean"] = float(np.mean(y))
        rows.append(row)
    return rows


def write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def copy_if_different(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and src.read_bytes() == dst.read_bytes():
        return
    shutil.copy2(src, dst)


def build_cases() -> list[CaseConfig]:
    normal_sources = NORMAL_DIR / "kukd_sources"
    stressed_sources = STRESSED_DIR / "kukd_sources"
    return [
        CaseConfig(
            name="normal_prbs_channel",
            title="Normal PRBS7 + accepted 50 ohm RLGC channel",
            out_dir=NORMAL_DIR,
            full_window_ns=(0.0, 75.0),
            zoom_window_ns=(50.0, 70.0),
            marker_ns=None,
            marker_label="",
            ngspice_source_deck=ROOT
            / "results"
            / "prbs_rlgc_clean_2026-05-10"
            / "ngspice"
            / "tb_clean_prbs_rlgc_ngspice.sp",
            ngspice_review_deck=normal_sources / "normal_ngspice_pybis_kukd.sp",
            ngspice_review_raw=normal_sources / "normal_ngspice_pybis_kukd.raw",
            xyce_csv=ROOT
            / "results"
            / "prbs_rlgc_clean_2026-05-10"
            / "xyce"
            / "tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir.csv",
            include_replacements={
                "prbs7_vstim.inc": ROOT / "ngspice_pybis" / "prbs7_vstim.inc",
                "driver_OutputInput_Typical.sub": ROOT / "ngspice_pybis" / "driver_OutputInput_Typical.sub",
                "../new 50ohm channel/channel_ngspice.sp": ROOT
                / "new 50ohm channel"
                / "channel_ngspice.sp",
            },
        ),
        CaseConfig(
            name="stressed_edge50_prbs80_channel",
            title="Stressed edge50 PRBS80 + 30 cm loss x5 coarse10 RLGC channel",
            out_dir=STRESSED_DIR,
            full_window_ns=(0.0, 160.0),
            zoom_window_ns=(55.5, 58.8),
            marker_ns=56.69,
            marker_label="spike peak",
            ngspice_source_deck=ROOT
            / "results"
            / "stressed_edge50_corrected_crossflow_2026-05-12_clean"
            / "runs"
            / "ui2_len30cm_loss5_coarse10"
            / "ngspice_pybis_edge50_corrected"
            / "ui2_len30cm_loss5_coarse10_ngspice_pybis_edge50_corrected.sp",
            ngspice_review_deck=stressed_sources / "stressed_ngspice_pybis_edge50_kukd.sp",
            ngspice_review_raw=stressed_sources / "stressed_ngspice_pybis_edge50_kukd.raw",
            xyce_csv=ROOT
            / "results"
            / "stressed_edge50_corrected_crossflow_2026-05-12_clean"
            / "runs"
            / "ui2_len30cm_loss5_coarse10"
            / "xyce_pybis_edge50"
            / "ui2_len30cm_loss5_coarse10_xyce_pybis_edge50.cir.csv",
            include_replacements={
                "../../../models/driver_OutputInput_Typical_relaxed92_edge50_tailflat4p2_ngspice_syntax.sub": ROOT
                / "results"
                / "stressed_edge50_corrected_crossflow_2026-05-12_clean"
                / "models"
                / "driver_OutputInput_Typical_relaxed92_edge50_tailflat4p2_ngspice_syntax.sub",
            },
        ),
    ]


def main() -> int:
    all_rows: list[dict[str, object]] = []
    for case in build_cases():
        run_ngspice_if_needed(case)
        case_rows: list[dict[str, object]] = []
        ng_flow = Flow(
            label="ngspice pybis",
            path=case.ngspice_review_raw,
            fmt="ngspice",
            n10b_signal="v(n10b)",
            ku_signal="v(xdrv.ku)",
            kd_signal="v(xdrv.kd)",
        )
        xy_flow = Flow(
            label="Xyce pybis",
            path=case.xyce_csv,
            fmt="xyce",
            n10b_signal="v(n10b)",
            ku_signal="v(xdrv:ku)",
            kd_signal="v(xdrv:kd)",
        )
        ng_data = load_flow(ng_flow)
        xy_data = load_flow(xy_flow)
        plot_individual(case, ng_flow, ng_data, case.out_dir / "12_ngspice_pybis_kukd.png")
        plot_individual(case, xy_flow, xy_data, case.out_dir / "13_xyce_pybis_kukd.png")
        plot_overlay(case, ng_data, xy_data, case.out_dir / "14_ngspice_xyce_pybis_kukd_overlay.png")
        case_rows.extend(summarize(case, "ngspice_pybis", ng_data))
        case_rows.extend(summarize(case, "xyce_pybis", xy_data))
        all_rows.extend(case_rows)
        write_metrics(case.out_dir / "kukd_metrics.csv", case_rows)
        copy_if_different(case.ngspice_review_raw.with_suffix(".log"), case.out_dir / "kukd_sources" / case.ngspice_review_raw.with_suffix(".log").name)

    write_metrics(REVIEW_DIR / "kukd_metrics.csv", all_rows)
    for row in all_rows:
        if row["window"] == "zoom":
            print(
                f"{row['case']} {row['flow']}: "
                f"Ku {row['ku_min']:.4g}..{row['ku_max']:.4g}, "
                f"Kd {row['kd_min']:.4g}..{row['kd_max']:.4g}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
