from __future__ import annotations

import csv
import shutil
import struct
import subprocess
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
NGSPICE_DIR = ROOT / "ngspice_pybis"
XYCE_DIR = ROOT / "xyce_pybis"
OUT_DIR = ROOT / "results" / "prbs_rlgc_clean_2026-05-10"

NGSPICE = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")
XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")

NG_DECK = NGSPICE_DIR / "tb_clean_prbs_rlgc_ngspice.sp"
NG_RAW = NGSPICE_DIR / "tb_clean_prbs_rlgc_ngspice.raw"
XY_DECK = XYCE_DIR / "tb_clean_prbs_rlgc_xyce_edge15_flat4p2.cir"
XY_CSV = Path(str(XY_DECK) + ".csv")


NG_DECK_TEXT = """* Clean PRBS7 + pybis2spice + new 50-ohm RLGC channel
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7

.include 'prbs7_vstim.inc'
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

RCH_TX  pad tx_out 1u
.include '../new 50ohm channel/channel_ngspice.sp'
RTERM   n10b 0 50

.save V(in_dig) V(pad) V(tx_out) V(n10b)
.tran 10p 1000n
.end
"""


XY_DECK_TEXT = """* Clean Xyce pybis tail-fix: PRBS7 + new 50-ohm RLGC channel
* Current best Xyce setup: edge/latch tanh15 + flat Ku/Kd tail after 4.2 ns

.include 'prbs7_vstim.inc'
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3

.include 'driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

RCH_TX  pad tx_out 1u
.include 'channel_xyce.sp'
RTERM   n10b 0 50

.ic V(pad)=0 V(tx_out)=0 V(n10b)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
.options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
.options output initial_interval=10p
.tran 10p 1000n uic
.print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
.end
"""


def load_ngspice_raw(path: Path) -> dict[str, np.ndarray]:
    data = path.read_bytes()
    idx = data.find(b"Binary:")
    if idx < 0:
        raise RuntimeError(f"Binary marker not found in {path}")

    header = data[:idx].decode("latin1")
    lines = header.splitlines()
    nvars = npts = None
    variables: list[str] = []
    reading_vars = False
    for line in lines:
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":", 1)[1])
        elif line.strip() == "Variables:":
            reading_vars = True
        elif reading_vars and line.startswith("\t"):
            variables.append(line.split()[1].lower())

    if nvars is None or npts is None or len(variables) != nvars:
        raise RuntimeError(f"Could not parse ngspice raw header for {path}")

    payload_start = data.find(b"\n", idx)
    payload = data[payload_start + 1:]
    if npts == 0:
        npts = len(payload) // (8 * nvars)
    expected = 8 * nvars * npts
    values = struct.unpack("<" + "d" * (nvars * npts), payload[:expected])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))
    return {name: arr[:, i] for i, name in enumerate(variables)}


def load_xyce_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = [h.strip().lower() for h in next(reader)]
        rows = []
        for row in reader:
            try:
                rows.append([float(x) for x in row])
            except ValueError:
                continue

    if not rows:
        raise RuntimeError(f"No numeric rows in {path}")
    arr = np.asarray(rows, dtype=float)

    out: dict[str, np.ndarray] = {}
    seen: dict[str, int] = {}
    for i, name in enumerate(header):
        count = seen.get(name, 0)
        seen[name] = count + 1
        key = name if count == 0 else f"{name}_{count}"
        out[key] = arr[:, i]
    return out


def col(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    key = name.lower()
    if key not in data:
        raise KeyError(f"{name} not in data. Have: {sorted(data)}")
    return data[key]


def run_process(cmd: list[str], cwd: Path, timeout_s: float, log_path: Path) -> dict[str, object]:
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        timeout=timeout_s,
        capture_output=True,
        text=True,
    )
    wall_s = time.time() - started
    log_path.write_text(
        "COMMAND: " + " ".join(cmd) + "\n\n"
        f"RETURN_CODE: {proc.returncode}\n"
        f"WALL_SECONDS: {wall_s:.3f}\n\n"
        "STDOUT:\n" + proc.stdout + "\n\nSTDERR:\n" + proc.stderr,
        encoding="utf-8",
    )
    return {"return_code": proc.returncode, "wall_s": wall_s}


def summarize_waveform(label: str, data: dict[str, np.ndarray], node: str) -> dict[str, object]:
    t = col(data, "time")
    y = col(data, node)
    return {
        "simulator": label,
        "completed_1000ns": bool(t[-1] >= 999.9e-9),
        "samples": int(len(t)),
        "t_end_ns": float(t[-1] * 1e9),
        "v_n10b_min": float(np.min(y)),
        "v_n10b_max": float(np.max(y)),
        "v_n10b_final": float(y[-1]),
    }


def compare_to_ngspice(ng: dict[str, np.ndarray], xy: dict[str, np.ndarray]) -> dict[str, object]:
    t_ng = col(ng, "time")
    y_ng = col(ng, "v(n10b)")
    t_xy = col(xy, "time")
    y_xy = col(xy, "v(n10b)")
    t0 = max(t_ng[0], t_xy[0])
    t1 = min(t_ng[-1], t_xy[-1])
    grid = np.linspace(t0, t1, 20001)
    ng_i = np.interp(grid, t_ng, y_ng)
    xy_i = np.interp(grid, t_xy, y_xy)
    err = xy_i - ng_i
    return {
        "simulator": "xyce_vs_ngspice",
        "completed_1000ns": bool(t1 >= 999.9e-9),
        "samples": int(len(grid)),
        "t_end_ns": float(t1 * 1e9),
        "v_n10b_min": "",
        "v_n10b_max": "",
        "v_n10b_final": "",
        "rmse_mV": float(np.sqrt(np.mean(err * err)) * 1e3),
        "max_abs_error_mV": float(np.max(np.abs(err)) * 1e3),
        "mean_error_mV": float(np.mean(err) * 1e3),
    }


def write_metrics(rows: list[dict[str, object]], out: Path) -> None:
    fieldnames = [
        "simulator",
        "completed_1000ns",
        "samples",
        "t_end_ns",
        "v_n10b_min",
        "v_n10b_max",
        "v_n10b_final",
        "rmse_mV",
        "max_abs_error_mV",
        "mean_error_mV",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot_overlay(ng: dict[str, np.ndarray], xy: dict[str, np.ndarray], out: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=False)

    t_ng = col(ng, "time") * 1e9
    t_xy = col(xy, "time") * 1e9
    for ax, window in zip(axes, [(0, 1000), (650, 750)]):
        ax.plot(t_ng, col(ng, "v(n10b)"), label="ngspice direct pybis", lw=1.0)
        ax.plot(t_xy, col(xy, "v(n10b)"), label="Xyce edge15 flat4p2", lw=0.9, alpha=0.85)
        ax.set_xlim(*window)
        ax.set_ylabel("V(n10b) (V)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=8)
    axes[0].set_title("Clean PRBS7 + 50-ohm RLGC Channel Transient")
    axes[1].set_title("Zoom")
    axes[1].set_xlabel("Time (ns)")
    fig.tight_layout()
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ngspice").mkdir(exist_ok=True)
    (OUT_DIR / "xyce").mkdir(exist_ok=True)
    (OUT_DIR / "plots").mkdir(exist_ok=True)

    NG_DECK.write_text(NG_DECK_TEXT, encoding="ascii")
    XY_DECK.write_text(XY_DECK_TEXT, encoding="ascii")

    NG_RAW.unlink(missing_ok=True)
    XY_CSV.unlink(missing_ok=True)

    ng_log = OUT_DIR / "ngspice" / "tb_clean_prbs_rlgc_ngspice.log"
    xy_log = OUT_DIR / "xyce" / "tb_clean_prbs_rlgc_xyce_edge15_flat4p2.log"

    print("Running ngspice clean PRBS+RLGC...")
    ng_run = run_process(
        [str(NGSPICE), "-b", "-r", NG_RAW.name, NG_DECK.name],
        NGSPICE_DIR,
        240.0,
        ng_log,
    )
    print(f"  ngspice rc={ng_run['return_code']} wall={ng_run['wall_s']:.2f}s")

    print("Running Xyce clean PRBS+RLGC...")
    xy_run = run_process(
        [str(XYCE), XY_DECK.name],
        XYCE_DIR,
        240.0,
        xy_log,
    )
    print(f"  Xyce rc={xy_run['return_code']} wall={xy_run['wall_s']:.2f}s")

    for src, dst_dir in [
        (NG_DECK, OUT_DIR / "ngspice"),
        (NG_RAW, OUT_DIR / "ngspice"),
        (XY_DECK, OUT_DIR / "xyce"),
        (XY_CSV, OUT_DIR / "xyce"),
    ]:
        if not src.exists():
            raise RuntimeError(f"Expected output missing: {src}")
        shutil.copy2(src, dst_dir / src.name)

    ng = load_ngspice_raw(NG_RAW)
    xy = load_xyce_csv(XY_CSV)
    rows = [
        summarize_waveform("ngspice_direct_pybis", ng, "v(n10b)"),
        summarize_waveform("xyce_edge15_flat4p2", xy, "v(n10b)"),
        compare_to_ngspice(ng, xy),
    ]
    write_metrics(rows, OUT_DIR / "prbs_rlgc_clean_metrics.csv")
    plot_overlay(ng, xy, OUT_DIR / "plots" / "prbs_rlgc_clean_ngspice_vs_xyce_overlay.png")

    summary = [
        "Clean PRBS7 + 50-ohm RLGC channel rerun",
        f"ngspice return code: {ng_run['return_code']}, wall_s: {ng_run['wall_s']:.3f}",
        f"Xyce return code: {xy_run['return_code']}, wall_s: {xy_run['wall_s']:.3f}",
        f"ngspice t_end_ns: {rows[0]['t_end_ns']:.3f}, samples: {rows[0]['samples']}",
        f"Xyce t_end_ns: {rows[1]['t_end_ns']:.3f}, samples: {rows[1]['samples']}",
        f"Xyce vs ngspice V(n10b) RMSE mV: {rows[2]['rmse_mV']:.3f}",
        f"Xyce vs ngspice V(n10b) max abs error mV: {rows[2]['max_abs_error_mV']:.3f}",
    ]
    (OUT_DIR / "README.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"Saved clean results to {OUT_DIR}")


if __name__ == "__main__":
    main()
