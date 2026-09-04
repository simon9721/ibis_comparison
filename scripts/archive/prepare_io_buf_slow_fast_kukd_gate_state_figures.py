from __future__ import annotations

import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402


OUT = (
    ROOT
    / "results"
    / "ibis_kukd_handwritten_notes_deck"
    / "hspice_slow_fast_transistor_comparison"
    / "kukd_gate_state_slow_fast"
)
PLOT_DIR = OUT / "plots"
NATIVE_DIR = PLOT_DIR / "01_hspice_native_slow_vs_fast"
GATE_DIR = PLOT_DIR / "02_gate_state_vs_matching_hspice"
CLEAN_OLD_DIR = PLOT_DIR / "05_gate_state_vs_old_ibis_clean"
CLEAN_PAD_DIR = PLOT_DIR / "06_old_ibis_gate_state_transistor_pad_clean"
NUMERIC_DIR = OUT / "numeric"

SLOW_STUDY = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
FAST_HSPICE_STUDY = (
    ROOT / "results" / "io_buf_correct_hspice_reference_waveforms_2026-07-23"
)
FAST_GATE_STUDY = ROOT / "results" / "io_buf_correct_hspice_vs_pybis_2026-07-23"

SLOW_IBIS = ROOT / "sim" / "hspice" / "sparam" / "io_buf.ibs"
FAST_IBIS = (
    ROOT
    / "results"
    / "io_buf_fast_edge_retest_2026-06-05"
    / "source"
    / "io_buf.ibs"
)

SLOW_COLOR = "#e68613"
FAST_COLOR = "#008f95"
REFERENCE_COLOR = "#111111"
GATE_COLOR = "#d62728"
INPUT_COLOR = "#777777"


@dataclass(frozen=True)
class Case:
    case_id: str
    title: str
    pattern: str
    pulse_width_ns: float
    xlim: tuple[float, float]

    @property
    def edge_times_ns(self) -> list[float]:
        if self.pattern == "long":
            return [5.0005, 15.0005]
        if self.pattern == "short_high":
            return [5.0005, 5.0 + self.pulse_width_ns + 0.0005]
        if self.pattern == "short_low":
            return [10.0005, 10.0 + self.pulse_width_ns + 0.0005]
        raise ValueError(self.pattern)


CASES = [
    Case(
        "edge_1ps_base_50r_2pf",
        "Normal complete pulse",
        "long",
        10.0,
        (4.0, 20.0),
    ),
    Case(
        "short_pulse_1ns_high",
        "Interrupted 1 ns high pulse",
        "short_high",
        1.0,
        (4.0, 12.0),
    ),
    Case(
        "short_pulse_2ns_high",
        "Interrupted 2 ns high pulse",
        "short_high",
        2.0,
        (4.0, 13.0),
    ),
    Case(
        "short_pulse_1ns_low",
        "Interrupted 1 ns low pulse",
        "short_low",
        1.0,
        (9.0, 18.0),
    ),
    Case(
        "short_pulse_2ns_low",
        "Interrupted 2 ns low pulse",
        "short_low",
        2.0,
        (9.0, 18.0),
    ),
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    ensure_dir(path.parent)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalized(data: dict[str, np.ndarray]) -> dict[str, str]:
    return {name.lower().replace(":", "."): name for name in data}


def signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    lookup = normalized(data)
    for name in names:
        key = lookup.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"Missing {names}; available={sorted(data)}")


def hspice_waveform(path: Path, pad_name: str) -> dict[str, np.ndarray]:
    data = parse_hspice_tr0(path)
    return {
        "time_ns": signal(data, "time") * 1e9,
        "pad_v": signal(data, pad_name),
        "ku": signal(data, "v(ku)"),
        "kd": signal(data, "v(kd)"),
    }


def ngspice_waveform(path: Path) -> dict[str, np.ndarray]:
    data = parse_ngspice_raw(path)
    return {
        "time_ns": signal(data, "time") * 1e9,
        "pad_v": signal(data, "v(pad)"),
        "ku": signal(data, "v(xdrv.ku)", "v(xdrv:ku)"),
        "kd": signal(data, "v(xdrv.kd)", "v(xdrv:kd)"),
    }


def slow_hspice_path(case: Case) -> Path:
    stem = f"{case.case_id}_hspice_native_ibis"
    return (
        SLOW_STUDY
        / "cases"
        / case.case_id
        / "hspice_native_ibis"
        / f"{stem}.tr0"
    )


def fast_hspice_path(case: Case) -> Path:
    return (
        FAST_HSPICE_STUDY
        / "cases"
        / case.case_id
        / "hspice_native_fast_ibis"
        / "run.tr0"
    )


def slow_gate_path(case: Case) -> Path:
    return (
        SLOW_STUDY
        / "cases"
        / case.case_id
        / "ngspice_two_state_directional_residual"
        / f"{case.case_id}_ngspice_two_state_directional_residual.raw"
    )


def slow_transistor_path(case: Case) -> Path:
    stem = f"{case.case_id}_hspice_transistor_sp"
    return (
        SLOW_STUDY
        / "cases"
        / case.case_id
        / "hspice_transistor_sp"
        / f"{stem}.tr0"
    )


def fast_gate_path(case: Case) -> Path:
    return (
        FAST_GATE_STUDY
        / "cases"
        / case.case_id
        / "ngspice_directional_residual"
        / "run.raw"
    )


def fast_gate_is_valid(case: Case) -> tuple[bool, str]:
    run_dir = fast_gate_path(case).parent
    failed = run_dir / "failed_signature.txt"
    log = run_dir / "ngspice_stdout.log"
    if failed.exists():
        return False, "NUMERIC FAIL"
    if log.exists() and "TIMEOUT after" in log.read_text(
        encoding="utf-8", errors="replace"
    ):
        return False, "NUMERIC FAIL"
    if not fast_gate_path(case).exists():
        return False, "MISSING"
    return True, "completed"


def common_grid(case: Case, step_ns: float = 0.001) -> np.ndarray:
    return np.arange(case.xlim[0], case.xlim[1] + 0.5 * step_ns, step_ns)


def interpolate(wave: dict[str, np.ndarray], grid: np.ndarray, name: str) -> np.ndarray:
    return np.interp(grid, wave["time_ns"], wave[name])


def input_values(case: Case, time_ns: np.ndarray) -> np.ndarray:
    edge = 0.001
    if case.pattern == "long":
        points = [(0, 0), (5, 0), (5 + edge, 3.3), (15, 3.3), (15 + edge, 0)]
    elif case.pattern == "short_high":
        reverse = 5 + case.pulse_width_ns
        points = [
            (0, 0),
            (5, 0),
            (5 + edge, 3.3),
            (reverse, 3.3),
            (reverse + edge, 0),
        ]
    elif case.pattern == "short_low":
        reverse = 10 + case.pulse_width_ns
        points = [
            (0, 0),
            (5, 0),
            (5 + edge, 3.3),
            (10, 3.3),
            (10 + edge, 0),
            (reverse, 0),
            (reverse + edge, 3.3),
        ]
    else:
        raise ValueError(case.pattern)
    xp = np.array([point[0] for point in points], dtype=float)
    yp = np.array([point[1] for point in points], dtype=float)
    return np.interp(time_ns, xp, yp)


def time_weighted_rmse(time_ns: np.ndarray, error: np.ndarray) -> float:
    duration = float(time_ns[-1] - time_ns[0])
    if duration <= 0:
        return float("nan")
    return float(np.sqrt(np.trapezoid(error * error, time_ns) / duration))


def metrics(
    case: Case,
    reference: dict[str, np.ndarray],
    candidate: dict[str, np.ndarray],
    comparison: str,
    candidate_status: str = "completed",
) -> dict[str, object]:
    grid = common_grid(case)
    row: dict[str, object] = {
        "case_id": case.case_id,
        "comparison": comparison,
        "status": candidate_status,
        "window_start_ns": case.xlim[0],
        "window_stop_ns": case.xlim[1],
    }
    if candidate_status != "completed":
        return row
    for name in ("pad_v", "ku", "kd"):
        ref = interpolate(reference, grid, name)
        dut = interpolate(candidate, grid, name)
        error = dut - ref
        prefix = "pad" if name == "pad_v" else name
        row[f"{prefix}_rmse"] = time_weighted_rmse(grid, error)
        row[f"{prefix}_max_abs_error"] = float(np.max(np.abs(error)))
        row[f"reference_{prefix}_min"] = float(np.min(ref))
        row[f"reference_{prefix}_max"] = float(np.max(ref))
        row[f"candidate_{prefix}_min"] = float(np.min(dut))
        row[f"candidate_{prefix}_max"] = float(np.max(dut))
    row["pad_rmse_mv"] = float(row["pad_rmse"]) * 1e3
    return row


def add_edge_markers(ax: plt.Axes, case: Case) -> None:
    for index, edge_ns in enumerate(case.edge_times_ns):
        ax.axvline(
            edge_ns,
            color=INPUT_COLOR,
            lw=1.0,
            ls="--",
            alpha=0.85,
            label="input edges" if index == 0 else "_nolegend_",
        )


def decorate(ax: plt.Axes, case: Case, ylabel: str) -> None:
    add_edge_markers(ax, case)
    ax.axhline(0.0, color="#999999", lw=0.7, alpha=0.65)
    ax.set_xlim(*case.xlim)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.2)


def plot_trace(
    ax: plt.Axes,
    wave: dict[str, np.ndarray],
    signal_name: str,
    label: str,
    color: str,
    linewidth: float,
    marker: str | None = None,
    zorder: int = 2,
) -> None:
    count = len(wave["time_ns"])
    markevery = max(1, count // 35)
    ax.plot(
        wave["time_ns"],
        wave[signal_name],
        color=color,
        lw=linewidth,
        marker=marker,
        markevery=markevery if marker else None,
        ms=3.0,
        label=label,
        zorder=zorder,
    )


def plot_native_case(
    case: Case,
    slow: dict[str, np.ndarray],
    fast: dict[str, np.ndarray],
) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(15.5, 10.0), sharex=True)
    specs = [
        ("pad_v", "pad voltage (V)"),
        ("ku", "Ku"),
        ("kd", "Kd"),
    ]
    for ax, (name, ylabel) in zip(axes, specs):
        plot_trace(
            ax,
            slow,
            name,
            "HSPICE old slow IBIS",
            SLOW_COLOR,
            2.5,
            marker="o",
        )
        plot_trace(
            ax,
            fast,
            name,
            "HSPICE fast 5 ps IBIS",
            FAST_COLOR,
            2.3,
            marker="s",
            zorder=3,
        )
        decorate(ax, case, ylabel)
    axes[0].set_title(f"{case.title}: native-HSPICE slow versus fast IBIS")
    axes[0].legend(loc="upper center", ncol=3, fontsize=10)
    axes[-1].set_xlabel("time (ns)")
    fig.tight_layout()
    path = NATIVE_DIR / f"{case.case_id}_hspice_slow_vs_fast_kukd.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_matching_gate_case(
    case: Case,
    slow_h: dict[str, np.ndarray],
    fast_h: dict[str, np.ndarray],
    slow_gate: dict[str, np.ndarray],
    fast_gate: dict[str, np.ndarray] | None,
    fast_status: str,
) -> Path:
    fig, axes = plt.subplots(
        3,
        2,
        figsize=(17.0, 11.0),
        sharex="col",
        sharey="row",
    )
    specs = [
        ("pad_v", "pad voltage (V)"),
        ("ku", "Ku"),
        ("kd", "Kd"),
    ]
    columns = [
        (
            "Old slow IBIS: reconstruction gate PASS",
            slow_h,
            slow_gate,
            "slow IBIS gate-state",
            "completed",
        ),
        (
            "Fast 5 ps IBIS: reconstruction gate FAIL",
            fast_h,
            fast_gate,
            "fast IBIS gate-state",
            fast_status,
        ),
    ]
    for column, (title, reference, gate, gate_label, status) in enumerate(columns):
        for row, (name, ylabel) in enumerate(specs):
            ax = axes[row, column]
            plot_trace(
                ax,
                reference,
                name,
                "matching HSPICE native IBIS",
                REFERENCE_COLOR,
                3.1,
                zorder=2,
            )
            if gate is not None and status == "completed":
                plot_trace(
                    ax,
                    gate,
                    name,
                    gate_label,
                    GATE_COLOR,
                    2.0,
                    marker="D",
                    zorder=3,
                )
            else:
                ax.text(
                    0.5,
                    0.5,
                    "Gate-state result unavailable\nngspice numeric failure",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=13,
                    color=GATE_COLOR,
                    bbox={
                        "facecolor": "white",
                        "edgecolor": GATE_COLOR,
                        "alpha": 0.92,
                    },
                )
            decorate(ax, case, ylabel if column == 0 else "")
            if row == 0:
                ax.set_title(title, fontsize=13, fontweight="bold")
            if row == 2:
                ax.set_xlabel("time (ns)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    if fast_gate is not None and fast_status == "completed":
        fast_handles, fast_labels = axes[0, 1].get_legend_handles_labels()
        for handle, label in zip(fast_handles, fast_labels):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=4,
        bbox_to_anchor=(0.5, 0.965),
        fontsize=10,
    )
    fig.suptitle(
        f"{case.title}: gate-state model versus its matching native-HSPICE IBIS",
        y=0.995,
        fontsize=16,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = GATE_DIR / f"{case.case_id}_gate_state_slow_fast.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_clean_old_gate_case(
    case: Case,
    slow_h: dict[str, np.ndarray],
    slow_gate: dict[str, np.ndarray],
) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(15.5, 10.0), sharex=True)
    specs = [
        ("pad_v", "pad voltage (V)"),
        ("ku", "Ku"),
        ("kd", "Kd"),
    ]
    for ax, (name, ylabel) in zip(axes, specs):
        plot_trace(
            ax,
            slow_h,
            name,
            "HSPICE old IBIS",
            REFERENCE_COLOR,
            3.2,
            zorder=2,
        )
        plot_trace(
            ax,
            slow_gate,
            name,
            "gate-state model",
            GATE_COLOR,
            2.0,
            marker="D",
            zorder=3,
        )
        decorate(ax, case, ylabel)
    axes[0].set_title(case.title, fontsize=16, fontweight="bold")
    axes[0].legend(loc="upper center", ncol=3, fontsize=10)
    axes[-1].set_xlabel("time (ns)")
    fig.tight_layout()
    path = CLEAN_OLD_DIR / f"{case.case_id}_gate_state_vs_hspice_old_ibis.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_clean_old_pad_case(
    case: Case,
    slow_h: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
    slow_gate: dict[str, np.ndarray],
) -> Path:
    fig, ax = plt.subplots(figsize=(15.5, 5.8))
    plot_trace(
        ax,
        slow_h,
        "pad_v",
        "HSPICE old IBIS",
        REFERENCE_COLOR,
        3.0,
        zorder=3,
    )
    plot_trace(
        ax,
        transistor,
        "pad_v",
        "HSPICE transistor",
        "#858585",
        5.0,
        zorder=1,
    )
    plot_trace(
        ax,
        slow_gate,
        "pad_v",
        "gate-state model",
        GATE_COLOR,
        2.0,
        marker="D",
        zorder=4,
    )
    decorate(ax, case, "pad voltage (V)")
    ax.set_title(case.title, fontsize=16, fontweight="bold")
    ax.set_xlabel("time (ns)")
    ax.legend(loc="upper center", ncol=4, fontsize=10)
    fig.tight_layout()
    path = CLEAN_PAD_DIR / f"{case.case_id}_pad_three_way.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_reconstruction_gate() -> Path:
    with (SLOW_STUDY / "gate_fit_summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        slow = next(csv.DictReader(handle))
    with (FAST_GATE_STUDY / "fast_ibis_reconstruction_summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        fast = next(csv.DictReader(handle))
    values = {
        "worst reconstruction RMSE": [
            float(slow["directional_residual_reconstruction_rmse_max"]),
            float(fast["worst_rmse"]),
        ],
        "worst maximum error": [
            float(slow["directional_residual_reconstruction_max_error_max"]),
            float(fast["worst_max_error"]),
        ],
    }
    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.2), constrained_layout=True)
    labels = ["old slow IBIS\nPASS", "fast 5 ps IBIS\nFAIL"]
    colors = [SLOW_COLOR, FAST_COLOR]
    for ax, (title, vals) in zip(axes, values.items()):
        bars = ax.bar(labels, vals, color=colors, width=0.58)
        for bar, value in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + max(vals) * 0.035,
                f"{value:.4f}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )
        ax.set_title(title)
        ax.set_ylabel("coefficient error")
        ax.grid(axis="y", alpha=0.22)
        ax.set_ylim(0, max(vals) * 1.2)
    fig.suptitle(
        "Offline gate-state reconstruction decides whether transient results are valid",
        fontsize=15,
        fontweight="bold",
    )
    path = PLOT_DIR / "03_reconstruction_gate_slow_vs_fast.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_metric_summary(rows: list[dict[str, object]]) -> Path:
    gate_rows = {
        (str(row["case_id"]), str(row["comparison"])): row
        for row in rows
        if str(row["comparison"]).startswith("gate_state")
    }
    case_labels = [
        "normal",
        "1 ns high",
        "2 ns high",
        "1 ns low",
        "2 ns low",
    ]
    fields = [
        ("pad_rmse_mv", "pad RMSE (mV)"),
        ("ku_rmse", "Ku RMSE"),
        ("kd_rmse", "Kd RMSE"),
    ]
    x = np.arange(len(CASES))
    width = 0.36
    fig, axes = plt.subplots(3, 1, figsize=(15.0, 10.0), sharex=True)
    for ax, (field, ylabel) in zip(axes, fields):
        slow_values = []
        fast_values = []
        fast_failed = []
        for case in CASES:
            slow_row = gate_rows[(case.case_id, "gate_state_slow_vs_slow_hspice")]
            fast_row = gate_rows[(case.case_id, "gate_state_fast_vs_fast_hspice")]
            slow_values.append(float(slow_row.get(field, np.nan)))
            status = str(fast_row["status"])
            fast_values.append(
                float(fast_row.get(field, np.nan))
                if status == "completed"
                else np.nan
            )
            fast_failed.append(status != "completed")
        ax.bar(
            x - width / 2,
            slow_values,
            width,
            color=SLOW_COLOR,
            label="slow gate-state vs slow HSPICE",
        )
        ax.bar(
            x + width / 2,
            fast_values,
            width,
            color=FAST_COLOR,
            label="fast gate-state vs fast HSPICE",
        )
        finite = np.asarray(slow_values + fast_values, dtype=float)
        ymax = float(np.nanmax(finite)) if np.any(np.isfinite(finite)) else 1.0
        for index, failed in enumerate(fast_failed):
            if failed:
                ax.text(
                    x[index] + width / 2,
                    ymax * 0.04,
                    "FAIL",
                    ha="center",
                    va="bottom",
                    rotation=90,
                    color=GATE_COLOR,
                    fontweight="bold",
                )
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.22)
        ax.set_ylim(0, ymax * 1.16)
    axes[0].legend(loc="upper center", ncol=2)
    axes[-1].set_xticks(x, case_labels)
    axes[-1].set_xlabel("stimulus")
    fig.suptitle(
        "Gate-state agreement with each model's matching native-HSPICE IBIS",
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    path = PLOT_DIR / "04_gate_state_matching_reference_rmse.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def make_contact_sheet(paths: list[Path], output: Path, title: str) -> None:
    images = [plt.imread(path) for path in paths]
    fig, axes = plt.subplots(3, 2, figsize=(22.0, 22.0))
    flat = axes.ravel()
    for ax, image in zip(flat, images):
        ax.imshow(image)
        ax.axis("off")
    for ax in flat[len(images) :]:
        ax.axis("off")
    fig.suptitle(title, fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98), h_pad=0.4, w_pad=0.3)
    fig.savefig(output, dpi=135)
    plt.close(fig)


def numeric_rows(
    case: Case,
    waves: dict[str, dict[str, np.ndarray] | None],
) -> list[dict[str, object]]:
    grid = common_grid(case)
    values: dict[str, np.ndarray] = {
        "time_ns": grid,
        "input_v": input_values(case, grid),
    }
    for flow, wave in waves.items():
        for name in ("pad_v", "ku", "kd"):
            values[f"{flow}_{name}"] = (
                interpolate(wave, grid, name)
                if wave is not None
                else np.full_like(grid, np.nan)
            )
    fields = list(values)
    return [
        {
            field: (
                "" if not np.isfinite(float(values[field][index]))
                else f"{float(values[field][index]):.12g}"
            )
            for field in fields
        }
        for index in range(len(grid))
    ]


def pad_numeric_rows(
    case: Case,
    slow_h: dict[str, np.ndarray],
    transistor: dict[str, np.ndarray],
    slow_gate: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    grid = common_grid(case)
    values = {
        "time_ns": grid,
        "input_v": input_values(case, grid),
        "hspice_old_ibis_pad_v": interpolate(slow_h, grid, "pad_v"),
        "hspice_transistor_pad_v": interpolate(transistor, grid, "pad_v"),
        "gate_state_pad_v": interpolate(slow_gate, grid, "pad_v"),
    }
    fields = list(values)
    return [
        {
            field: f"{float(values[field][index]):.12g}"
            for field in fields
        }
        for index in range(len(grid))
    ]


def main() -> None:
    for path in [
        SLOW_IBIS,
        FAST_IBIS,
        SLOW_STUDY,
        FAST_HSPICE_STUDY,
        FAST_GATE_STUDY,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)
    for path in [
        OUT,
        PLOT_DIR,
        NATIVE_DIR,
        GATE_DIR,
        CLEAN_OLD_DIR,
        CLEAN_PAD_DIR,
        NUMERIC_DIR,
    ]:
        ensure_dir(path)

    all_metric_rows: list[dict[str, object]] = []
    source_rows: list[dict[str, object]] = []
    native_paths: list[Path] = []
    gate_paths: list[Path] = []
    clean_old_paths: list[Path] = []
    clean_pad_paths: list[Path] = []

    for case in CASES:
        paths = {
            "hspice_slow_ibis": slow_hspice_path(case),
            "hspice_fast_ibis": fast_hspice_path(case),
            "hspice_transistor": slow_transistor_path(case),
            "gate_state_slow_ibis": slow_gate_path(case),
            "gate_state_fast_ibis": fast_gate_path(case),
        }
        for flow, path in paths.items():
            if flow == "gate_state_fast_ibis":
                valid, status = fast_gate_is_valid(case)
            else:
                valid, status = path.exists(), "completed" if path.exists() else "MISSING"
            if flow == "hspice_transistor":
                source_ibis = ""
                source_ibis_hash = ""
                source_model = path.parent / "io_buf.sp"
            else:
                source_model = None
                source_ibis_path = FAST_IBIS if "fast" in flow else SLOW_IBIS
                source_ibis = str(source_ibis_path.relative_to(ROOT))
                source_ibis_hash = sha256(source_ibis_path)
            source_rows.append(
                {
                    "case_id": case.case_id,
                    "flow": flow,
                    "status": status,
                    "source_ibis": source_ibis,
                    "source_ibis_sha256": source_ibis_hash,
                    "source_model": (
                        str(source_model.relative_to(ROOT))
                        if source_model is not None
                        else ""
                    ),
                    "source_model_sha256": (
                        sha256(source_model)
                        if source_model is not None and source_model.exists()
                        else ""
                    ),
                    "waveform_path": str(path.relative_to(ROOT)),
                    "waveform_sha256": sha256(path) if path.exists() else "",
                }
            )
            if not valid and flow != "gate_state_fast_ibis":
                raise FileNotFoundError(path)

        slow_h = hspice_waveform(paths["hspice_slow_ibis"], "v(pad_ibis)")
        fast_h = hspice_waveform(paths["hspice_fast_ibis"], "v(pad)")
        transistor_data = parse_hspice_tr0(paths["hspice_transistor"])
        transistor = {
            "time_ns": signal(transistor_data, "time") * 1e9,
            "pad_v": signal(transistor_data, "v(pad_sp)"),
        }
        slow_gate = ngspice_waveform(paths["gate_state_slow_ibis"])
        fast_valid, fast_status = fast_gate_is_valid(case)
        fast_gate = (
            ngspice_waveform(paths["gate_state_fast_ibis"]) if fast_valid else None
        )

        all_metric_rows.append(
            metrics(
                case,
                slow_h,
                fast_h,
                "hspice_fast_vs_hspice_slow",
            )
        )
        all_metric_rows.append(
            metrics(
                case,
                slow_h,
                slow_gate,
                "gate_state_slow_vs_slow_hspice",
            )
        )
        all_metric_rows.append(
            metrics(
                case,
                fast_h,
                fast_gate if fast_gate is not None else fast_h,
                "gate_state_fast_vs_fast_hspice",
                candidate_status=fast_status,
            )
        )

        native_paths.append(plot_native_case(case, slow_h, fast_h))
        gate_paths.append(
            plot_matching_gate_case(
                case,
                slow_h,
                fast_h,
                slow_gate,
                fast_gate,
                fast_status,
            )
        )
        clean_old_paths.append(plot_clean_old_gate_case(case, slow_h, slow_gate))
        clean_pad_paths.append(
            plot_clean_old_pad_case(case, slow_h, transistor, slow_gate)
        )
        write_csv(
            NUMERIC_DIR / f"{case.case_id}_aligned_waveforms.csv",
            numeric_rows(
                case,
                {
                    "hspice_slow": slow_h,
                    "hspice_fast": fast_h,
                    "gate_slow": slow_gate,
                    "gate_fast": fast_gate,
                },
            ),
        )
        write_csv(
            NUMERIC_DIR / f"{case.case_id}_pad_three_way.csv",
            pad_numeric_rows(case, slow_h, transistor, slow_gate),
        )

    reconstruction_plot = plot_reconstruction_gate()
    metric_plot = plot_metric_summary(all_metric_rows)
    native_contact = PLOT_DIR / "01_hspice_native_slow_vs_fast_contact_sheet.png"
    gate_contact = PLOT_DIR / "02_gate_state_slow_fast_contact_sheet.png"
    clean_old_contact = PLOT_DIR / "05_gate_state_vs_old_ibis_clean_contact_sheet.png"
    clean_pad_contact = (
        PLOT_DIR / "06_old_ibis_gate_state_transistor_pad_clean_contact_sheet.png"
    )
    make_contact_sheet(
        native_paths,
        native_contact,
        "Native-HSPICE runtime behavior: old slow IBIS versus fast 5 ps IBIS",
    )
    make_contact_sheet(
        gate_paths,
        gate_contact,
        "Gate-state model versus its matching native-HSPICE IBIS",
    )
    make_contact_sheet(
        clean_old_paths,
        clean_old_contact,
        "Gate-state model versus HSPICE old IBIS",
    )
    make_contact_sheet(
        clean_pad_paths,
        clean_pad_contact,
        "Old IBIS, transistor, and gate-state pad voltage",
    )

    write_csv(OUT / "comparison_metrics.csv", all_metric_rows)
    write_csv(OUT / "source_manifest.csv", source_rows)

    metric_lookup = {
        (str(row["case_id"]), str(row["comparison"])): row
        for row in all_metric_rows
    }

    def value(case_id: str, comparison: str, field: str, scale: float = 1.0) -> str:
        row = metric_lookup[(case_id, comparison)]
        if str(row["status"]) != "completed" or field not in row:
            return "NUMERIC FAIL"
        return f"{float(row[field]) * scale:.4f}"

    readme = f"""# Slow/Fast IBIS Ku/Kd and Gate-State Comparison

## What Is Compared

1. Native-HSPICE runtime `Ku/Kd` from the old slow IBIS and regenerated 5 ps IBIS.
2. The `two_state_directional_residual` ngspice model generated separately from each IBIS.
3. Each gate-state result is scored only against the native-HSPICE run using the same IBIS file.

Common bench: 3.3 V ideal supply and enable, 1 ps input command edges, 50 ohm to ground in parallel with 2 pF, 27 C, and no channel.

## Main Finding

- Slow IBIS offline gate-state reconstruction: worst RMSE `0.01994`, worst max error `0.04869`, `PASS`.
- Fast 5 ps IBIS offline gate-state reconstruction: worst RMSE `0.46428`, worst max error `0.69980`, `FAIL`.
- Normal complete-pulse slow gate-state runtime errors are pad `{value('edge_1ps_base_50r_2pf', 'gate_state_slow_vs_slow_hspice', 'pad_rmse_mv')} mV`, Ku `{value('edge_1ps_base_50r_2pf', 'gate_state_slow_vs_slow_hspice', 'ku_rmse')}`, Kd `{value('edge_1ps_base_50r_2pf', 'gate_state_slow_vs_slow_hspice', 'kd_rmse')}`.
- Normal complete-pulse fast gate-state runtime errors are pad `{value('edge_1ps_base_50r_2pf', 'gate_state_fast_vs_fast_hspice', 'pad_rmse_mv')} mV`, Ku `{value('edge_1ps_base_50r_2pf', 'gate_state_fast_vs_fast_hspice', 'ku_rmse')}`, Kd `{value('edge_1ps_base_50r_2pf', 'gate_state_fast_vs_fast_hspice', 'kd_rmse')}`.
- The fast 2 ns high gate-state run is a numeric failure; it is shown as such rather than plotting a partial raw file.
- Slow short-high remains incomplete: Ku is often reasonable, but Kd recovery is wrong.
- Slow short-low is the mirror: Kd can be accurate while Ku recovery is wrong; the 2 ns low case is the strongest slow-IBIS result.
- Fast gate-state transient curves are diagnostic only because the offline reconstruction gate fails before simulation.

## Figures

- `{native_contact.relative_to(OUT)}`
- `{gate_contact.relative_to(OUT)}`
- `{reconstruction_plot.relative_to(OUT)}`
- `{metric_plot.relative_to(OUT)}`
- `{clean_old_contact.relative_to(OUT)}`
- `{clean_pad_contact.relative_to(OUT)}`
- `plots/01_hspice_native_slow_vs_fast/<case>_hspice_slow_vs_fast_kukd.png`
- `plots/02_gate_state_vs_matching_hspice/<case>_gate_state_slow_fast.png`
- `plots/05_gate_state_vs_old_ibis_clean/<case>_gate_state_vs_hspice_old_ibis.png`
- `plots/06_old_ibis_gate_state_transistor_pad_clean/<case>_pad_three_way.png`

## Numeric Evidence

- `comparison_metrics.csv`
- `source_manifest.csv`
- `numeric/<case>_aligned_waveforms.csv`

No HSPICE simulations were run by this report. Existing `.tr0` references were read from cache. The missing fast 2 ns low ngspice gate-state case was generated before this report; its exact deck, model, raw file, and log remain in the fast comparison study.
"""
    (OUT / "README.md").write_text(readme, encoding="ascii")
    print(OUT)


if __name__ == "__main__":
    main()
