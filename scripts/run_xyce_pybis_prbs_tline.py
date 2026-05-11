from __future__ import annotations

import argparse
import csv
import subprocess
import time
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from test_xyce_pybis_tail_fixes import (
    CANDIDATES,
    NGSPICE_DIR,
    OUT_DIR,
    OUTPUT,
    ROOT,
    TIMEINT,
    XYCE,
    XYCE_DIR,
    Candidate,
    col,
    load_ngspice_raw,
    load_xyce_csv,
    make_model,
    ns,
)


NGSPICE = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")

DIRECT = Candidate("direct", "direct tanh200", "base", "driver_OutputInput_Typical.sub")
CANDIDATE_BY_NAME = {c.name: c for c in [DIRECT, *CANDIDATES]}


def clean_stop(stop: str) -> str:
    return stop.replace(".", "p").replace("n", "n").replace("u", "u")


def riso_suffix(riso: float) -> str:
    if abs(riso) < 1e-15:
        return ""
    tag = f"{riso:g}".replace("-", "m").replace(".", "p")
    return f"_riso{tag}"


def target_ns(stop: str) -> float:
    text = stop.strip().lower()
    if text.endswith("ns"):
        return float(text[:-2])
    if text.endswith("n"):
        return float(text[:-1])
    if text.endswith("us"):
        return float(text[:-2]) * 1000.0
    if text.endswith("u"):
        return float(text[:-1]) * 1000.0
    raise ValueError(f"Unsupported stop time {stop}")


def ng_deck(stop: str, riso: float = 0.0) -> Path:
    return NGSPICE_DIR / f"tb_prbs7_tline_50ohm_{clean_stop(stop)}{riso_suffix(riso)}_ngspice_pybis.sp"


def ng_raw(stop: str, riso: float = 0.0) -> Path:
    return NGSPICE_DIR / f"tb_prbs7_tline_50ohm_{clean_stop(stop)}{riso_suffix(riso)}_ngspice_pybis.raw"


def xyce_deck(stop: str, candidate: Candidate, riso: float = 0.0) -> Path:
    return XYCE_DIR / f"tb_prbs7_tline_50ohm_{clean_stop(stop)}{riso_suffix(riso)}_xyce_{candidate.name}.cir"


def xyce_csv(stop: str, candidate: Candidate, riso: float = 0.0) -> Path:
    return Path(str(xyce_deck(stop, candidate, riso)) + ".csv")


def tline_load(riso: float) -> str:
    if abs(riso) < 1e-15:
        return """TVAL  pad  0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0 50"""
    return f"""RISO  pad  tpad  {riso:g}
TVAL  tpad 0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0 50"""


def save_nodes(riso: float) -> str:
    return "V(in_dig) V(pad) V(tpad) V(ntst) V(xdrv.ku) V(xdrv.kd)" if abs(riso) >= 1e-15 else "V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)"


def print_nodes(riso: float) -> str:
    return "V(in_dig) V(pad) V(tpad) V(ntst)" if abs(riso) >= 1e-15 else "V(in_dig) V(pad) V(ntst)"


def ic_nodes(riso: float) -> str:
    return "V(pad)=0 V(tpad)=0 V(ntst)=0" if abs(riso) >= 1e-15 else "V(pad)=0 V(ntst)=0"


def write_ngspice_deck(stop: str, riso: float = 0.0) -> Path:
    path = ng_deck(stop, riso)
    path.write_text(
        f"""* PRBS7 + pybis2spice + ideal 30 ps 50-ohm T-line
* Driver-to-line series damping RISO={riso:g} ohm
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

.include 'prbs7_vstim.inc'
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

{tline_load(riso)}

.save {save_nodes(riso)}
.tran 10p {stop}
.end
""",
        encoding="ascii",
    )
    return path


def write_xyce_deck(stop: str, candidate: Candidate, riso: float = 0.0) -> Path:
    if candidate.name != "direct":
        make_model(candidate)
    path = xyce_deck(stop, candidate, riso)
    path.write_text(
        f"""* PRBS7 + Xyce pybis + ideal 30 ps 50-ohm T-line
* Candidate: {candidate.title}
* Driver-to-line series damping RISO={riso:g} ohm

.include 'prbs7_vstim.inc'
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3

.include '{candidate.include_file}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

{tline_load(riso)}

.ic {ic_nodes(riso)} V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
{TIMEINT}
{OUTPUT}
.tran 10p {stop} uic
.print tran format=csv time {print_nodes(riso)} V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
.end
""",
        encoding="ascii",
    )
    return path


def run_process(cmd: list[str], cwd: Path, timeout_s: float) -> tuple[int | None, bool, float]:
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=cwd, timeout=timeout_s, capture_output=True, text=True)
        return proc.returncode, False, round(time.time() - t0, 2)
    except subprocess.TimeoutExpired:
        return None, True, round(time.time() - t0, 2)


def run_ngspice(stop: str, timeout_s: float, reuse_existing: bool = False, riso: float = 0.0) -> dict[str, object]:
    deck = write_ngspice_deck(stop, riso)
    raw = ng_raw(stop, riso)
    if reuse_existing and raw.exists():
        rc, timed_out, wall_s = 0, False, 0.0
    else:
        raw.unlink(missing_ok=True)
        rc, timed_out, wall_s = run_process([str(NGSPICE), "-b", "-r", raw.name, deck.name], NGSPICE_DIR, timeout_s)
    row: dict[str, object] = {
        "simulator": "ngspice",
        "candidate": "direct",
        "model": "driver_OutputInput_Typical.sub",
        "riso_ohm": riso,
        "returncode": rc if rc is not None else "",
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(deck.relative_to(ROOT)).replace("\\", "/"),
        "output": str(raw.relative_to(ROOT)).replace("\\", "/"),
    }
    if raw.exists():
        data = load_ngspice_raw(raw)
        t = col(data, "time")
        row.update(
            {
                "rows": len(t),
                "t_end_ns": float(ns(t[-1])),
                "completed": float(ns(t[-1])) >= target_ns(stop) - 0.05,
                "ntst_min": float(np.min(col(data, "v(ntst)"))),
                "ntst_max": float(np.max(col(data, "v(ntst)"))),
                "pad_min": float(np.min(col(data, "v(pad)"))),
                "pad_max": float(np.max(col(data, "v(pad)"))),
            }
        )
    else:
        row["completed"] = False
        row["error"] = "raw not generated"
    return row


def compare(stop: str, xy: dict[str, np.ndarray], riso: float = 0.0) -> dict[str, float]:
    ref = load_ngspice_raw(ng_raw(stop, riso))
    t_ref = col(ref, "time")
    y_ref = col(ref, "v(ntst)")
    p_ref = col(ref, "v(pad)")
    t = col(xy, "time")
    y = col(xy, "v(ntst)")
    p = col(xy, "v(pad)")
    compare_stop = min(t[-1], t_ref[-1], target_ns(stop) * 1e-9)
    mask = (t_ref >= 0) & (t_ref <= compare_stop)
    common = t_ref[mask]
    y_err = np.interp(common, t, y) - y_ref[mask]
    p_err = np.interp(common, t, p) - p_ref[mask]
    return {
        "compare_stop_ns": float(ns(compare_stop)),
        "ntst_rmse_mv": float(np.sqrt(np.mean(y_err**2)) * 1e3),
        "ntst_max_abs_mv": float(np.max(np.abs(y_err)) * 1e3),
        "ntst_mean_mv": float(np.mean(y_err) * 1e3),
        "pad_rmse_mv": float(np.sqrt(np.mean(p_err**2)) * 1e3),
        "pad_max_abs_mv": float(np.max(np.abs(p_err)) * 1e3),
    }


def run_xyce(stop: str, candidate: Candidate, timeout_s: float, reuse_existing: bool = False, riso: float = 0.0) -> dict[str, object]:
    deck = write_xyce_deck(stop, candidate, riso)
    out = xyce_csv(stop, candidate, riso)
    if reuse_existing and out.exists():
        rc, timed_out, wall_s = 0, False, 0.0
    else:
        out.unlink(missing_ok=True)
        rc, timed_out, wall_s = run_process([str(XYCE), deck.name], XYCE_DIR, timeout_s)
    row: dict[str, object] = {
        "simulator": "xyce",
        "candidate": candidate.name,
        "candidate_title": candidate.title,
        "model": candidate.include_file,
        "riso_ohm": riso,
        "returncode": rc if rc is not None else "",
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(deck.relative_to(ROOT)).replace("\\", "/"),
        "output": str(out.relative_to(ROOT)).replace("\\", "/"),
    }
    if out.exists():
        try:
            data = load_xyce_csv(out)
            t = col(data, "time")
            row.update(
                {
                    "rows": len(t),
                    "t_end_ns": float(ns(t[-1])),
                    "completed": float(ns(t[-1])) >= target_ns(stop) - 0.05,
                    "ntst_min": float(np.min(col(data, "v(ntst)"))),
                    "ntst_max": float(np.max(col(data, "v(ntst)"))),
                    "pad_min": float(np.min(col(data, "v(pad)"))),
                    "pad_max": float(np.max(col(data, "v(pad)"))),
                    "nx_last": float(col(data, "v(xdrv:nx)")[-1]),
                    "nx_max": float(np.max(col(data, "v(xdrv:nx)"))),
                }
            )
            row.update(compare(stop, data, riso))
        except Exception as exc:
            row["completed"] = False
            row["error"] = str(exc)
    else:
        row["completed"] = False
        row["error"] = "csv not generated"
    return row


def write_metrics(stop: str, rows: list[dict[str, object]], riso: float = 0.0) -> Path:
    out = OUT_DIR / f"xyce_pybis_prbs_tline_{clean_stop(stop)}{riso_suffix(riso)}_metrics.csv"
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    return out


def plot_overlay(stop: str, rows: list[dict[str, object]], riso: float = 0.0) -> Path:
    out = OUT_DIR / f"xyce_pybis_prbs_tline_{clean_stop(stop)}{riso_suffix(riso)}_overlay.png"
    ref = load_ngspice_raw(ng_raw(stop, riso))
    t_ref = ns(col(ref, "time"))
    y_ref = col(ref, "v(ntst)")
    completed_xy = [r for r in rows if r["simulator"] == "xyce" and str(r.get("completed")) == "True"]
    partial_xy = [r for r in rows if r["simulator"] == "xyce" and str(r.get("completed")) != "True"]

    tmax = target_ns(stop)
    windows = [(0.0, min(250.0, tmax))]
    if tmax > 300:
        windows.append((max(0.0, tmax - 100.0), tmax))
    else:
        windows.append((max(0.0, tmax - 80.0), tmax))

    fig, axes = plt.subplots(len(windows), 1, figsize=(11, 4 * len(windows)), sharex=False)
    if len(windows) == 1:
        axes = [axes]
    for ax, (lo, hi) in zip(axes, windows):
        mask = (t_ref >= lo) & (t_ref <= hi)
        ax.plot(t_ref[mask], y_ref[mask], color="black", linewidth=1.1, label="ngspice direct")
        for row in completed_xy:
            cand = CANDIDATE_BY_NAME[row["candidate"]]
            data = load_xyce_csv(xyce_csv(stop, cand, riso))
            t = ns(col(data, "time"))
            y = col(data, "v(ntst)")
            m = (t >= lo) & (t <= hi)
            ax.plot(t[m], y[m], linewidth=0.9, label=f"{cand.name} ({float(row['ntst_rmse_mv']):.1f} mV)")
        for row in partial_xy:
            cand = CANDIDATE_BY_NAME[row["candidate"]]
            data = load_xyce_csv(xyce_csv(stop, cand, riso))
            t = ns(col(data, "time"))
            y = col(data, "v(ntst)")
            m = (t >= lo) & (t <= hi)
            if np.any(m):
                ax.plot(t[m], y[m], linewidth=0.8, linestyle="--", label=f"{cand.name} partial")
        ax.set_xlim(lo, hi)
        ax.set_ylabel("V(ntst) [V]")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8, ncol=3)
    axes[0].set_title(f"PRBS7 + ideal 30 ps 50-ohm T-line, stop={stop}, RISO={riso:g} ohm")
    axes[-1].set_xlabel("Time [ns]")
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def selected_candidates(text: str) -> list[Candidate]:
    if text in {"none", "ngspice-only"}:
        return []
    if text == "default":
        names = ["direct", "tanh92", "flat4p2", "edge50_flat4p2", "edge15_flat4p2", "tanh15"]
    else:
        names = [name.strip() for name in text.split(",") if name.strip()]
    missing = [name for name in names if name not in CANDIDATE_BY_NAME]
    if missing:
        raise SystemExit(f"Unknown candidate(s): {', '.join(missing)}")
    return [CANDIDATE_BY_NAME[name] for name in names]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop", default="200n")
    parser.add_argument("--candidates", default="default")
    parser.add_argument("--ng-timeout", type=float, default=180.0)
    parser.add_argument("--xyce-timeout", type=float, default=120.0)
    parser.add_argument("--skip-ngspice", action="store_true")
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument("--riso", type=float, default=0.0, help="driver-to-line series resistance in ohms")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    if args.skip_ngspice and ng_raw(args.stop, args.riso).exists():
        ng_row = run_ngspice(args.stop, args.ng_timeout, reuse_existing=True, riso=args.riso)
    else:
        ng_row = run_ngspice(args.stop, args.ng_timeout, reuse_existing=args.reuse_existing, riso=args.riso)
    rows.append(ng_row)
    print(
        f"{'PASS' if ng_row.get('completed') is True else 'FAIL':4s} "
        f"ngspice direct t_end={ng_row.get('t_end_ns', '')} ns wall={ng_row.get('wall_s', '')} s",
        flush=True,
    )

    if not ng_raw(args.stop, args.riso).exists():
        raise SystemExit("ngspice reference raw was not generated; aborting Xyce comparisons")

    for candidate in selected_candidates(args.candidates):
        row = run_xyce(args.stop, candidate, args.xyce_timeout, reuse_existing=args.reuse_existing, riso=args.riso)
        rows.append(row)
        rmse = row.get("ntst_rmse_mv", "")
        rmse_text = f", rmse={float(rmse):.1f} mV" if rmse != "" else ""
        print(
            f"{'PASS' if row.get('completed') is True else 'FAIL':4s} "
            f"xyce {candidate.name:18s} t_end={row.get('t_end_ns', '')} ns "
            f"wall={row.get('wall_s', '')} s{rmse_text}",
            flush=True,
        )

    metrics = write_metrics(args.stop, rows, args.riso)
    plot = plot_overlay(args.stop, rows, args.riso)
    print(metrics.relative_to(ROOT))
    print(plot.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
