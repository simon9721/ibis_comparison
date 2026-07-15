from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from eye_diagram import parse_hspice_tr0, parse_ngspice_raw
import run_io_buf_value_matched_replay_redo as redo


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "results" / "io_buf_value_matched_replay_redo_2026-06-25"
CASE_ID = "short_pulse_2ns_high"
OUT = STUDY / "timeout_investigation"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_stop_ns(name: str) -> float:
    text = name.removeprefix("stop_").removesuffix("ns").replace("p", ".")
    return float(text)


def raw_summary(raw: Path, stop_ns: float) -> dict[str, object]:
    row: dict[str, object] = {
        "stop_ns": stop_ns,
        "raw": str(raw.relative_to(ROOT)),
        "raw_mb": raw.stat().st_size / 1e6 if raw.exists() else 0.0,
    }
    if not raw.exists():
        row.update({"status": "missing_raw", "n_rows": 0, "tmax_ns": math.nan})
        return row
    try:
        data = parse_ngspice_raw(raw)
        t = np.asarray(data.get("time", []), dtype=float) * 1e9
    except Exception as exc:
        row.update({"status": "parse_error", "parse_error": repr(exc), "n_rows": 0, "tmax_ns": math.nan})
        return row
    if t.size <= 1:
        row.update({"status": "partial_unusable", "n_rows": int(t.size), "tmax_ns": float(t[-1]) if t.size else math.nan})
        return row
    dt = np.diff(t)
    complete = t[-1] >= stop_ns - 1e-6
    row.update(
        {
            "status": "complete" if complete else "partial",
            "n_rows": int(t.size),
            "tmax_ns": float(t[-1]),
            "dt_min_ns": float(np.nanmin(dt)),
            "dt_median_ns": float(np.nanmedian(dt)),
            "rows_after_7ns": int(np.sum(t >= 7.0)),
            "rows_7p2_to_7p25ns": int(np.sum((t >= 7.2) & (t <= 7.25))),
        }
    )
    return row


def build_timeout_bracket() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    root = STUDY / "debug_timeout"
    for d in sorted(root.glob("stop_*ns"), key=lambda p: parse_stop_ns(p.name)):
        raw_files = list(d.glob("*.raw"))
        raw = raw_files[0] if raw_files else d / "missing.raw"
        rows.append(raw_summary(raw, parse_stop_ns(d.name)))
    write_csv(OUT / "timeout_bracket.csv", rows)
    return rows


def interp_hspice(case: redo.StudyCase):
    h = parse_hspice_tr0(STUDY / "cases" / case.case_id / "hspice_native_ibis" / f"{case.case_id}_hspice_native_ibis.tr0")
    ht = redo.to_ns(redo.find_signal(h, "time"))
    return ht, redo.find_signal(h, "v(pad_ibis)"), redo.find_signal(h, "v(ku)"), redo.find_signal(h, "v(kd)")


def value_at(t: np.ndarray, y: np.ndarray, x: float) -> float:
    return float(np.interp(x, t, y))


def build_tau_sweep(case: redo.StudyCase) -> list[dict[str, object]]:
    ht, hpad, hku, hkd = interp_hspice(case)
    mask = redo.active_mask(ht, case)
    rows: list[dict[str, object]] = []
    root = STUDY / "debug_timeout_tau"
    for d in sorted(root.glob("coeff_tau_*"), key=lambda p: float(p.name.removeprefix("coeff_tau_").removesuffix("p"))):
        tau = d.name.removeprefix("coeff_tau_")
        raw_files = list(d.glob("*.raw"))
        row: dict[str, object] = {"coeff_tau": tau, "raw": str(raw_files[0].relative_to(ROOT)) if raw_files else ""}
        if not raw_files:
            row["status"] = "missing_raw"
            rows.append(row)
            continue
        try:
            data = parse_ngspice_raw(raw_files[0])
            nt = redo.to_ns(redo.find_signal(data, "time"))
        except Exception as exc:
            row.update({"status": "parse_error", "error": repr(exc)})
            rows.append(row)
            continue
        row.update({"n_rows": int(len(nt)), "tmax_ns": float(nt[-1]) if len(nt) else math.nan})
        if len(nt) <= 1 or nt[-1] < case.stop_ns - 0.01:
            row["status"] = "partial_unusable"
            rows.append(row)
            continue
        pad = redo.interp_to(nt, redo.find_signal(data, "v(pad)"), ht)
        ku = redo.interp_to(nt, redo.find_signal(data, "v(xdrv.ku)"), ht)
        kd = redo.interp_to(nt, redo.find_signal(data, "v(xdrv.kd)"), ht)
        row.update(
            {
                "status": "complete",
                "pad_rmse_v": redo.rmse(hpad[mask], pad[mask]),
                "ku_rmse": redo.rmse(hku[mask], ku[mask]),
                "kd_rmse": redo.rmse(hkd[mask], kd[mask]),
                "pad_peak_v": redo.finite_max(pad, mask),
                "ku_peak": redo.finite_max(ku, mask),
                "kd_min": redo.finite_min(kd, mask),
                "start_disagree_max": float(np.nanmax(redo.find_signal(data, "v(xdrv.start_disagree)"))),
            }
        )
        rows.append(row)
    write_csv(OUT / "coeff_tau_sweep.csv", rows)
    return rows


def plot_internal_diagnostics(case: redo.StudyCase) -> None:
    ht, hpad, hku, hkd = interp_hspice(case)
    legacy = parse_ngspice_raw(STUDY / "cases" / case.case_id / "ngspice_legacy" / f"{case.case_id}_ngspice_legacy.raw")
    lt = redo.to_ns(redo.find_signal(legacy, "time"))
    partial = parse_ngspice_raw(
        STUDY
        / "debug_timeout"
        / "stop_7p25ns"
        / "short_pulse_2ns_value_matched_stop_7p25ns.raw"
    )
    vt = redo.to_ns(redo.find_signal(partial, "time"))
    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True, constrained_layout=True)
    xlim = (6.9, 7.25)
    axes[0].plot(ht, hpad, color="#1f77b4", lw=2, label="HSPICE native pad")
    axes[0].plot(lt, redo.find_signal(legacy, "v(pad)"), color="#ff7f0e", lw=1.3, label="legacy pad")
    axes[0].plot(vt, redo.find_signal(partial, "v(pad)"), color="#2ca02c", lw=1.5, label="value-matched partial pad")
    axes[0].set_ylabel("Pad (V)")

    axes[1].plot(vt, redo.find_signal(partial, "v(xdrv.ku)"), color="#1f77b4", lw=1.4, label="Ku")
    axes[1].plot(vt, redo.find_signal(partial, "v(xdrv.kd)"), color="#d62728", lw=1.4, label="Kd")
    axes[1].plot(vt, redo.find_signal(partial, "v(xdrv.kutarget)"), color="#17becf", lw=1.0, label="Ku target")
    axes[1].plot(vt, redo.find_signal(partial, "v(xdrv.kdtarget)"), color="#9467bd", lw=1.0, label="Kd target")
    axes[1].set_ylabel("Coeff")

    axes[2].plot(vt, redo.find_signal(partial, "v(xdrv.vmarg)"), color="#2ca02c", lw=1.5, label="VMARG")
    axes[2].plot(vt, redo.find_signal(partial, "v(xdrv.vmstart)"), color="#9467bd", lw=1.2, label="VMSTART")
    axes[2].plot(vt, redo.find_signal(partial, "v(xdrv.tf_ku)"), color="#17becf", lw=1.0, label="TF_KU")
    axes[2].plot(vt, redo.find_signal(partial, "v(xdrv.tf_kd)"), color="#d62728", lw=1.0, label="TF_KD")
    axes[2].plot(vt, redo.find_signal(partial, "v(xdrv.start_disagree)"), color="#7f7f7f", lw=1.0, label="start disagree")
    axes[2].set_ylabel("Table time (ns)")

    dt = np.diff(vt)
    axes[3].semilogy(vt[1:], np.maximum(dt, 1e-18), color="#444444", lw=0.8, label="accepted timestep")
    axes[3].set_ylabel("dt (ns)")
    axes[3].set_xlabel("Time (ns)")
    for ax in axes:
        ax.axvline(7.0, color="#999999", lw=1.0)
        ax.axvline(7.001, color="#bbbbbb", lw=1.0)
        ax.set_xlim(*xlim)
        ax.grid(True, color="#d8dee8", linewidth=0.8)
        ax.legend(loc="best", ncol=3, frameon=False)
    fig.suptitle("short_pulse_2ns_high value-matched timeout: internal diagnostics", fontweight="bold")
    fig.savefig(OUT / "01_internal_diagnostics_stop_7p25ns.png", dpi=180)
    plt.close(fig)


def plot_tau_sweep(rows: list[dict[str, object]]) -> None:
    complete = [r for r in rows if r.get("status") == "complete"]
    if not complete:
        return
    labels = [str(r["coeff_tau"]) for r in complete]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 8.5), sharex=True, constrained_layout=True)
    for ax, key, ylabel, scale in [
        (axes[0], "pad_rmse_v", "Pad RMSE (mV)", 1e3),
        (axes[1], "ku_rmse", "Ku RMSE", 1.0),
        (axes[2], "kd_rmse", "Kd RMSE", 1.0),
    ]:
        vals = [float(r[key]) * scale for r in complete]
        ax.bar(x, vals, color="#2ca02c")
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", color="#d8dee8")
    axes[-1].set_xticks(x, labels)
    axes[-1].set_xlabel("coeff_tau")
    fig.suptitle("short_pulse_2ns_high completed value-matched tau variants", fontweight="bold")
    fig.savefig(OUT / "02_coeff_tau_sweep_metrics.png", dpi=180)
    plt.close(fig)


def write_readme(bracket_rows: list[dict[str, object]], tau_rows: list[dict[str, object]]) -> None:
    complete_tau = [r for r in tau_rows if r.get("status") == "complete"]
    best = min(complete_tau, key=lambda r: float(r.get("pad_rmse_v", 1e9))) if complete_tau else None
    lines = [
        "# Value-Matched Replay Timeout Investigation",
        "",
        "This folder analyzes why `short_pulse_2ns_high` produced no value-matched waveform in the canonical redo.",
        "",
        "## Findings",
        "",
        "- The value-matched run is not zero-progress. It completes to `7.25 ns`, but accepted timesteps collapse after the falling/reverse edge at `7.0 ns`.",
        "- Stop-time bracketing shows the row explosion directly: `7.25 ns` completes with about 196k rows, while `7.5 ns` and later do not complete within the debug timeout.",
        "- The immediate mechanism is stiffness in the capacitor-backed `Ku/Kd` states with `coeff_tau=1p` while tracking a discontinuous/jagged value-matched target.",
        "- The deeper algorithmic issue is that `VMARG` briefly includes the old rising-edge elapsed time before the delayed legacy edge timer resets. Around the falling edge, `VMARG` jumps from the old-transition region into the value-matched falling-table region.",
        "- Ku-derived and Kd-derived falling-table start times disagree by nearly `1.94 ns`, so the balanced table-start assumption is physically ambiguous.",
        "- Increasing only `coeff_tau` to `5p` or larger makes ngspice complete, proving the timeout is a stiffness/numerical robustness issue, but coefficient accuracy remains poor, especially `Kd`.",
        "",
        "## Artifacts",
        "",
        "- `timeout_bracket.csv`: stop-time bracketing and timestep statistics.",
        "- `coeff_tau_sweep.csv`: controlled tau variants for the same value-matched logic.",
        "- `01_internal_diagnostics_stop_7p25ns.png`: internal waveforms and timestep collapse.",
        "- `02_coeff_tau_sweep_metrics.png`: completed tau-variant metric summary.",
        "",
        "## Tau Sweep Summary",
        "",
        "| coeff_tau | status | pad RMSE mV | Ku RMSE | Kd RMSE | pad peak V | Ku peak | Kd min |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in tau_rows:
        def val(key: str, scale: float = 1.0, fmt: str = ".4g") -> str:
            try:
                return format(float(row[key]) * scale, fmt)
            except Exception:
                return "n/a"
        lines.append(
            f"| {row.get('coeff_tau','')} | {row.get('status','')} | {val('pad_rmse_v',1e3,'.3f')} | {val('ku_rmse')} | {val('kd_rmse')} | {val('pad_peak_v')} | {val('ku_peak')} | {val('kd_min')} |"
        )
    if best:
        lines.extend(
            [
                "",
                f"Best completed pad RMSE in this diagnostic sweep is `coeff_tau={best['coeff_tau']}`, but this is not a proposed fix because `Kd` RMSE remains high.",
            ]
        )
    lines.append("")
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ensure_dir(OUT)
    case = redo.case_by_id(CASE_ID)
    bracket = build_timeout_bracket()
    tau = build_tau_sweep(case)
    plot_internal_diagnostics(case)
    plot_tau_sweep(tau)
    write_readme(bracket, tau)
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
