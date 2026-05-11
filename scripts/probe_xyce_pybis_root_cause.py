from __future__ import annotations

import argparse
import csv
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
XYCE_DIR = ROOT / "xyce_pybis"
OUT_DIR = ROOT / "plots" / "xyce_pybis"
XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")

BASE_MODEL = "driver_OutputInput_Typical_xyce_relaxed92.sub"
STIM = "PWL(0 0 1n 0 1.2n 3.3 9n 3.3 9.2n 0 17n 0 17.2n 3.3 25n 3.3 25.2n 0)"
TIMEINT = ".options timeint method=trap maxord=1 erroption=1 delmax={delmax} nlmin=3 nlmax=8 timestepsreversal=1"


@dataclass(frozen=True)
class Case:
    name: str
    model: str
    stop: str
    target_ns: float
    load: str
    print_kind: str = "full"
    delmax: str = "20p"
    nx_cap: float | None = None
    kur_cap: float | None = None
    kdr_cap: float | None = None


CASES = {
    "tline_stop21": Case("tline_stop21", BASE_MODEL, "21n", 21.0, "tline"),
    "tline_stop22": Case("tline_stop22", BASE_MODEL, "22n", 22.0, "tline"),
    "tline_minprint": Case("tline_minprint", BASE_MODEL, "26n", 26.0, "tline", print_kind="minimal"),
    "tline_delmax100p": Case("tline_delmax100p", BASE_MODEL, "26n", 26.0, "tline", delmax="100p"),
    "rload": Case("rload", BASE_MODEL, "26n", 26.0, "rload"),
    "nxcap4p0": Case("nxcap4p0", "driver_OutputInput_Typical_xyce_relaxed92_nxcap4p0.sub", "26n", 26.0, "tline", nx_cap=4.0),
    "nxcap4p1": Case("nxcap4p1", "driver_OutputInput_Typical_xyce_relaxed92_nxcap4p1.sub", "26n", 26.0, "tline", nx_cap=4.1),
    "nxcap4p2": Case("nxcap4p2", "driver_OutputInput_Typical_xyce_relaxed92_nxcap4p2.sub", "26n", 26.0, "tline", nx_cap=4.2),
    "nxcap4p3": Case("nxcap4p3", "driver_OutputInput_Typical_xyce_relaxed92_nxcap4p3.sub", "26n", 26.0, "tline", nx_cap=4.3),
    "nxcap4p4": Case("nxcap4p4", "driver_OutputInput_Typical_xyce_relaxed92_nxcap4p4.sub", "26n", 26.0, "tline", nx_cap=4.4),
    "nxcap4p5": Case("nxcap4p5", "driver_OutputInput_Typical_xyce_relaxed92_nxcap4p5.sub", "26n", 26.0, "tline", nx_cap=4.5),
    "nxcap4p8": Case("nxcap4p8", "driver_OutputInput_Typical_xyce_relaxed92_nxcap4p8.sub", "26n", 26.0, "tline", nx_cap=4.8),
    "nxcap5p0": Case("nxcap5p0", "driver_OutputInput_Typical_xyce_relaxed92_nxcap5p0.sub", "26n", 26.0, "tline", nx_cap=5.0),
    "kurcap4p2": Case("kurcap4p2", "driver_OutputInput_Typical_xyce_relaxed92_kurcap4p2.sub", "26n", 26.0, "tline", kur_cap=4.2),
    "kdrcap4p2": Case("kdrcap4p2", "driver_OutputInput_Typical_xyce_relaxed92_kdrcap4p2.sub", "26n", 26.0, "tline", kdr_cap=4.2),
    "kurkdrcap4p2": Case(
        "kurkdrcap4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_kurkdrcap4p2.sub",
        "26n",
        26.0,
        "tline",
        kur_cap=4.2,
        kdr_cap=4.2,
    ),
    "rload_kurkdrcap4p2": Case(
        "rload_kurkdrcap4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_kurkdrcap4p2.sub",
        "26n",
        26.0,
        "rload",
        kur_cap=4.2,
        kdr_cap=4.2,
    ),
}


def ns(v):
    return v * 1e9


def make_capped_model(case: Case):
    if case.nx_cap is None and case.kur_cap is None and case.kdr_cap is None:
        return
    src = XYCE_DIR / BASE_MODEL
    dst = XYCE_DIR / case.model
    text = src.read_text(encoding="ascii")
    if case.nx_cap is not None:
        old = "B18 NX 0 V={min(5.96,"
        new = f"B18 NX 0 V={{min({case.nx_cap},"
        if old not in text:
            raise RuntimeError(f"Could not find NX cap expression in {src}")
        text = text.replace(old, new, 1)
    if case.kur_cap is not None or case.kdr_cap is not None:
        lines = []
        for line in text.splitlines():
            if case.kur_cap is not None and line.startswith("B20 "):
                line = line.replace(
                    "table(min(max(V(NX), 0), 5.9639999999999995),",
                    f"table(min(max(V(NX), 0), {case.kur_cap}),",
                    1,
                )
            if case.kdr_cap is not None and line.startswith("B21 "):
                line = line.replace(
                    "table(min(max(V(NX), 0), 5.9639999999999995),",
                    f"table(min(max(V(NX), 0), {case.kdr_cap}),",
                    1,
                )
            lines.append(line)
        text = "\n".join(lines) + "\n"
    dst.write_text(text, encoding="ascii")


def deck_path(case: Case) -> Path:
    return XYCE_DIR / f"tb_rootcause_{case.name}.cir"


def csv_path(case: Case) -> Path:
    return Path(str(deck_path(case)) + ".csv")


def make_deck(case: Case):
    make_capped_model(case)
    if case.load == "tline":
        load = """TVAL  pad  0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0  50"""
        ic = "V(pad)=0 V(ntst)=0"
        nodes = "V(pad) V(ntst)"
    elif case.load == "rload":
        load = "RLOAD pad 0 50"
        ic = "V(pad)=0"
        nodes = "V(pad)"
    else:
        raise ValueError(case.load)

    if case.print_kind == "minimal":
        print_line = f".print tran format=csv time V(in_dig) {nodes}"
    else:
        print_line = f".print tran format=csv time V(in_dig) {nodes} V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX) V(XDRV:N6) V(XDRV:N8) I(Vdd)"

    deck = f"""* Root-cause probe: {case.name}

Vin   in_dig   0  {STIM}
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include '{case.model}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

{load}

.ic {ic} V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
{TIMEINT.format(delmax=case.delmax)}
.options output initial_interval=10p
.tran 10p {case.stop} uic
{print_line}
.end
"""
    deck_path(case).write_text(deck, encoding="ascii")


def load_csv(path: Path):
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = []
        for row in reader:
            try:
                rows.append([float(x) for x in row])
            except ValueError:
                continue
    arr = np.asarray(rows, dtype=float)
    return {name.lower(): arr[:, i] for i, name in enumerate(header)}


def col(data, name):
    return data[name.lower()]


def run_case(case: Case, timeout_s: float):
    make_deck(case)
    out = csv_path(case)
    out.unlink(missing_ok=True)
    t0 = time.time()
    timed_out = False
    rc = None
    try:
        proc = subprocess.run(
            [str(XYCE), deck_path(case).name],
            cwd=XYCE_DIR,
            timeout=timeout_s,
            capture_output=True,
            text=True,
        )
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    wall_s = round(time.time() - t0, 2)
    row = {
        "case": case.name,
        "model": case.model,
        "load": case.load,
        "print_kind": case.print_kind,
        "delmax": case.delmax,
        "nx_cap": case.nx_cap if case.nx_cap is not None else "",
        "kur_cap": case.kur_cap if case.kur_cap is not None else "",
        "kdr_cap": case.kdr_cap if case.kdr_cap is not None else "",
        "target_ns": case.target_ns,
        "returncode": rc if rc is not None else "",
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(deck_path(case).relative_to(ROOT)).replace("\\", "/"),
        "output": str(out.relative_to(ROOT)).replace("\\", "/"),
    }
    if out.exists():
        try:
            d = load_csv(out)
            t = col(d, "time")
            row.update(
                {
                    "rows": len(t),
                    "t_end_ns": float(ns(t[-1])),
                    "completed": float(ns(t[-1])) >= case.target_ns - 0.05,
                    "vpad_last": float(col(d, "v(pad)")[-1]),
                    "vpad_max": float(np.max(col(d, "v(pad)"))),
                }
            )
            if "v(ntst)" in d:
                row["vntst_last"] = float(col(d, "v(ntst)")[-1])
                row["vntst_max"] = float(np.max(col(d, "v(ntst)")))
            if "v(xdrv:nx)" in d:
                row["nx_last"] = float(col(d, "v(xdrv:nx)")[-1])
                row["ku_last"] = float(col(d, "v(xdrv:ku)")[-1])
                row["kd_last"] = float(col(d, "v(xdrv:kd)")[-1])
        except Exception as exc:
            row["error"] = str(exc)
    else:
        row["completed"] = False
    return row


def append_metrics(rows):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "xyce_pybis_rootcause_experiments.csv"
    keys = []
    old_rows = []
    if path.exists():
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            old_rows = list(reader)
            keys.extend(reader.fieldnames or [])
    merged = old_rows + rows
    for row in merged:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(merged)
    print(path)


def plot_available():
    selected = [
        ("tline_stop22", "original tline"),
        ("rload", "Rload only"),
        ("nxcap4p0", "NX cap 4.0 ns"),
        ("nxcap4p5", "NX cap 4.5 ns"),
        ("nxcap4p8", "NX cap 4.8 ns"),
        ("nxcap5p0", "NX cap 5.0 ns"),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for name, label in selected:
        case = CASES[name]
        path = csv_path(case)
        if not path.exists():
            continue
        try:
            d = load_csv(path)
        except Exception:
            continue
        t = ns(col(d, "time"))
        axes[0].plot(t, col(d, "v(pad)"), lw=1.0, label=label)
        if "v(xdrv:nx)" in d:
            axes[1].plot(t, col(d, "v(xdrv:nx)"), lw=1.0, label=label)
    axes[0].set_ylabel("V(pad) (V)")
    axes[0].set_title("RFR200p Root-Cause Probes")
    axes[0].grid(True, alpha=0.28)
    axes[0].legend(loc="best", fontsize=8)
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_ylabel("NX (ns)")
    axes[1].grid(True, alpha=0.28)
    axes[1].legend(loc="best", fontsize=8)
    fig.tight_layout()
    path = OUT_DIR / "xyce_pybis_rootcause_experiments.png"
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--case", action="append", choices=sorted(CASES), help="Run one case; can be repeated.")
    ap.add_argument("--plot-only", action="store_true")
    args = ap.parse_args()

    if args.plot_only:
        plot_available()
        return

    names = args.case or list(CASES)
    rows = []
    for name in names:
        row = run_case(CASES[name], args.timeout)
        rows.append(row)
        t_end = row.get("t_end_ns", "n/a")
        t_end_s = f"{t_end:.3f}" if isinstance(t_end, float) else str(t_end)
        print(
            f"{name:<16} completed={row.get('completed')} timeout={row.get('timed_out')} "
            f"t_end={t_end_s} ns wall={row.get('wall_s')}s nx={row.get('nx_last', '')}"
        )
    append_metrics(rows)
    plot_available()


if __name__ == "__main__":
    main()
