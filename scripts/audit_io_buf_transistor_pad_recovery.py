from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import parse_hspice_tr0  # noqa: E402
import run_io_buf_value_matched_replay_v2 as base  # noqa: E402


RESULT_ROOT = ROOT / "results" / "io_buf_two_state_gate_model_2026-06-30"
CASES_DIR = RESULT_ROOT / "cases"
OUT_DIR = RESULT_ROOT / "reference_truth_audit" / "pad_recovery_timing"
SHORT_HIGH_CASES = [
    "short_pulse_500ps_high",
    "short_pulse_1ns_high",
    "short_pulse_2ns_high",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def t_ns(data: dict[str, np.ndarray]) -> np.ndarray:
    t = np.asarray(data["time"], dtype=float)
    return t * 1e9 if np.nanmax(t) < 1e-3 else t


def sig(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    lower = {key.lower(): key for key in data}
    for name in names:
        key = lower.get(name.lower())
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(names)


def load_hspice(case_id: str, flow: str) -> dict[str, np.ndarray]:
    path = CASES_DIR / case_id / flow / f"{case_id}_{flow}.tr0"
    if not path.exists():
        raise FileNotFoundError(path)
    return parse_hspice_tr0(path)


def crossing_time(
    t: np.ndarray,
    y: np.ndarray,
    level: float,
    start_ns: float,
    direction: str,
) -> float:
    mask = (t >= start_ns) & np.isfinite(y)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(y[mask], dtype=float)
    if len(tt) < 2:
        return float("nan")
    d = yy - level
    if direction == "fall":
        idx = np.where((d[:-1] >= 0.0) & (d[1:] < 0.0))[0]
    elif direction == "rise":
        idx = np.where((d[:-1] <= 0.0) & (d[1:] > 0.0))[0]
    else:
        raise ValueError(direction)
    if len(idx) == 0:
        return float("nan")
    i = int(idx[0])
    if yy[i + 1] == yy[i]:
        return float(tt[i])
    return float(tt[i] + (level - yy[i]) * (tt[i + 1] - tt[i]) / (yy[i + 1] - yy[i]))


def tail_median(t: np.ndarray, y: np.ndarray, start_ns: float, end_ns: float) -> float:
    mask = (t >= start_ns) & (t <= end_ns) & np.isfinite(y)
    vals = y[mask]
    return float(np.median(vals)) if len(vals) else float("nan")


def pad_recovery_markers(case: base.StudyCase, t: np.ndarray, pad: np.ndarray) -> dict[str, float | str]:
    _, reverse_ns = base.command_times(case)
    active_end_ns = max(end for _, end in base.transition_windows(case))
    tail_start_ns = max(reverse_ns, active_end_ns - max(0.35, 0.15 * (active_end_ns - reverse_ns)))
    final_v = tail_median(t, pad, tail_start_ns, active_end_ns)

    mask = (t >= reverse_ns) & (t <= active_end_ns) & np.isfinite(pad)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(pad[mask], dtype=float)
    if len(tt) < 8 or not math.isfinite(final_v):
        return {
            "pad_final_v": final_v,
            "pad_peak_v": float("nan"),
            "pad_peak_time_ns": float("nan"),
            "pad_peak_from_reverse_ns": float("nan"),
            "pad_fall_90_ns": float("nan"),
            "pad_fall_50_ns": float("nan"),
            "pad_fall_10_ns": float("nan"),
            "pad_fall_90_from_reverse_ns": float("nan"),
            "pad_fall_50_from_reverse_ns": float("nan"),
            "pad_fall_10_from_reverse_ns": float("nan"),
            "pad_recovery_span_v": float("nan"),
            "pad_recovery_note": "INSUFFICIENT_POINTS",
        }

    peak_idx = int(np.nanargmax(yy))
    peak_v = float(yy[peak_idx])
    peak_time_ns = float(tt[peak_idx])
    span = peak_v - final_v
    note = "OK"
    if span < 0.01:
        note = "SMALL_OR_INVERTED_POST_REVERSE_PULSE"

    levels = {
        "90": final_v + 0.90 * span,
        "50": final_v + 0.50 * span,
        "10": final_v + 0.10 * span,
    }
    crossings = {
        key: crossing_time(t, pad, level, peak_time_ns, "fall")
        for key, level in levels.items()
    }
    return {
        "pad_final_v": final_v,
        "pad_peak_v": peak_v,
        "pad_peak_time_ns": peak_time_ns,
        "pad_peak_from_reverse_ns": peak_time_ns - reverse_ns,
        "pad_fall_90_ns": crossings["90"],
        "pad_fall_50_ns": crossings["50"],
        "pad_fall_10_ns": crossings["10"],
        "pad_fall_90_from_reverse_ns": crossings["90"] - reverse_ns if math.isfinite(crossings["90"]) else float("nan"),
        "pad_fall_50_from_reverse_ns": crossings["50"] - reverse_ns if math.isfinite(crossings["50"]) else float("nan"),
        "pad_fall_10_from_reverse_ns": crossings["10"] - reverse_ns if math.isfinite(crossings["10"]) else float("nan"),
        "pad_recovery_span_v": span,
        "pad_recovery_note": note,
    }


def kd_recovery_markers(case: base.StudyCase, t: np.ndarray, kd: np.ndarray) -> dict[str, float]:
    _, reverse_ns = base.command_times(case)
    active_end_ns = max(end for _, end in base.transition_windows(case))
    mask = (t >= reverse_ns) & (t <= active_end_ns) & np.isfinite(kd)
    tt = np.asarray(t[mask], dtype=float)
    yy = np.asarray(kd[mask], dtype=float)
    if len(tt) < 8:
        return {"kd_min_time_ns": float("nan"), "kd_recovery_50_ns": float("nan"), "kd_t_hold_50_ns": float("nan")}
    min_idx = int(np.nanargmin(yy))
    kd_min = float(yy[min_idx])
    kd_min_time_ns = float(tt[min_idx])
    tail_start_ns = max(kd_min_time_ns, active_end_ns - max(0.3, 0.15 * (active_end_ns - kd_min_time_ns)))
    kd_final = tail_median(tt, yy, tail_start_ns, active_end_ns)
    span = kd_final - kd_min
    if span <= 1e-4:
        return {"kd_min_time_ns": kd_min_time_ns, "kd_recovery_50_ns": float("nan"), "kd_t_hold_50_ns": float("nan")}
    t50 = crossing_time(tt, yy, kd_min + 0.50 * span, kd_min_time_ns, "rise")
    return {
        "kd_min_time_ns": kd_min_time_ns,
        "kd_recovery_50_ns": t50,
        "kd_t_hold_50_ns": t50 - reverse_ns if math.isfinite(t50) else float("nan"),
    }


def classify_transistor(trans_fall50: float, native_kd_hold50: float, native_pad_fall50: float) -> str:
    if not math.isfinite(trans_fall50):
        return "TRANSISTOR_PAD_NOT_COMPARABLE"
    if math.isfinite(native_kd_hold50) and trans_fall50 < native_kd_hold50 - 0.5:
        return "TRANSISTOR_PAD_RECOVERS_MUCH_SOONER_THAN_NATIVE_KD_HOLD"
    if math.isfinite(native_kd_hold50) and abs(trans_fall50 - native_kd_hold50) <= 0.3:
        return "TRANSISTOR_PAD_HOLD_SIMILAR_TO_NATIVE_KD_HOLD"
    if math.isfinite(native_pad_fall50) and abs(trans_fall50 - native_pad_fall50) <= 0.3:
        return "TRANSISTOR_PAD_SIMILAR_TO_NATIVE_PAD"
    return "TRANSISTOR_PAD_DIFFERENT_TIMING"


def build_rows(cases: list[base.StudyCase]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in cases:
        _, reverse_ns = base.command_times(case)
        native = load_hspice(case.case_id, "hspice_native_ibis")
        transistor = load_hspice(case.case_id, "hspice_transistor_sp")

        nt = t_ns(native)
        npad = sig(native, "v(pad_ibis)")
        nkd = sig(native, "v(kd)")
        tt = t_ns(transistor)
        tpad = sig(transistor, "v(pad_sp)")

        native_pad = pad_recovery_markers(case, nt, npad)
        trans_pad = pad_recovery_markers(case, tt, tpad)
        native_kd = kd_recovery_markers(case, nt, nkd)

        for reference, markers in [
            ("hspice_native_ibis_pad", native_pad),
            ("hspice_transistor_sp_pad", trans_pad),
        ]:
            row: dict[str, object] = {
                "case_id": case.case_id,
                "pulse_width_ns": case.pulse_width_ns,
                "reference": reference,
                "reverse_edge_ns": reverse_ns,
                **markers,
                "native_kd_recovery_50_ns": native_kd["kd_recovery_50_ns"],
                "native_kd_t_hold_50_ns": native_kd["kd_t_hold_50_ns"],
                "native_kd_min_time_ns": native_kd["kd_min_time_ns"],
            }
            if reference == "hspice_transistor_sp_pad":
                row["classification"] = classify_transistor(
                    float(trans_pad["pad_fall_50_from_reverse_ns"]),
                    float(native_kd["kd_t_hold_50_ns"]),
                    float(native_pad["pad_fall_50_from_reverse_ns"]),
                )
                row["transistor_fall50_minus_native_kd_hold50_ps"] = (
                    (float(trans_pad["pad_fall_50_from_reverse_ns"]) - float(native_kd["kd_t_hold_50_ns"])) * 1e3
                    if math.isfinite(float(trans_pad["pad_fall_50_from_reverse_ns"])) and math.isfinite(float(native_kd["kd_t_hold_50_ns"]))
                    else float("nan")
                )
                row["transistor_fall50_minus_native_pad_fall50_ps"] = (
                    (float(trans_pad["pad_fall_50_from_reverse_ns"]) - float(native_pad["pad_fall_50_from_reverse_ns"])) * 1e3
                    if math.isfinite(float(trans_pad["pad_fall_50_from_reverse_ns"])) and math.isfinite(float(native_pad["pad_fall_50_from_reverse_ns"]))
                    else float("nan")
                )
            rows.append(row)
    return rows


def plot_case(case: base.StudyCase, rows: list[dict[str, object]]) -> None:
    _, reverse_ns = base.command_times(case)
    active_end_ns = max(end for _, end in base.transition_windows(case))
    native = load_hspice(case.case_id, "hspice_native_ibis")
    transistor = load_hspice(case.case_id, "hspice_transistor_sp")
    nt = t_ns(native)
    npad = sig(native, "v(pad_ibis)")
    tt = t_ns(transistor)
    tpad = sig(transistor, "v(pad_sp)")
    nkd = sig(native, "v(kd)")
    kd = kd_recovery_markers(case, nt, nkd)
    row_by_ref = {
        str(row["reference"]): row
        for row in rows
        if row["case_id"] == case.case_id
    }

    fig, axes = plt.subplots(2, 1, figsize=(9.5, 6.6), sharex=True)
    ax = axes[0]
    t0 = max(0.0, reverse_ns - 1.0)
    t1 = min(case.stop_ns, active_end_ns + 0.8)
    ax.plot(nt, npad, color="#1f77b4", lw=2.0, label="HSPICE native IBIS pad")
    ax.plot(tt, tpad, color="#6f2dbd", lw=2.0, label="HSPICE transistor io_buf.sp pad")
    ax.axvline(reverse_ns, color="#222222", lw=1.2, alpha=0.75, label="input reverse edge")
    if math.isfinite(float(kd["kd_recovery_50_ns"])):
        ax.axvline(float(kd["kd_recovery_50_ns"]), color="#7f7f7f", lw=1.2, ls=":", label="native Kd 50% recovery")
    for ref, color in [("hspice_native_ibis_pad", "#1f77b4"), ("hspice_transistor_sp_pad", "#6f2dbd")]:
        row = row_by_ref.get(ref)
        if not row:
            continue
        peak_t = float(row["pad_peak_time_ns"])
        peak_v = float(row["pad_peak_v"])
        fall50 = float(row["pad_fall_50_ns"])
        if math.isfinite(peak_t):
            ax.scatter([peak_t], [peak_v], color=color, edgecolors="white", zorder=5)
            ax.text(peak_t, peak_v, " peak", color=color, fontsize=8, ha="left", va="bottom")
        if math.isfinite(fall50):
            y50 = float(row["pad_final_v"]) + 0.5 * float(row["pad_recovery_span_v"])
            ax.scatter([fall50], [y50], color=color, marker="s", edgecolors="white", zorder=5)
            ax.text(fall50, y50, " 50% return", color=color, fontsize=8, ha="left", va="top")
    ax.set_xlim(t0, t1)
    ax.set_ylabel("Pad voltage (V)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    ax.set_title(f"{case.case_id}: pad-level recovery timing from cached HSPICE references")

    ax = axes[1]
    ax.plot(nt, nkd, color="#1f77b4", lw=2.0, label="native IBIS Kd")
    ax.axvline(reverse_ns, color="#222222", lw=1.2, alpha=0.75, label="input reverse edge")
    if math.isfinite(float(kd["kd_min_time_ns"])):
        ax.axvline(float(kd["kd_min_time_ns"]), color="#d62728", lw=1.0, ls="--", label="native Kd min")
    if math.isfinite(float(kd["kd_recovery_50_ns"])):
        ax.axvline(float(kd["kd_recovery_50_ns"]), color="#7f7f7f", lw=1.2, ls=":", label="native Kd 50% recovery")
    ax.set_ylabel("Native Kd")
    ax.set_xlabel("Time (ns)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "plots" / f"{case.case_id}_pad_recovery_timing.png", dpi=180)
    plt.close(fig)


def plot_summary(rows: list[dict[str, object]]) -> None:
    by = {(row["case_id"], row["reference"]): row for row in rows}
    cases = [case for case in SHORT_HIGH_CASES]
    pulse = np.asarray([float(by[(case, "hspice_native_ibis_pad")]["pulse_width_ns"]) for case in cases], dtype=float)
    native_pad = np.asarray([float(by[(case, "hspice_native_ibis_pad")]["pad_fall_50_from_reverse_ns"]) for case in cases], dtype=float)
    trans_pad = np.asarray([float(by[(case, "hspice_transistor_sp_pad")]["pad_fall_50_from_reverse_ns"]) for case in cases], dtype=float)
    native_kd = np.asarray([float(by[(case, "hspice_native_ibis_pad")]["native_kd_t_hold_50_ns"]) for case in cases], dtype=float)
    native_peak = np.asarray([float(by[(case, "hspice_native_ibis_pad")]["pad_peak_from_reverse_ns"]) for case in cases], dtype=float)
    trans_peak = np.asarray([float(by[(case, "hspice_transistor_sp_pad")]["pad_peak_from_reverse_ns"]) for case in cases], dtype=float)

    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    ax.plot(pulse, native_kd, marker="o", lw=2.2, color="#7f7f7f", label="native IBIS Kd 50% recovery")
    ax.plot(pulse, native_pad, marker="o", lw=2.2, color="#1f77b4", label="native IBIS pad 50% return")
    ax.plot(pulse, trans_pad, marker="o", lw=2.2, color="#6f2dbd", label="transistor pad 50% return")
    ax.plot(pulse, native_peak, marker="^", lw=1.6, color="#1f77b4", alpha=0.75, label="native pad peak/turnaround")
    ax.plot(pulse, trans_peak, marker="^", lw=1.6, color="#6f2dbd", alpha=0.75, label="transistor pad peak/turnaround")
    ax.set_xlabel("Short-high pulse width (ns)")
    ax.set_ylabel("Time from input falling edge (ns)")
    ax.set_title("Pad recovery timing vs native-IBIS Kd hold")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "plots" / "pad_recovery_timing_vs_width.png", dpi=180)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]]) -> None:
    trans_rows = [row for row in rows if row["reference"] == "hspice_transistor_sp_pad"]
    native_rows = [row for row in rows if row["reference"] == "hspice_native_ibis_pad"]
    lines = [
        "# Transistor Pad Recovery Timing Audit",
        "",
        "This audit uses cached HSPICE `.tr0` files only. It asks whether the short-high pad recovery in the transistor-level `io_buf.sp` reference has a native-IBIS-like delayed hold, or whether it returns much sooner.",
        "",
        "Definitions:",
        "",
        "- `pad peak/turnaround`: first post-reverse pad maximum, where the short-high pulse stops rising and starts returning low.",
        "- `pad 50% return`: first falling crossing halfway from that post-reverse pad peak back to the tail/final voltage.",
        "- `native Kd 50% recovery`: native HSPICE IBIS coefficient recovery from Kd minimum to final, included only as coefficient-model context.",
        "",
        "## Result",
        "",
    ]
    table = [
        "| Case | Native Kd hold50 ns | Native pad 50% return ns | Transistor pad 50% return ns | Transistor minus native Kd ps | Classification |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for nrow, trow in zip(native_rows, trans_rows):
        table.append(
            "| {case} | {kd:.4f} | {npad:.4f} | {tpad:.4f} | {err:.1f} | {cls} |".format(
                case=trow["case_id"],
                kd=float(trow["native_kd_t_hold_50_ns"]),
                npad=float(nrow["pad_fall_50_from_reverse_ns"]),
                tpad=float(trow["pad_fall_50_from_reverse_ns"]) if math.isfinite(float(trow["pad_fall_50_from_reverse_ns"])) else float("nan"),
                err=float(trow["transistor_fall50_minus_native_kd_hold50_ps"]) if math.isfinite(float(trow["transistor_fall50_minus_native_kd_hold50_ps"])) else float("nan"),
                cls=trow["classification"],
            )
        )
    lines.extend(table)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The transistor pad does **not** show the same approximately 2 ns native-IBIS Kd hold in the cleanly comparable 1 ns and 2 ns short-high cases. Its post-reverse pad return is much earlier.",
            "- The 500 ps transistor case is only weakly comparable because the post-reverse pulse is small/inverted; the plot makes this visible instead of hiding it in one number.",
            "- This does not prove the transistor netlist is the sole truth, because the long-pulse native-IBIS-vs-transistor pad gap remains large. It does say the native-IBIS Kd hold should be treated as a playback-model behavior unless we can reconcile the transistor/reference setup.",
            "- Product implication stays conservative: ship/report the directional+residual model as the best current experimental candidate, keep Kd recovery variants diagnostic, and do not implement the failed simple command-age law.",
            "",
            "## Outputs",
            "",
            "- `pad_recovery_timing.csv`",
            "- `plots/pad_recovery_timing_vs_width.png`",
            "- `plots/<case>_pad_recovery_timing.png`",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="ascii")


def main() -> None:
    ensure_dir(OUT_DIR / "plots")
    case_map = {case.case_id: case for case in base.build_cases(include_low=True)}
    cases = [case_map[case_id] for case_id in SHORT_HIGH_CASES]
    rows = build_rows(cases)
    write_csv(OUT_DIR / "pad_recovery_timing.csv", rows)
    for case in cases:
        plot_case(case, rows)
    plot_summary(rows)
    write_readme(rows)
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
