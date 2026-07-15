from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402
import run_io_buf_value_matched_replay_redo as redo  # noqa: E402


STUDY = ROOT / "results" / "io_buf_value_matched_replay_redo_2026-06-25"
OUT = ROOT / "results" / "io_buf_value_match_misalignment_demo_2026-06-25"
CASE_ID = "short_pulse_2ns_high"
FALL_NS = 7.0
SAMPLE_NS = 7.001
PRE_EDGE_NS = 7.0

COL = {
    "input": "#222222",
    "hspice": "#0057b8",
    "legacy": "#ff7f0e",
    "vm": "#159947",
    "ku": "#0072b2",
    "kd": "#d55e00",
    "ku2": "#00a6d6",
    "kd2": "#cc79a7",
    "mid": "#6f2dbd",
    "target": "#e7298a",
    "actual": "#111827",
    "gray": "#6b7280",
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def find_signal(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    return redo.find_signal(data, name)


def to_ns(signal: np.ndarray) -> np.ndarray:
    return redo.to_ns(signal)


def val_at(t: np.ndarray, y: np.ndarray, x: float) -> float:
    return float(np.interp(x, t, y))


def style(ax: plt.Axes, ylabel: str | None = None) -> None:
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(True, color="#d8dee8", linewidth=0.8)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def parse_table(subckt: Path, source: str) -> np.ndarray:
    text = subckt.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(rf"^B\d+\s+{re.escape(source)}\s+0\s+V\s*=\s*pwl\(", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"source {source} not found in {subckt}")
    line_end = text.find("\n", match.start())
    line = text[match.start() : line_end if line_end >= 0 else len(text)]
    # All relevant tables use: pwl(min(max(V(...), 0), tmax), t0, y0, ...)
    try:
        # Split after the inner max(...), then after the outer min(...). The
        # remaining values are the actual PWL pairs.
        payload = line.split("),", 2)[2].split("),", 1)[1].rsplit(")", 1)[0]
    except IndexError as exc:
        raise ValueError(f"could not parse PWL payload for {source}") from exc
    nums = [float(item) for item in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", payload)]
    if len(nums) % 2:
        raise ValueError(f"odd number of PWL values for {source}")
    arr = np.asarray(nums, dtype=float).reshape(-1, 2)
    order = np.argsort(arr[:, 0])
    return arr[order]


def nearest_time(table: np.ndarray, value: float) -> tuple[float, float]:
    idx = int(np.nanargmin(np.abs(table[:, 1] - value)))
    return float(table[idx, 0]), float(table[idx, 1])


def interp_table(table: np.ndarray, x: float) -> float:
    return float(np.interp(x, table[:, 0], table[:, 1]))


def load_data() -> dict[str, object]:
    case_dir = STUDY / "cases" / CASE_ID
    debug_dir = STUDY / "debug_timeout" / "stop_7p25ns"
    hspice = parse_hspice_tr0(case_dir / "hspice_native_ibis" / f"{CASE_ID}_hspice_native_ibis.tr0")
    legacy = parse_ngspice_raw(case_dir / "ngspice_legacy" / f"{CASE_ID}_ngspice_legacy.raw")
    vm = parse_ngspice_raw(debug_dir / "short_pulse_2ns_value_matched_stop_7p25ns.raw")
    subckt = debug_dir / "driver_OutputInput_Typical.sub"
    tables = {
        "ku_rise": parse_table(subckt, "HKUR0"),
        "kd_rise": parse_table(subckt, "HKDR0"),
        "ku_fall": parse_table(subckt, "HKUF0"),
        "kd_fall": parse_table(subckt, "HKDF0"),
    }
    return {"hspice": hspice, "legacy": legacy, "vm": vm, "tables": tables, "subckt": subckt}


def build_summary(data: dict[str, object]) -> dict[str, float]:
    vm = data["vm"]
    assert isinstance(vm, dict)
    vt = to_ns(find_signal(vm, "time"))
    summary = {
        "pre_edge_ns": PRE_EDGE_NS,
        "sample_ns": SAMPLE_NS,
        "pre_ku": val_at(vt, find_signal(vm, "v(xdrv.ku)"), PRE_EDGE_NS),
        "pre_kd": val_at(vt, find_signal(vm, "v(xdrv.kd)"), PRE_EDGE_NS),
        "sample_kusamp": val_at(vt, find_signal(vm, "v(xdrv.kusamp)"), SAMPLE_NS),
        "sample_kdsamp": val_at(vt, find_signal(vm, "v(xdrv.kdsamp)"), SAMPLE_NS),
        "raw_tf_ku": val_at(vt, find_signal(vm, "v(xdrv.tf_ku)"), SAMPLE_NS),
        "raw_tf_kd": val_at(vt, find_signal(vm, "v(xdrv.tf_kd)"), SAMPLE_NS),
        "raw_tf_start": val_at(vt, find_signal(vm, "v(xdrv.tf_start)"), SAMPLE_NS),
        "raw_start_disagree": val_at(vt, find_signal(vm, "v(xdrv.start_disagree)"), SAMPLE_NS),
        "raw_vmstart": val_at(vt, find_signal(vm, "v(xdrv.vmstart)"), SAMPLE_NS),
        "raw_vmarg": val_at(vt, find_signal(vm, "v(xdrv.vmarg)"), SAMPLE_NS),
        "raw_hvmatch": val_at(vt, find_signal(vm, "v(xdrv.hvmatch)"), SAMPLE_NS),
        "target_7001_kdtarget": val_at(vt, find_signal(vm, "v(xdrv.kdtarget)"), 7.001),
        "target_7001_vmarg": val_at(vt, find_signal(vm, "v(xdrv.vmarg)"), 7.001),
        "target_7015_kdtarget": val_at(vt, find_signal(vm, "v(xdrv.kdtarget)"), 7.015),
        "target_7015_vmarg": val_at(vt, find_signal(vm, "v(xdrv.vmarg)"), 7.015),
        "hspice_7001_ku": val_at(to_ns(find_signal(data["hspice"], "time")), find_signal(data["hspice"], "v(ku)"), 7.001),
        "hspice_7001_kd": val_at(to_ns(find_signal(data["hspice"], "time")), find_signal(data["hspice"], "v(kd)"), 7.001),
        "hspice_7080_ku": val_at(to_ns(find_signal(data["hspice"], "time")), find_signal(data["hspice"], "v(ku)"), 7.080),
        "hspice_7080_kd": val_at(to_ns(find_signal(data["hspice"], "time")), find_signal(data["hspice"], "v(kd)"), 7.080),
    }
    tables = data["tables"]
    assert isinstance(tables, dict)
    for prefix, ku_val, kd_val in [
        ("pre", summary["pre_ku"], summary["pre_kd"]),
        ("sample", summary["sample_kusamp"], summary["sample_kdsamp"]),
    ]:
        tr_ku, tr_ku_val = nearest_time(tables["ku_rise"], ku_val)
        tr_kd, tr_kd_val = nearest_time(tables["kd_rise"], kd_val)
        tf_ku, tf_ku_val = nearest_time(tables["ku_fall"], ku_val)
        tf_kd, tf_kd_val = nearest_time(tables["kd_fall"], kd_val)
        tf_start = 0.5 * (tf_ku + tf_kd)
        summary.update(
            {
                f"{prefix}_tr_ku": tr_ku,
                f"{prefix}_tr_kd": tr_kd,
                f"{prefix}_tr_disagree": abs(tr_ku - tr_kd),
                f"{prefix}_tf_ku": tf_ku,
                f"{prefix}_tf_kd": tf_kd,
                f"{prefix}_tf_start": tf_start,
                f"{prefix}_tf_disagree": abs(tf_ku - tf_kd),
                f"{prefix}_ku_at_tf": tf_ku_val,
                f"{prefix}_kd_at_tf": tf_kd_val,
                f"{prefix}_ku_at_mid": interp_table(tables["ku_fall"], tf_start),
                f"{prefix}_kd_at_mid": interp_table(tables["kd_fall"], tf_start),
            }
        )
        summary[f"{prefix}_ku_mid_error"] = summary[f"{prefix}_ku_at_mid"] - ku_val
        summary[f"{prefix}_kd_mid_error"] = summary[f"{prefix}_kd_at_mid"] - kd_val
    return summary


def plot_event_context(data: dict[str, object], s: dict[str, float]) -> None:
    h = data["hspice"]
    legacy = data["legacy"]
    vm = data["vm"]
    assert isinstance(h, dict) and isinstance(legacy, dict) and isinstance(vm, dict)
    ht = to_ns(find_signal(h, "time"))
    lt = to_ns(find_signal(legacy, "time"))
    vt = to_ns(find_signal(vm, "time"))

    value_match_end = float(vt[-1])
    fig, axes = plt.subplots(
        4,
        1,
        figsize=(12.5, 10.5),
        sharex=True,
        gridspec_kw={"height_ratios": [0.65, 1.05, 1.05, 1.05]},
        constrained_layout=True,
    )
    axes[0].plot(vt, find_signal(vm, "v(in_dig)") / 3.3, color=COL["input"], lw=2.2, label="input command")
    axes[0].fill_between([5.0, FALL_NS], [1, 1], [0, 0], color="#eef2ff", alpha=0.8)
    axes[0].text(5.58, 0.50, "2 ns high pulse", fontsize=12, fontweight="bold", color="#1f2937")
    axes[0].set_ylim(-0.08, 1.13)
    style(axes[0], "Input")

    axes[1].plot(ht, find_signal(h, "v(pad_ibis)"), color=COL["hspice"], lw=2.0, label="HSPICE native IBIS pad")
    axes[1].plot(lt, find_signal(legacy, "v(pad)"), color=COL["legacy"], lw=1.6, label="legacy pybis pad")
    axes[1].plot(vt, find_signal(vm, "v(pad)"), color=COL["vm"], lw=1.8, label="value-match partial pad")
    style(axes[1], "Pad (V)")

    axes[2].plot(ht, find_signal(h, "v(ku)"), color=COL["hspice"], lw=2.0, label="HSPICE Ku")
    axes[2].plot(lt, find_signal(legacy, "v(xdrv.ku)"), color=COL["legacy"], lw=1.3, label="legacy Ku")
    axes[2].plot(vt, find_signal(vm, "v(xdrv.ku)"), color=COL["actual"], lw=1.6, label="value-match Ku")
    axes[2].plot([PRE_EDGE_NS], [s["pre_ku"]], "o", color=COL["actual"], ms=7)
    axes[2].axhline(s["pre_ku"], color=COL["actual"], lw=1.2, ls=":")
    axes[2].annotate(
        f"value-match Ku={s['pre_ku']:.3f}",
        xy=(PRE_EDGE_NS, s["pre_ku"]),
        xytext=(6.24, 0.42),
        arrowprops={"arrowstyle": "->", "color": COL["actual"], "lw": 1.3},
        fontsize=10,
        color=COL["actual"],
    )
    style(axes[2], "Ku")

    axes[3].plot(ht, find_signal(h, "v(kd)"), color=COL["hspice"], lw=2.0, label="HSPICE Kd")
    axes[3].plot(lt, find_signal(legacy, "v(xdrv.kd)"), color=COL["legacy"], lw=1.3, label="legacy Kd")
    axes[3].plot(vt, find_signal(vm, "v(xdrv.kd)"), color=COL["actual"], lw=1.6, label="value-match Kd")
    axes[3].plot([PRE_EDGE_NS], [s["pre_kd"]], "o", color=COL["actual"], ms=7)
    axes[3].axhline(s["pre_kd"], color=COL["actual"], lw=1.2, ls=":")
    axes[3].annotate(
        f"value-match Kd={s['pre_kd']:.3f}",
        xy=(PRE_EDGE_NS, s["pre_kd"]),
        xytext=(6.18, 0.30),
        arrowprops={"arrowstyle": "->", "color": COL["actual"], "lw": 1.3},
        fontsize=10,
        color=COL["actual"],
    )
    style(axes[3], "Kd")

    # Keep the pre-edge state visually prominent without hiding HSPICE/legacy.
    axes[2].axhline(s["pre_ku"], color=COL["actual"], lw=1.2, ls=":")
    axes[3].axhline(s["pre_kd"], color=COL["actual"], lw=1.2, ls=":")

    for ax in axes:
        ax.axvline(5.0, color=COL["gray"], lw=1.1)
        ax.axvline(FALL_NS, color="#111111", lw=1.8)
        ax.axvline(value_match_end, color=COL["vm"], lw=1.1, ls=":")
        ax.axvspan(value_match_end, 14.0, color="#f8fafc", alpha=0.75, zorder=-1)
        ax.text(5.01, ax.get_ylim()[1] * 0.88, "rise", color=COL["gray"], fontsize=10)
        ax.text(FALL_NS + 0.01, ax.get_ylim()[1] * 0.88, "fall/retrigger", color="#111111", fontsize=10)
        ax.set_xlim(4.92, 14.0)
        ax.legend(loc="best", frameon=False, ncol=3 if ax is axes[1] else 2)
    axes[1].text(
        value_match_end + 0.12,
        axes[1].get_ylim()[1] * 0.72,
        "value-match partial raw ends here\n(full run times out)",
        color=COL["vm"],
        fontsize=10,
        va="top",
    )
    axes[-1].set_xlabel("Time (ns)")
    axes[0].set_title("01 Event context: pad and coefficients at the interrupted falling edge", fontweight="bold")
    fig.savefig(OUT / "01_event_context.png", dpi=180)
    plt.close(fig)


def plot_rising_snapshot(data: dict[str, object], s: dict[str, float]) -> None:
    tables = data["tables"]
    assert isinstance(tables, dict)
    fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)
    ax.plot(tables["ku_rise"][:, 0], tables["ku_rise"][:, 1], color=COL["ku"], lw=2.0, label="Ku rise table")
    ax.plot(tables["kd_rise"][:, 0], tables["kd_rise"][:, 1], color=COL["kd"], lw=2.0, label="Kd rise table")
    for key, color, label, valkey in [
        ("pre_tr_ku", COL["ku"], "Ku maps to rise time", "pre_ku"),
        ("pre_tr_kd", COL["kd"], "Kd maps to rise time", "pre_kd"),
    ]:
        ax.axvline(s[key], color=color, lw=1.5, ls="--")
        ax.axhline(s[valkey], color=color, lw=1.0, ls=":")
        ax.plot([s[key]], [s[valkey]], "o", color=color, ms=7, label=f"{label}: {s[key]:.3f} ns")
        ax.text(0.08, s[valkey] + (0.025 if valkey == "pre_ku" else -0.055), f"{valkey.replace('pre_', '').upper()}={s[valkey]:.3f}", color=color, fontsize=11, fontweight="bold")
    ax.annotate(
        f"On rising table, Ku and Kd agree within {s['pre_tr_disagree']:.3f} ns",
        xy=(0.50 * (s["pre_tr_ku"] + s["pre_tr_kd"]), 0.62),
        xytext=(2.7, 0.78),
        arrowprops={"arrowstyle": "->", "color": COL["gray"]},
        fontsize=11,
    )
    ax.set_xlim(0, 4.2)
    ax.set_ylim(-0.12, 1.08)
    ax.set_xlabel("Rising table time (ns)")
    ax.set_ylabel("Coefficient")
    ax.set_title("02 Rising-state snapshot before the reverse edge", fontweight="bold")
    style(ax)
    ax.legend(loc="best", frameon=False)
    fig.savefig(OUT / "02_rising_state_snapshot.png", dpi=180)
    plt.close(fig)


def plot_inverse_mapping(data: dict[str, object], s: dict[str, float]) -> None:
    tables = data["tables"]
    assert isinstance(tables, dict)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8.2), sharex=True, constrained_layout=True)
    axes[0].plot(tables["ku_fall"][:, 0], tables["ku_fall"][:, 1], color=COL["ku"], lw=2.0, label="Ku fall table")
    axes[0].axhline(s["pre_ku"], color=COL["ku"], lw=1.0, ls=":")
    axes[0].axvline(s["pre_tf_ku"], color=COL["ku"], lw=1.5, ls="--")
    axes[0].plot([s["pre_tf_ku"]], [s["pre_ku_at_tf"]], "o", color=COL["ku"], ms=7)
    axes[0].text(0.06, s["pre_ku"] + 0.035, f"Ku_current={s['pre_ku']:.3f}", color=COL["ku"], fontsize=11, fontweight="bold")
    axes[0].annotate(f"Ku-inferred falling start = {s['pre_tf_ku']:.3f} ns", xy=(s["pre_tf_ku"], s["pre_ku"]), xytext=(0.15, 0.55), arrowprops={"arrowstyle": "->", "color": COL["ku"]})
    style(axes[0], "Ku")

    axes[1].plot(tables["kd_fall"][:, 0], tables["kd_fall"][:, 1], color=COL["kd"], lw=2.0, label="Kd fall table")
    axes[1].axhline(s["pre_kd"], color=COL["kd"], lw=1.0, ls=":")
    axes[1].axvline(s["pre_tf_kd"], color=COL["kd"], lw=1.5, ls="--")
    axes[1].plot([s["pre_tf_kd"]], [s["pre_kd_at_tf"]], "o", color=COL["kd"], ms=7)
    axes[1].text(0.06, s["pre_kd"] + 0.035, f"Kd_current={s['pre_kd']:.3f}", color=COL["kd"], fontsize=11, fontweight="bold")
    axes[1].annotate(f"Kd-inferred falling start = {s['pre_tf_kd']:.3f} ns", xy=(s["pre_tf_kd"], s["pre_kd"]), xytext=(2.55, 0.30), arrowprops={"arrowstyle": "->", "color": COL["kd"]})
    style(axes[1], "Kd")

    for ax in axes:
        ax.axvspan(s["pre_tf_ku"], s["pre_tf_kd"], color="#f2c94c", alpha=0.18)
        ax.legend(loc="best", frameon=False)
        ax.set_xlim(0, 4.2)
        ax.set_ylim(-0.12, 1.08)
    axes[-1].set_xlabel("Falling table time (ns)")
    fig.suptitle(f"03 Inverse mapping to falling tables: inferred start times disagree by {s['pre_tf_disagree']:.3f} ns", fontweight="bold")
    fig.savefig(OUT / "03_inverse_mapping_to_falling_tables.png", dpi=180)
    plt.close(fig)


def plot_forced_midpoint(data: dict[str, object], s: dict[str, float]) -> None:
    tables = data["tables"]
    assert isinstance(tables, dict)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8.2), sharex=True, constrained_layout=True)
    for ax, table_name, color, label, cur_key, mid_key, err_key in [
        (axes[0], "ku_fall", COL["ku"], "Ku fall", "pre_ku", "pre_ku_at_mid", "pre_ku_mid_error"),
        (axes[1], "kd_fall", COL["kd"], "Kd fall", "pre_kd", "pre_kd_at_mid", "pre_kd_mid_error"),
    ]:
        table = tables[table_name]
        ax.plot(table[:, 0], table[:, 1], color=color, lw=2.0, label=f"{label} table")
        ax.axvline(s["pre_tf_ku"], color=COL["ku"], lw=1.2, ls="--", label="Ku-inferred start" if ax is axes[0] else None)
        ax.axvline(s["pre_tf_kd"], color=COL["kd"], lw=1.2, ls="--", label="Kd-inferred start" if ax is axes[0] else None)
        ax.axvline(s["pre_tf_start"], color=COL["mid"], lw=2.0, label="forced midpoint" if ax is axes[0] else None)
        ax.axhline(s[cur_key], color=color, lw=1.0, ls=":", label="current value" if ax is axes[0] else None)
        ax.plot([s["pre_tf_start"]], [s[mid_key]], "o", color=COL["mid"], ms=7)
        ax.annotate(
            f"midpoint value error = {s[err_key]:+.3f}",
            xy=(s["pre_tf_start"], s[mid_key]),
            xytext=(2.25, 0.72 if ax is axes[0] else 0.22),
            arrowprops={"arrowstyle": "->", "color": COL["mid"]},
            fontsize=10,
        )
        ax.set_ylim(-0.12, 1.08)
        style(ax, "Coefficient")
        ax.legend(loc="best", frameon=False, ncol=3)
    axes[-1].set_xlabel("Falling table time (ns)")
    axes[0].set_title("04 Forced shared midpoint replay cannot satisfy both coefficients", fontweight="bold")
    fig.savefig(OUT / "04_forced_shared_midpoint.png", dpi=180)
    plt.close(fig)


def plot_time_consequence(data: dict[str, object], s: dict[str, float]) -> None:
    h = data["hspice"]
    vm = data["vm"]
    assert isinstance(h, dict) and isinstance(vm, dict)
    ht = to_ns(find_signal(h, "time"))
    vt = to_ns(find_signal(vm, "time"))
    vm_end = float(vt[-1])
    fig, axes = plt.subplots(3, 1, figsize=(11.5, 9), constrained_layout=True, gridspec_kw={"height_ratios": [1.05, 1.05, 0.9]})
    axes[0].plot(ht, find_signal(h, "v(ku)"), color=COL["hspice"], lw=2.0, label="HSPICE Ku reference")
    axes[0].plot(vt, find_signal(vm, "v(xdrv.ku)"), color=COL["actual"], lw=1.5, label="value-match Ku")
    axes[0].plot(vt, find_signal(vm, "v(xdrv.kutarget)"), color=COL["target"], lw=1.3, label="algorithm KuTarget")
    axes[0].annotate(
        "target drives Ku off;\nKu follows in ~1 ps",
        xy=(7.006, val_at(vt, find_signal(vm, "v(xdrv.kutarget)"), 7.006)),
        xytext=(7.30, 0.18),
        arrowprops={"arrowstyle": "->", "color": COL["target"], "lw": 1.4},
        fontsize=10,
        color=COL["target"],
    )
    axes[0].annotate(
        "HSPICE response is delayed;\nits larger motion happens later",
        xy=(7.45, val_at(ht, find_signal(h, "v(ku)"), 7.45)),
        xytext=(7.78, 0.56),
        arrowprops={"arrowstyle": "->", "color": COL["hspice"], "lw": 1.4},
        fontsize=10,
        color=COL["hspice"],
    )
    style(axes[0], "Ku")

    axes[1].plot(ht, find_signal(h, "v(kd)"), color=COL["hspice"], lw=2.0, label="HSPICE Kd reference")
    axes[1].plot(vt, find_signal(vm, "v(xdrv.kd)"), color="#ff7f0e", lw=1.5, label="value-match Kd")
    axes[1].plot(vt, find_signal(vm, "v(xdrv.kdtarget)"), color=COL["target"], lw=1.3, label="algorithm KdTarget")
    axes[1].annotate(
        "target drives Kd on;\nKd follows in ~1 ps",
        xy=(7.006, val_at(vt, find_signal(vm, "v(xdrv.kdtarget)"), 7.006)),
        xytext=(7.30, 0.78),
        arrowprops={"arrowstyle": "->", "color": COL["target"], "lw": 1.4},
        fontsize=10,
        color=COL["target"],
    )
    axes[1].annotate(
        "target steps are internal table-replay\nartifacts, not HSPICE behavior",
        xy=(7.011, val_at(vt, find_signal(vm, "v(xdrv.kdtarget)"), 7.011)),
        xytext=(7.43, 0.42),
        arrowprops={"arrowstyle": "->", "color": COL["gray"], "lw": 1.2},
        fontsize=9.5,
        color=COL["gray"],
    )
    axes[1].annotate(
        "HSPICE Kd continues its delayed\nturn-off/recovery after the early zoom",
        xy=(7.55, val_at(ht, find_signal(h, "v(kd)"), 7.55)),
        xytext=(7.72, -0.12),
        arrowprops={"arrowstyle": "->", "color": COL["hspice"], "lw": 1.4},
        fontsize=10,
        color=COL["hspice"],
    )
    style(axes[1], "Kd")

    ax = axes[2]
    ax.set_title("Why the target is wrong: one midpoint is forced between two incompatible starts", fontsize=12, fontweight="bold")
    y = 0.5
    ax.hlines(y, 0, 4.2, color="#d8dee8", lw=2.0)
    ax.axvspan(s["pre_tf_ku"], s["pre_tf_kd"], color="#f2c94c", alpha=0.22)
    ax.plot([s["pre_tf_ku"]], [y], "o", color=COL["ku"], ms=10, label=f"Ku-inferred start {s['pre_tf_ku']:.3f} ns")
    ax.plot([s["pre_tf_kd"]], [y], "o", color=COL["kd"], ms=10, label=f"Kd-inferred start {s['pre_tf_kd']:.3f} ns")
    ax.plot([s["pre_tf_start"]], [y], "D", color=COL["mid"], ms=9, label=f"forced midpoint {s['pre_tf_start']:.3f} ns")
    ax.annotate(
        f"disagreement = {s['pre_tf_disagree']:.3f} ns",
        xy=(0.5 * (s["pre_tf_ku"] + s["pre_tf_kd"]), y),
        xytext=(1.15, 0.78),
        arrowprops={"arrowstyle": "->", "color": COL["gray"], "lw": 1.3},
        fontsize=11,
    )
    ax.set_xlim(0, 4.2)
    ax.set_ylim(0.25, 0.95)
    ax.set_yticks([])
    ax.set_xlabel("Falling coefficient table time (ns)")
    style(ax)
    ax.legend(loc="lower center", frameon=False, ncol=3)

    for ax in axes[:2]:
        ax.axvline(FALL_NS, color="#111111", lw=1.2)
        ax.axvline(SAMPLE_NS, color=COL["mid"], lw=1.0, ls="--")
        ax.axvline(vm_end, color=COL["actual"], lw=1.1, ls=":")
        ax.axvspan(vm_end, 8.1, color="#f8fafc", alpha=0.72, zorder=-1)
        ax.text(vm_end + 0.015, 0.985, "value-match raw ends", fontsize=8.8, color=COL["actual"], va="top")
        ax.set_xlim(6.95, 8.1)
        ax.legend(loc="best", frameon=False, ncol=3)
    axes[1].set_xlabel("Time (ns)")
    axes[0].set_title("05 Consequence: algorithm targets jump early while HSPICE response is delayed", fontweight="bold")
    fig.savefig(OUT / "05_time_domain_consequence.png", dpi=180)
    plt.close(fig)


def plot_summary(data: dict[str, object], s: dict[str, float]) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2), constrained_layout=True)
    ax.set_axis_off()
    ax.set_title("06 Summary: no single falling-table replay time represents this state", fontweight="bold", pad=18)

    boxes = [
        (0.07, 0.62, 0.24, 0.20, "Before reverse edge", f"Ku={s['pre_ku']:.3f}\nKd={s['pre_kd']:.3f}\nRising table age ~2 ns"),
        (0.39, 0.72, 0.20, 0.14, "Map Ku to fall", f"TF_KU={s['pre_tf_ku']:.3f} ns"),
        (0.39, 0.48, 0.20, 0.14, "Map Kd to fall", f"TF_KD={s['pre_tf_kd']:.3f} ns"),
        (0.68, 0.58, 0.25, 0.20, "Forced average", f"TF_START={s['pre_tf_start']:.3f} ns\nMismatch={s['pre_tf_disagree']:.3f} ns"),
    ]
    for x, y, w, h, title, body in boxes:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="#f8fafc", edgecolor="#334155", linewidth=1.2))
        ax.text(x + 0.015, y + h - 0.045, title, fontsize=12, fontweight="bold", color="#111827")
        ax.text(x + 0.015, y + h - 0.095, body, fontsize=11, color="#111827", va="top")

    arrows = [
        ((0.31, 0.72), (0.39, 0.79), COL["ku"]),
        ((0.31, 0.67), (0.39, 0.55), COL["kd"]),
        ((0.59, 0.79), (0.68, 0.70), COL["ku"]),
        ((0.59, 0.55), (0.68, 0.65), COL["kd"]),
    ]
    for start, end, color in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 2.0, "color": color})

    ax.text(
        0.07,
        0.22,
        "Finding: value-matched replay assumes Ku and Kd can share one replay time.\n"
        "For the 2 ns short-high case, Ku and Kd map to falling-table times more than 1.6 ns apart.\n"
        "That makes the midpoint replay internally inconsistent and leads to jagged targets/timestep collapse.",
        fontsize=12,
        color="#111827",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#fff7ed", "edgecolor": "#f59e0b"},
    )
    fig.savefig(OUT / "06_misalignment_summary.png", dpi=180)
    plt.close(fig)


def write_summary_csv(s: dict[str, float]) -> None:
    fields = list(s.keys())
    with (OUT / "value_match_misalignment_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerow(s)


def write_readme(s: dict[str, float]) -> None:
    lines = [
        "# Value-Matched Replay Misalignment Demo",
        "",
        "This demo explains why `short_pulse_2ns_high` is different from the easier `short_pulse_1ns_high` case.",
        "It uses cached artifacts only: no HSPICE or ngspice simulation is rerun.",
        "",
        "## Core Finding",
        "",
        "- Just before the reverse falling edge, the rising-state coefficients are already mid-transition.",
        f"- On the rising table, the pre-edge values still align: `Ku` maps to `{s['pre_tr_ku']:.3f} ns` and `Kd` maps to `{s['pre_tr_kd']:.3f} ns`.",
        f"- When those same values are mapped onto the falling tables, they split badly: `TF_KU={s['pre_tf_ku']:.3f} ns`, `TF_KD={s['pre_tf_kd']:.3f} ns`, disagreement `{s['pre_tf_disagree']:.3f} ns`.",
        f"- The implementation's own latched diagnostic sample shows the same issue: `TF_KU={s['raw_tf_ku']:.3f} ns`, `TF_KD={s['raw_tf_kd']:.3f} ns`, disagreement `{s['raw_start_disagree']:.3f} ns` near `{SAMPLE_NS:.3f} ns`.",
        "- Therefore a single forced midpoint replay time cannot preserve both coefficients.",
        "",
        "Here `TF` means falling-table time. `TF_KU` is the time on the falling `Ku` table whose coefficient value is closest to the current `Ku`; `TF_KD` is the equivalent time on the falling `Kd` table. The failure is that those two inferred falling-table times are far apart.",
        "",
        "## Figures",
        "",
        "- `01_event_context.png`: full 14 ns input, pad-voltage overlay, and HSPICE/legacy/value-match Ku/Kd. Value-match is shown only through its completed partial raw at 7.25 ns.",
        "- `02_rising_state_snapshot.png`: the pre-edge state is coherent on the rising table.",
        "- `03_inverse_mapping_to_falling_tables.png`: the same state maps to mismatched falling-table start times.",
        "- `04_forced_shared_midpoint.png`: the averaged start time creates coefficient value errors.",
        "- `05_time_domain_consequence.png`: time-domain consequence of the forced midpoint over a longer 6.95-8.10 ns window. `KuTarget`/`KdTarget` are internal value-match algorithm targets, not HSPICE signals. The target steps come from switching the replay argument into the midpoint path. HSPICE looks nearly flat only in the first few tens of ps after the edge because its coefficient response is delayed; the later HSPICE motion is visible in this wider view.",
        "- `06_misalignment_summary.png`: presentation-ready one-slide summary.",
        "- `value_match_misalignment_summary.csv`: numeric values used by the figures.",
        "",
        "## Why `KuTarget` / `KdTarget` Behave That Way",
        "",
        "`KuTarget` and `KdTarget` are not HSPICE quantities. They are internal targets generated by the experimental value-matched pybis subcircuit before the final smoothed `Ku`/`Kd` states follow them.",
        "",
        "In Figure 05 the target and final coefficient traces often look nearly identical because the final states use a very fast `coeff_tau=1 ps` follower. On a nanosecond-scale plot, `Ku`/`Kd` almost immediately sit on top of `KuTarget`/`KdTarget`. They are still both useful: the target shows the algorithm command, while final `Ku`/`Kd` show the actual state that enters the buffer current equation. The brief places where they separate are the discontinuous target jumps that force ngspice into very small timesteps.",
        "",
        "The generated logic is:",
        "",
        "- `VMSTART` is the chosen replay start location on the opposite coefficient table. For a falling-after-rising event, it is the selected starting x-axis time on the falling tables.",
        "- `VMARG = VMSTART + HNX`. `VMARG` is the actual moving x-axis value used to read the replay table. If `VMSTART=2.68 ns` and the new replay has advanced by `0.05 ns`, then `VMARG=2.73 ns`.",
        "- `KDMATCH = falling_Kd_table(VMARG)`.",
        "- `KdTarget = KDMATCH` while value-match mode is active; otherwise it follows legacy `Kd`.",
        "",
        f"In this failed 2 ns case, right after the reverse edge the raw debug values show `VMARG={s['target_7001_vmarg']:.3f} ns` and `KdTarget={s['target_7001_kdtarget']:.3f}` at 7.001 ns, then `VMARG={s['target_7015_vmarg']:.3f} ns` and `KdTarget={s['target_7015_kdtarget']:.3f}` at 7.015 ns. That step/drop is the value-match algorithm switching into an inconsistent midpoint replay path; it is not a physical HSPICE response.",
        "",
        f"HSPICE looks nearly flat in the old tight Figure 05 zoom because only the first 80 ps after the reverse edge were shown. In that early window HSPICE moves from `Ku={s['hspice_7001_ku']:.3f}, Kd={s['hspice_7001_kd']:.3f}` at 7.001 ns to `Ku={s['hspice_7080_ku']:.3f}, Kd={s['hspice_7080_kd']:.3f}` at 7.080 ns. The larger delayed HSPICE motion is visible when the plot extends beyond that early window.",
        "",
        "## Why Figure 05 `Kd` Looks Worse Than Figure 04",
        "",
        "Figure 04 is a static explanation: it freezes one pre-edge coefficient state, maps that state onto the falling `Ku` and `Kd` tables, and shows that no single falling-table start time satisfies both. The purple midpoint in Figure 04 is the conceptual average of the two inferred falling-table times.",
        "",
        "Figure 05 is the actual generated ngspice value-match logic. That logic has two extra time-domain effects that Figure 04 intentionally does not show:",
        "",
        "- The sample nodes are driven by the edge pulse, not by a perfect mathematical one-shot. During the reverse-edge window, `KUSAMP`/`KDSAMP` can continue moving while `Ku`/`Kd` are already reacting.",
        "- The replay argument is `VMARG = VMSTART + elapsed_time`. Around the delayed edge-timer reset, `VMARG` makes narrow backward jumps. Because `KdTarget = falling_Kd_table(VMARG)`, those `VMARG` jumps become `KdTarget` spikes.",
        "",
        "The table below is the practical story from the partial raw file:",
        "",
        "| time | `KDSAMP` | `TF_START` | `VMSTART` | `VMARG` | `KdTarget` | meaning |",
        "|---:|---:|---:|---:|---:|---:|---|",
        "| `7.001 ns` | `0.352` | `1.769 ns` | `1.674 ns` | `3.674 ns` | `1.002` | sample and timer are still moving; replay reads far into the falling `Kd` table |",
        "| `7.010 ns` | `1.002` | `2.682 ns` | `2.682 ns` | `4.682 ns` | `1.002` | the algorithm has re-sampled its own Kd response, so the selected start moved later |",
        "| `7.015 ns` | `1.002` | `2.682 ns` | `2.682 ns` | `2.692 ns` | `0.486` | the elapsed-time part resets, so `VMARG` jumps backward and `KdTarget` drops |",
        "| `7.080 ns` | `1.002` | `2.682 ns` | `2.682 ns` | `2.752 ns` | `0.625` | now `VMARG` advances forward again, so `KdTarget` rises along the steep table |",
        "",
        "This hurts `Kd` much more than `Ku` because of the table shapes. In the falling table, `Ku` is already nearly flat/off over the later replay region, so argument jitter barely changes `KuTarget`. But `Kd` is on a steep rising part of its falling table around the replay region, so the same small `VMARG` jumps create large `KdTarget` changes. Therefore `Ku` looks like the clean Figure 04 story, while `Kd` exposes both problems: bad midpoint assumption plus imperfect time-domain sampling/replay control.",
        "",
        "## Interpretation",
        "",
        "This is not a throwaway failed run. It shows that table retiming can help when the pulse is so short that the coefficients are still near an endpoint, but it breaks once the buffer is genuinely mid-transition. The correct next model likely needs independent, continuous Ku/Kd or hidden gate-state dynamics rather than one shared replay time.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_dir(OUT)
    data = load_data()
    summary = build_summary(data)
    write_summary_csv(summary)
    plot_event_context(data, summary)
    plot_rising_snapshot(data, summary)
    plot_inverse_mapping(data, summary)
    plot_forced_midpoint(data, summary)
    plot_time_consequence(data, summary)
    plot_summary(data, summary)
    write_readme(summary)
    print(f"OUT={OUT}")


if __name__ == "__main__":
    main()
