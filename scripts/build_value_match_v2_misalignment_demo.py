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


STUDY = ROOT / "results" / "io_buf_value_matched_replay_v2_2026-06-26"
OUT = ROOT / "results" / "io_buf_value_match_v2_misalignment_demo_2026-06-26"
CASE_ID = "short_pulse_2ns_high"
RISE_NS = 5.0
FALL_NS = 7.0

COL = {
    "input": "#222222",
    "hspice": "#0057b8",
    "legacy": "#ff7f0e",
    "v2": "#6f2dbd",
    "ku": "#0072b2",
    "kd": "#d55e00",
    "mid": "#6f2dbd",
    "target": "#e7298a",
    "gray": "#6b7280",
    "timer": "#159947",
    "elapsed": "#00a6d6",
    "bad": "#b91c1c",
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def find_signal(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    return redo.find_signal(data, name)


def to_ns(signal: np.ndarray) -> np.ndarray:
    return redo.to_ns(signal)


def val_at(t: np.ndarray, y: np.ndarray, x: float) -> float:
    return float(np.interp(x, t, y))


def first_cross(t: np.ndarray, y: np.ndarray, level: float = 0.5) -> float:
    idx = np.flatnonzero(y > level)
    return float(t[int(idx[0])]) if len(idx) else float("nan")


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
    try:
        payload = line.split("),", 2)[2].split("),", 1)[1].rsplit(")", 1)[0]
    except IndexError as exc:
        raise ValueError(f"could not parse PWL payload for {source}") from exc
    nums = [float(item) for item in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", payload)]
    if len(nums) % 2:
        raise ValueError(f"odd number of PWL values for {source}")
    arr = np.asarray(nums, dtype=float).reshape(-1, 2)
    return arr[np.argsort(arr[:, 0])]


def interp_table(table: np.ndarray, x: float) -> float:
    return float(np.interp(x, table[:, 0], table[:, 1]))


def nearest_time(table: np.ndarray, value: float) -> tuple[float, float]:
    idx = int(np.nanargmin(np.abs(table[:, 1] - value)))
    return float(table[idx, 0]), float(table[idx, 1])


def read_metrics() -> dict[str, str]:
    metrics = STUDY / "candidate_metrics.csv"
    with metrics.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["case_id"] == CASE_ID and row["flow"] == "ngspice_v2_balanced":
                return row
    raise RuntimeError("ngspice_v2_balanced metrics row not found")


def load_data() -> dict[str, object]:
    case_dir = STUDY / "cases" / CASE_ID
    hspice = parse_hspice_tr0(case_dir / "hspice_native_ibis" / f"{CASE_ID}_hspice_native_ibis.tr0")
    legacy = parse_ngspice_raw(case_dir / "ngspice_legacy" / f"{CASE_ID}_ngspice_legacy.raw")
    v2 = parse_ngspice_raw(case_dir / "ngspice_v2_balanced" / f"{CASE_ID}_ngspice_v2_balanced.raw")
    subckt = STUDY / "common" / "v2_balanced" / "driver_OutputInput_Typical.sub"
    tables = {
        "ku_rise": parse_table(subckt, "HKUR0"),
        "kd_rise": parse_table(subckt, "HKDR0"),
        "ku_fall": parse_table(subckt, "HKUF0"),
        "kd_fall": parse_table(subckt, "HKDF0"),
    }
    return {"hspice": hspice, "legacy": legacy, "v2": v2, "tables": tables, "metrics": read_metrics()}


def build_summary(data: dict[str, object]) -> dict[str, float | str]:
    v2 = data["v2"]
    hspice = data["hspice"]
    assert isinstance(v2, dict)
    assert isinstance(hspice, dict)
    vt = to_ns(find_signal(v2, "time"))
    ht = to_ns(find_signal(hspice, "time"))
    hmatch = find_signal(v2, "v(xdrv.hvmatch)")
    vmsample = find_signal(v2, "v(xdrv.vmsample)")
    latch = find_signal(v2, "v(xdrv.vmlatchpulse)")
    activate_ns = first_cross(vt, hmatch, 0.5)
    latch_ns = first_cross(vt, latch, 0.5)
    sample_ns = first_cross(vt, vmsample, 0.5)
    kupre = find_signal(v2, "v(xdrv.kupre)")
    kdpre = find_signal(v2, "v(xdrv.kdpre)")
    summary: dict[str, float | str] = {
        "case_id": CASE_ID,
        "fall_ns": FALL_NS,
        "sample_ns": sample_ns,
        "latch_ns": latch_ns,
        "activate_ns": activate_ns,
        "pre_ku": val_at(vt, find_signal(v2, "v(xdrv.ku)"), FALL_NS),
        "pre_kd": val_at(vt, find_signal(v2, "v(xdrv.kd)"), FALL_NS),
        "sample_source_kupre": val_at(vt, kupre, sample_ns),
        "sample_source_kdpre": val_at(vt, kdpre, sample_ns),
        "sample_kusamp": val_at(vt, find_signal(v2, "v(xdrv.kusamp)"), activate_ns),
        "sample_kdsamp": val_at(vt, find_signal(v2, "v(xdrv.kdsamp)"), activate_ns),
        "tf_ku": val_at(vt, find_signal(v2, "v(xdrv.tf_ku)"), activate_ns),
        "tf_kd": val_at(vt, find_signal(v2, "v(xdrv.tf_kd)"), activate_ns),
        "tf_start": val_at(vt, find_signal(v2, "v(xdrv.tf_start)"), activate_ns),
        "start_disagree": val_at(vt, find_signal(v2, "v(xdrv.start_disagree)"), activate_ns),
        "vmstart_latch": val_at(vt, find_signal(v2, "v(xdrv.vmstart_latch)"), activate_ns),
        "vmarg_at_activate": val_at(vt, find_signal(v2, "v(xdrv.vmarg)"), activate_ns),
        "vmarg_8ns": val_at(vt, find_signal(v2, "v(xdrv.vmarg)"), 8.0),
        "ku_peak": float(np.nanmax(find_signal(v2, "v(xdrv.ku)"))),
        "kd_min": float(np.nanmin(find_signal(v2, "v(xdrv.kd)"))),
        "hspice_ku_peak": float(np.nanmax(find_signal(hspice, "v(ku)"))),
        "hspice_kd_min": float(np.nanmin(find_signal(hspice, "v(kd)"))),
    }
    tables = data["tables"]
    assert isinstance(tables, dict)
    sample_ku = float(summary["sample_kusamp"])
    sample_kd = float(summary["sample_kdsamp"])
    tr_ku, tr_ku_val = nearest_time(tables["ku_rise"], sample_ku)
    tr_kd, tr_kd_val = nearest_time(tables["kd_rise"], sample_kd)
    tf_ku, tf_ku_val = nearest_time(tables["ku_fall"], sample_ku)
    tf_kd, tf_kd_val = nearest_time(tables["kd_fall"], sample_kd)
    tf_start = 0.5 * (tf_ku + tf_kd)
    summary.update(
        {
            "table_tr_ku": tr_ku,
            "table_tr_kd": tr_kd,
            "table_tr_disagree": abs(tr_ku - tr_kd),
            "table_tf_ku": tf_ku,
            "table_tf_kd": tf_kd,
            "table_tf_start": tf_start,
            "table_tf_disagree": abs(tf_ku - tf_kd),
            "table_ku_at_tf": tf_ku_val,
            "table_kd_at_tf": tf_kd_val,
            "table_ku_at_mid": interp_table(tables["ku_fall"], tf_start),
            "table_kd_at_mid": interp_table(tables["kd_fall"], tf_start),
            "table_ku_mid_error": interp_table(tables["ku_fall"], tf_start) - sample_ku,
            "table_kd_mid_error": interp_table(tables["kd_fall"], tf_start) - sample_kd,
            "sample_source_ku_error": sample_ku - float(summary["sample_source_kupre"]),
            "sample_source_kd_error": sample_kd - float(summary["sample_source_kdpre"]),
        }
    )
    metrics = data["metrics"]
    assert isinstance(metrics, dict)
    for key in [
        "pad_active_rmse_v",
        "ku_active_rmse",
        "kd_active_rmse",
        "pad_peak_v",
        "vmarg_match_active_max_negative_step",
        "start_disagree_max",
    ]:
        summary[f"metric_{key}"] = float(metrics[key])
    return summary


def plot_event_context(data: dict[str, object], s: dict[str, float | str]) -> None:
    h = data["hspice"]
    legacy = data["legacy"]
    v2 = data["v2"]
    assert isinstance(h, dict) and isinstance(legacy, dict) and isinstance(v2, dict)
    ht = to_ns(find_signal(h, "time"))
    lt = to_ns(find_signal(legacy, "time"))
    vt = to_ns(find_signal(v2, "time"))

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(12.5, 10.5),
        sharex=True,
        gridspec_kw={"height_ratios": [0.65, 1.05, 1.05, 1.05]},
        constrained_layout=True,
    )
    axes[0].plot(vt, find_signal(v2, "v(in_dig)") / 3.3, color=COL["input"], lw=2.2, label="input command")
    axes[0].fill_between([RISE_NS, FALL_NS], [1, 1], [0, 0], color="#eef2ff", alpha=0.8)
    axes[0].text(5.65, 0.50, "2 ns high pulse", fontsize=12, fontweight="bold", color="#1f2937")
    axes[0].set_ylim(-0.08, 1.13)
    style(axes[0], "Input")

    axes[1].plot(ht, find_signal(h, "v(pad_ibis)"), color=COL["hspice"], lw=2.0, label="HSPICE native IBIS")
    axes[1].plot(lt, find_signal(legacy, "v(pad)"), color=COL["legacy"], lw=1.5, label="legacy pybis")
    axes[1].plot(vt, find_signal(v2, "v(pad)"), color=COL["v2"], lw=1.8, label="v2 value-match")
    style(axes[1], "Pad (V)")

    axes[2].plot(ht, find_signal(h, "v(ku)"), color=COL["hspice"], lw=2.0, label="HSPICE Ku")
    axes[2].plot(lt, find_signal(legacy, "v(xdrv.ku)"), color=COL["legacy"], lw=1.3, label="legacy Ku")
    axes[2].plot(vt, find_signal(v2, "v(xdrv.ku)"), color=COL["v2"], lw=1.7, label="v2 Ku")
    axes[2].plot([FALL_NS], [s["pre_ku"]], "s", color=COL["bad"], ms=7, label="pre-edge Ku")
    axes[2].plot([s["activate_ns"]], [s["sample_kusamp"]], "o", color=COL["v2"], ms=7)
    axes[2].annotate(
        f"pre-edge Ku={s['pre_ku']:.3f}",
        xy=(FALL_NS, float(s["pre_ku"])),
        xytext=(6.00, 0.28),
        arrowprops={"arrowstyle": "->", "color": COL["bad"], "lw": 1.3},
        fontsize=10,
        color=COL["bad"],
    )
    axes[2].annotate(
        f"v2 latched Ku={s['sample_kusamp']:.3f}",
        xy=(float(s["activate_ns"]), float(s["sample_kusamp"])),
        xytext=(7.22, 0.48),
        arrowprops={"arrowstyle": "->", "color": COL["v2"], "lw": 1.3},
        fontsize=10,
        color=COL["v2"],
    )
    style(axes[2], "Ku")

    axes[3].plot(ht, find_signal(h, "v(kd)"), color=COL["hspice"], lw=2.0, label="HSPICE Kd")
    axes[3].plot(lt, find_signal(legacy, "v(xdrv.kd)"), color=COL["legacy"], lw=1.3, label="legacy Kd")
    axes[3].plot(vt, find_signal(v2, "v(xdrv.kd)"), color=COL["v2"], lw=1.7, label="v2 Kd")
    axes[3].plot([FALL_NS], [s["pre_kd"]], "s", color=COL["bad"], ms=7, label="pre-edge Kd")
    axes[3].plot([s["activate_ns"]], [s["sample_kdsamp"]], "o", color=COL["v2"], ms=7)
    axes[3].annotate(
        f"pre-edge Kd={s['pre_kd']:.3f}",
        xy=(FALL_NS, float(s["pre_kd"])),
        xytext=(6.00, 0.18),
        arrowprops={"arrowstyle": "->", "color": COL["bad"], "lw": 1.3},
        fontsize=10,
        color=COL["bad"],
    )
    axes[3].annotate(
        f"v2 latched Kd={s['sample_kdsamp']:.3f}",
        xy=(float(s["activate_ns"]), float(s["sample_kdsamp"])),
        xytext=(7.22, 0.33),
        arrowprops={"arrowstyle": "->", "color": COL["v2"], "lw": 1.3},
        fontsize=10,
        color=COL["v2"],
    )
    style(axes[3], "Kd")

    for ax in axes:
        ax.axvline(RISE_NS, color=COL["gray"], lw=1.1)
        ax.axvline(FALL_NS, color="#111111", lw=1.8)
        ax.axvline(float(s["activate_ns"]), color=COL["v2"], lw=1.3, ls="--")
        ax.text(RISE_NS + 0.01, ax.get_ylim()[1] * 0.88, "rise", color=COL["gray"], fontsize=10)
        ax.text(FALL_NS + 0.01, ax.get_ylim()[1] * 0.88, "fall/retrigger", color="#111111", fontsize=10)
        ax.set_xlim(4.92, 13.0)
        ax.legend(loc="best", frameon=False, ncol=3)
    axes[-1].set_xlabel("Time (ns)")
    axes[0].set_title("01 Event context: v2 samples the pre-edge state, but replay still misaligns", fontweight="bold")
    fig.savefig(OUT / "01_event_context.png", dpi=180)
    plt.close(fig)


def plot_rising_snapshot(data: dict[str, object], s: dict[str, float | str]) -> None:
    tables = data["tables"]
    assert isinstance(tables, dict)
    fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)
    ax.plot(tables["ku_rise"][:, 0], tables["ku_rise"][:, 1], color=COL["ku"], lw=2.0, label="Ku rise table")
    ax.plot(tables["kd_rise"][:, 0], tables["kd_rise"][:, 1], color=COL["kd"], lw=2.0, label="Kd rise table")
    for xkey, ykey, color, label in [
        ("table_tr_ku", "sample_kusamp", COL["ku"], "Ku maps to rise time"),
        ("table_tr_kd", "sample_kdsamp", COL["kd"], "Kd maps to rise time"),
    ]:
        ax.axvline(float(s[xkey]), color=color, lw=1.5, ls="--")
        ax.axhline(float(s[ykey]), color=color, lw=1.0, ls=":")
        ax.plot([s[xkey]], [s[ykey]], "o", color=color, ms=7, label=f"{label}: {s[xkey]:.3f} ns")
        ax.text(0.08, float(s[ykey]) + (0.035 if "ku" in ykey else -0.060), f"{ykey.replace('sample_', '').upper()}={s[ykey]:.3f}", color=color, fontsize=11, fontweight="bold")
    ax.annotate(
        f"Latch now samples the intended pre-edge source:\nKu error={s['sample_source_ku_error']:+.3f}, Kd error={s['sample_source_kd_error']:+.3f}",
        xy=(0.5 * (float(s["table_tr_ku"]) + float(s["table_tr_kd"])), 0.58),
        xytext=(2.35, 0.78),
        arrowprops={"arrowstyle": "->", "color": COL["gray"]},
        fontsize=11,
    )
    ax.set_xlim(0, 4.2)
    ax.set_ylim(-0.12, 1.08)
    ax.set_xlabel("Rising table time (ns)")
    ax.set_ylabel("Coefficient")
    ax.set_title("02 V2 latch snapshot: sampled state is now pre-edge-like", fontweight="bold")
    style(ax)
    ax.legend(loc="best", frameon=False)
    fig.savefig(OUT / "02_rising_state_snapshot.png", dpi=180)
    plt.close(fig)


def plot_inverse_mapping(data: dict[str, object], s: dict[str, float | str]) -> None:
    tables = data["tables"]
    assert isinstance(tables, dict)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8.2), sharex=True, constrained_layout=True)
    axes[0].plot(tables["ku_fall"][:, 0], tables["ku_fall"][:, 1], color=COL["ku"], lw=2.0, label="Ku fall table")
    axes[0].axhline(float(s["sample_kusamp"]), color=COL["ku"], lw=1.0, ls=":")
    axes[0].axvline(float(s["table_tf_ku"]), color=COL["ku"], lw=1.5, ls="--")
    axes[0].plot([s["table_tf_ku"]], [s["table_ku_at_tf"]], "o", color=COL["ku"], ms=7)
    axes[0].text(0.06, float(s["sample_kusamp"]) + 0.035, f"Ku_latch={s['sample_kusamp']:.3f}", color=COL["ku"], fontsize=11, fontweight="bold")
    axes[0].annotate(f"Ku-inferred falling start = {s['table_tf_ku']:.3f} ns", xy=(float(s["table_tf_ku"]), float(s["sample_kusamp"])), xytext=(0.15, 0.55), arrowprops={"arrowstyle": "->", "color": COL["ku"]})
    style(axes[0], "Ku")

    axes[1].plot(tables["kd_fall"][:, 0], tables["kd_fall"][:, 1], color=COL["kd"], lw=2.0, label="Kd fall table")
    axes[1].axhline(float(s["sample_kdsamp"]), color=COL["kd"], lw=1.0, ls=":")
    axes[1].axvline(float(s["table_tf_kd"]), color=COL["kd"], lw=1.5, ls="--")
    axes[1].plot([s["table_tf_kd"]], [s["table_kd_at_tf"]], "o", color=COL["kd"], ms=7)
    axes[1].text(0.06, float(s["sample_kdsamp"]) + 0.035, f"Kd_latch={s['sample_kdsamp']:.3f}", color=COL["kd"], fontsize=11, fontweight="bold")
    axes[1].annotate(f"Kd-inferred falling start = {s['table_tf_kd']:.3f} ns", xy=(float(s["table_tf_kd"]), float(s["sample_kdsamp"])), xytext=(2.45, 0.34), arrowprops={"arrowstyle": "->", "color": COL["kd"]})
    style(axes[1], "Kd")

    for ax in axes:
        ax.axvspan(float(s["table_tf_ku"]), float(s["table_tf_kd"]), color="#f2c94c", alpha=0.18)
        ax.legend(loc="best", frameon=False)
        ax.set_xlim(0, 4.2)
        ax.set_ylim(-0.12, 1.08)
    axes[-1].set_xlabel("Falling table time (ns)")
    fig.suptitle(f"03 V2 inverse mapping: falling-table starts disagree by {s['table_tf_disagree']:.3f} ns", fontweight="bold")
    fig.savefig(OUT / "03_inverse_mapping_to_falling_tables.png", dpi=180)
    plt.close(fig)


def plot_forced_midpoint(data: dict[str, object], s: dict[str, float | str]) -> None:
    tables = data["tables"]
    assert isinstance(tables, dict)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8.2), sharex=True, constrained_layout=True)
    for ax, table_name, color, label, cur_key, mid_key, err_key in [
        (axes[0], "ku_fall", COL["ku"], "Ku fall", "sample_kusamp", "table_ku_at_mid", "table_ku_mid_error"),
        (axes[1], "kd_fall", COL["kd"], "Kd fall", "sample_kdsamp", "table_kd_at_mid", "table_kd_mid_error"),
    ]:
        table = tables[table_name]
        ax.plot(table[:, 0], table[:, 1], color=color, lw=2.0, label=f"{label} table")
        ax.axvline(float(s["table_tf_ku"]), color=COL["ku"], lw=1.2, ls="--", label="Ku-inferred start" if ax is axes[0] else None)
        ax.axvline(float(s["table_tf_kd"]), color=COL["kd"], lw=1.2, ls="--", label="Kd-inferred start" if ax is axes[0] else None)
        ax.axvline(float(s["table_tf_start"]), color=COL["mid"], lw=2.0, label="forced shared start" if ax is axes[0] else None)
        ax.axhline(float(s[cur_key]), color=color, lw=1.0, ls=":", label="latched value" if ax is axes[0] else None)
        ax.plot([s["table_tf_start"]], [s[mid_key]], "o", color=COL["mid"], ms=7)
        ax.annotate(
            f"shared-start value error = {s[err_key]:+.3f}",
            xy=(float(s["table_tf_start"]), float(s[mid_key])),
            xytext=(2.18, 0.72 if ax is axes[0] else 0.22),
            arrowprops={"arrowstyle": "->", "color": COL["mid"]},
            fontsize=10,
        )
        ax.set_ylim(-0.12, 1.08)
        style(ax, "Coefficient")
        ax.legend(loc="best", frameon=False, ncol=3)
    axes[-1].set_xlabel("Falling table time (ns)")
    axes[0].set_title("04 Forced shared replay start cannot satisfy Ku and Kd simultaneously", fontweight="bold")
    fig.savefig(OUT / "04_forced_shared_midpoint.png", dpi=180)
    plt.close(fig)


def plot_time_consequence(data: dict[str, object], s: dict[str, float | str]) -> None:
    h = data["hspice"]
    v2 = data["v2"]
    assert isinstance(h, dict) and isinstance(v2, dict)
    ht = to_ns(find_signal(h, "time"))
    vt = to_ns(find_signal(v2, "time"))
    fig, axes = plt.subplots(4, 1, figsize=(11.5, 10.5), sharex=True, constrained_layout=True)

    axes[0].plot(vt, find_signal(v2, "v(xdrv.vmsample)"), color=COL["ku"], lw=1.4, label="VMSAMPLE one-shot")
    axes[0].plot(vt, find_signal(v2, "v(xdrv.vmlatchpulse)"), color=COL["kd"], lw=1.4, label="VMLATCHPULSE")
    axes[0].plot(vt, find_signal(v2, "v(xdrv.hprehold)"), color=COL["timer"], lw=1.8, label="HPREHOLD target hold")
    axes[0].plot(vt, find_signal(v2, "v(xdrv.hvmatch)"), color=COL["v2"], lw=1.8, label="HVMATCH active")
    axes[0].set_ylim(-0.08, 1.12)
    style(axes[0], "Logic")

    axes[1].plot(vt, find_signal(v2, "v(xdrv.vmstart_latch)"), color=COL["mid"], lw=1.7, label="VMSTART_LATCH")
    axes[1].plot(vt, find_signal(v2, "v(xdrv.vmelapsed)"), color=COL["elapsed"], lw=1.5, label="VMELAPSED")
    axes[1].plot(vt, find_signal(v2, "v(xdrv.vmarg)"), color=COL["timer"], lw=1.8, label="VMARG = VMSTART_LATCH + VMELAPSED")
    axes[1].annotate(
        "active VMARG backstep = 0 ns",
        xy=(7.45, val_at(vt, find_signal(v2, "v(xdrv.vmarg)"), 7.45)),
        xytext=(7.75, 4.8),
        arrowprops={"arrowstyle": "->", "color": COL["timer"]},
        fontsize=10,
        color=COL["timer"],
    )
    style(axes[1], "Table time (ns)")

    axes[2].plot(ht, find_signal(h, "v(ku)"), color=COL["hspice"], lw=2.0, label="HSPICE Ku")
    axes[2].plot(vt, find_signal(v2, "v(xdrv.ku)"), color=COL["v2"], lw=1.6, label="v2 Ku")
    axes[2].plot(vt, find_signal(v2, "v(xdrv.kutarget)"), color=COL["target"], lw=1.1, label="v2 KuTarget")
    axes[2].annotate(
        f"HSPICE peak Ku={s['hspice_ku_peak']:.3f}; v2 peak Ku={s['ku_peak']:.3f}",
        xy=(7.3, 0.9),
        xytext=(7.55, 0.52),
        arrowprops={"arrowstyle": "->", "color": COL["bad"]},
        fontsize=10,
        color=COL["bad"],
    )
    style(axes[2], "Ku")

    axes[3].plot(ht, find_signal(h, "v(kd)"), color=COL["hspice"], lw=2.0, label="HSPICE Kd")
    axes[3].plot(vt, find_signal(v2, "v(xdrv.kd)"), color=COL["v2"], lw=1.6, label="v2 Kd")
    axes[3].plot(vt, find_signal(v2, "v(xdrv.kdtarget)"), color=COL["target"], lw=1.1, label="v2 KdTarget")
    style(axes[3], "Kd")

    for ax in axes:
        ax.axvline(FALL_NS, color="#111111", lw=1.2)
        ax.axvline(float(s["activate_ns"]), color=COL["v2"], lw=1.2, ls="--")
        ax.set_xlim(6.95, 8.4)
        ax.legend(loc="best", frameon=False, ncol=3)
    axes[-1].set_xlabel("Time (ns)")
    axes[0].set_title("05 V2 consequence: target hold is fixed, but table retiming remains coefficient-wrong", fontweight="bold")
    fig.savefig(OUT / "05_time_domain_consequence.png", dpi=180)
    plt.close(fig)


def plot_summary(s: dict[str, float | str]) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2), constrained_layout=True)
    ax.set_axis_off()
    ax.set_title("06 V2 summary: bug fixed, shared-start assumption still fails", fontweight="bold", pad=18)
    boxes = [
        (0.05, 0.62, 0.25, 0.20, "True pre-edge", f"Ku={s['pre_ku']:.3f}\nKd={s['pre_kd']:.3f}\nat fall={s['fall_ns']:.3f} ns"),
        (0.05, 0.36, 0.25, 0.18, "V2 latch", f"Ku={s['sample_kusamp']:.3f}\nKd={s['sample_kdsamp']:.3f}\nsource error={s['sample_source_ku_error']:+.3f}/{s['sample_source_kd_error']:+.3f}"),
        (0.37, 0.72, 0.20, 0.14, "Map Ku to fall", f"TF_KU={s['table_tf_ku']:.3f} ns"),
        (0.37, 0.48, 0.20, 0.14, "Map Kd to fall", f"TF_KD={s['table_tf_kd']:.3f} ns"),
        (0.68, 0.62, 0.25, 0.20, "V2 result", f"VMARG backstep=0 ns\nKu peak={s['ku_peak']:.3f}\nstatus=AMBIGUOUS"),
    ]
    for x, y, w, h, title, body in boxes:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="#f8fafc", edgecolor="#334155", linewidth=1.2))
        ax.text(x + 0.015, y + h - 0.045, title, fontsize=12, fontweight="bold", color="#111827")
        ax.text(x + 0.015, y + h - 0.095, body, fontsize=11, color="#111827", va="top")
    for start, end, color in [
        ((0.30, 0.72), (0.37, 0.79), COL["ku"]),
        ((0.30, 0.67), (0.37, 0.55), COL["kd"]),
        ((0.57, 0.79), (0.68, 0.73), COL["ku"]),
        ((0.57, 0.55), (0.68, 0.68), COL["kd"]),
    ]:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 2.0, "color": color})
    ax.text(
        0.06,
        0.22,
        "Finding: v2 fixes the replay-timer bug and the pre-edge sampling bug. The remaining failure is not numerical.\n"
        f"The corrected latch captures a pre-edge-like state, but that state maps to falling-table starts {s['table_tf_disagree']:.3f} ns apart.\n"
        "That is why v2 completes the 2 ns case but still gets a VALUE_MATCH_AMBIGUOUS classification.",
        fontsize=12,
        color="#111827",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#fff7ed", "edgecolor": "#f59e0b"},
    )
    fig.savefig(OUT / "06_misalignment_summary.png", dpi=180)
    plt.close(fig)


def write_summary_csv(s: dict[str, float | str]) -> None:
    with (OUT / "value_match_v2_misalignment_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(s.keys()))
        writer.writeheader()
        writer.writerow(s)


def write_readme(s: dict[str, float | str]) -> None:
    lines = [
        "# Value-Matched Replay v2 Misalignment Demo",
        "",
        "This is the v2 version of `io_buf_value_match_misalignment_demo_2026-06-25`.",
        "It uses cached/generated artifacts only; no HSPICE or ngspice simulation is rerun.",
        "",
        "## Core Finding",
        "",
        "- V2 fixes the confirmed v1 timer/latch bug: active `VMARG` backstep is `0 ns`.",
        "- V2 completes `short_pulse_2ns_high`, while v1 value-match had a numeric failure.",
        f"- V2 now latches a pre-edge-like coefficient state. At the falling edge the coefficient state is about `Ku={s['pre_ku']:.3f}`, `Kd={s['pre_kd']:.3f}`; the v2 latch captures `Ku={s['sample_kusamp']:.3f}`, `Kd={s['sample_kdsamp']:.3f}` with source errors `{s['sample_source_ku_error']:+.3f}` / `{s['sample_source_kd_error']:+.3f}`.",
        f"- That latched state is still incompatible with one shared falling-table replay start: `TF_KU={s['table_tf_ku']:.3f} ns`, `TF_KD={s['table_tf_kd']:.3f} ns`, disagreement `{s['table_tf_disagree']:.3f} ns`.",
        f"- Coefficient result remains wrong: v2 `Ku` peak is `{s['ku_peak']:.3f}` while HSPICE native IBIS peaks at `{s['hspice_ku_peak']:.3f}` for this 2 ns case.",
        "- Therefore the implementation bugs are fixed, but value-matched table replay is still not a good short-pulse model.",
        "",
        "## Figures",
        "",
        "- `01_event_context.png`: same context style as the old demo: input, pad, Ku, and Kd overlays.",
        "- `02_rising_state_snapshot.png`: the corrected v2-latched state, with explicit source-error annotation.",
        "- `03_inverse_mapping_to_falling_tables.png`: the same state maps to badly separated falling-table start times.",
        "- `04_forced_shared_midpoint.png`: a single shared replay start creates coefficient value errors.",
        "- `05_time_domain_consequence.png`: v2 hold/timer diagnostics plus Ku/Kd consequence. This plot shows the important distinction: target hold and `VMARG` are now stable, but the coefficients are still wrong.",
        "- `06_misalignment_summary.png`: one-slide presentation summary.",
        "- `value_match_v2_misalignment_summary.csv`: numeric values used by the figures.",
        "",
        "## Interpretation",
        "",
        "V2 did what it was supposed to do as a diagnostic: it separated implementation bugs from a real modeling limitation.",
        "The old v1 failure had a timer/latch bug, and the first v2 demo still sampled after the legacy replay path had switched.",
        "The corrected v2 result removes the active `VMARG` backstep, keeps the target on the pending state until match activation, and samples a pre-edge-like state. What remains is the important limitation: that state still maps to incompatible Ku/Kd falling-table start times.",
        "",
        "That means the next algorithm should not keep trying to force one replay time onto both coefficients.",
        "A better direction is an independent hidden-state or gate-charge model where Ku and Kd each carry their own continuous state.",
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
    plot_summary(summary)
    write_readme(summary)
    print(f"OUT={OUT}")


if __name__ == "__main__":
    main()
