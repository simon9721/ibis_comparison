from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402


OUT_DIR = ROOT / "results" / "agilent_io_buf_ibis_bbs_transient_2026-06-19"
HSPICE_DIR = OUT_DIR / "hspice_native_ibis_sparam"
NGSPICE_DIR = OUT_DIR / "ngspice_pybis_bbs"
PLOTS_DIR = OUT_DIR / "plots"
ARTIFACTS_DIR = OUT_DIR / "artifacts"

IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
AGILENT_S4P = ROOT / "results" / "agilent_e5071b_bbs_s4p_overlay_2026-06-19" / "artifacts" / "Agilent_E5071B_original.s4p"
BBS_GSPICE = ROOT / "results" / "agilent_e5071b_bbs_s4p_overlay_2026-06-19" / "artifacts" / "Agilent_E5071B_GSPICE.txt"
NGSPICE_EXE = Path(r"\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin\ngspice.exe")

TRAN_STEP = "2p"
TRAN_STOP = "12n"
EDGE_S = 5e-12
VDD = 3.3
Z0 = 75.0


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def copy2(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def run_process(cmd: list[str], cwd: Path, log_path: Path, timeout_s: int = 300) -> int:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_s,
    )
    log_path.write_text("COMMAND: " + " ".join(cmd) + "\n\n" + proc.stdout, encoding="utf-8", errors="replace")
    return int(proc.returncode)


def hspice_deck() -> str:
    return f"""* HSPICE: io_buf native IBIS driving Agilent_E5071B.s4p
* Port convention: p1=Tx driven by IBIS, p2=near-side unused, p3=RX observed, p4=far-side unused.
* All non-driven channel ports are matched to {Z0:g} ohms, matching the Touchstone R 75 reference.
.option post=2 probe accurate
.option ingold=2
.temp 27

VPU  pu_ref  0  DC {VDD:g}
VPD  pd_ref  0  DC 0
VPC  pc_ref  0  DC {VDD:g}
VGC  gc_ref  0  DC 0

Vin  in_dig  0  PWL(0 0 1n 0 {1e-9 + EDGE_S:.12g} {VDD:g} 9n {VDD:g} {9e-9 + EDGE_S:.12g} 0)
Ven  en_sig  0  DC {VDD:g}

BIBIS pu_ref pd_ref p1 in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2

Rdig  dig_q  0  1k

Schannel  p1  p2  p3  p4  0  MNAME=agilent_ch
Rterm_p2  p2  0  {Z0:g}
Rterm_p3  p3  0  {Z0:g}
Rterm_p4  p4  0  {Z0:g}

.MODEL agilent_ch S
+ TSTONEFILE='Agilent_E5071B.s4p'
+ Z0={Z0:g}
+ RATIONAL_FUNC=1
+ INTERPOLATION=HYBRID
+ LOWPASS=1
+ HIGHPASS=3
+ PASSIVE=1

.probe tran V(in_dig) V(p1) V(p2) V(p3) V(p4) V(dig_q)
.tran {TRAN_STEP} {TRAN_STOP}
.end
"""


def ngspice_wrapper() -> str:
    return """* Local ngspice wrapper for BBS General SPICE output
.include 'Agilent_E5071B_GSPICE.txt'
.subckt s_equivalent p1 p2 p3 p4
Xbbs p1 p2 p3 p4 0 Agilent_E5071B_GSPICE
.ends s_equivalent
"""


def ngspice_deck() -> str:
    return f"""* ngspice: pybis io_buf driving BBS converted Agilent_E5071B channel
* Port convention matches HSPICE deck: p1=Tx, p3=RX observed.
.temp 27
.options method=gear maxord=2 reltol=2e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin  in_dig  0  PWL(0 0 1n 0 {1e-9 + EDGE_S:.12g} {VDD:g} 9n {VDD:g} {9e-9 + EDGE_S:.12g} 0)
Ven  en_sig  0  DC {VDD:g}
Vdd  vdd     0  DC {VDD:g}

.include 'driver_OutputInput_Typical.sub'
XDRV  p1  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

.include 'agilent_bbs_wrapper.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rterm_p2  p2  0  {Z0:g}
Rterm_p3  p3  0  {Z0:g}
Rterm_p4  p4  0  {Z0:g}

.save V(in_dig) V(p1) V(p2) V(p3) V(p4) V(xdrv.ku) V(xdrv.kd)
.tran {TRAN_STEP} {TRAN_STOP}
.end
"""


def signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    by_lower = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = by_lower.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    raise KeyError(f"Missing {names}; available={sorted(data)}")


def interp(src_t: np.ndarray, src_y: np.ndarray, dst_t: np.ndarray) -> np.ndarray:
    return np.interp(dst_t, src_t, src_y)


def metric_rows(h: dict[str, np.ndarray], n: dict[str, np.ndarray]) -> list[dict[str, object]]:
    ht = signal(h, "time")
    nt = signal(n, "time")
    rows = []
    for node in ["p1", "p2", "p3", "p4", "in_dig"]:
        hs = signal(h, f"v({node})")
        ns = signal(n, f"v({node})")
        ni = interp(nt, ns, ht)
        diff = ni - hs
        active = (ht >= 0.8e-9) & (ht <= 11.5e-9)
        rows.append(
            {
                "node": node,
                "rmse_v": float(np.sqrt(np.mean(diff**2))),
                "maxabs_v": float(np.max(np.abs(diff))),
                "active_rmse_v": float(np.sqrt(np.mean(diff[active] ** 2))),
                "active_maxabs_v": float(np.max(np.abs(diff[active]))),
                "hspice_min_v": float(np.min(hs)),
                "hspice_max_v": float(np.max(hs)),
                "ngspice_min_v": float(np.min(ns)),
                "ngspice_max_v": float(np.max(ns)),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_waveforms(path: Path, h: dict[str, np.ndarray], n: dict[str, np.ndarray]) -> None:
    ht = signal(h, "time")
    nt = signal(n, "time")
    cols: dict[str, np.ndarray] = {"time_ns": ht * 1e9}
    for node in ["in_dig", "p1", "p2", "p3", "p4"]:
        cols[f"hspice_{node}_v"] = signal(h, f"v({node})")
        cols[f"ngspice_{node}_v"] = interp(nt, signal(n, f"v({node})"), ht)
    keys = list(cols)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for idx in range(len(ht)):
            writer.writerow([cols[key][idx] for key in keys])


def plot_overlay(h: dict[str, np.ndarray], n: dict[str, np.ndarray], path: Path) -> None:
    ht = signal(h, "time") * 1e9
    nt = signal(n, "time") * 1e9
    fig, axes = plt.subplots(4, 1, figsize=(11.0, 10.0), sharex=True, constrained_layout=True)
    specs = [
        ("v(in_dig)", "Input stimulus"),
        ("v(p1)", "TX / channel port 1"),
        ("v(p3)", "RX / channel port 3"),
        ("v(p2)", "Terminated port 2"),
    ]
    for ax, (sig, title) in zip(axes, specs):
        ax.plot(ht, signal(h, sig), lw=1.8, label="HSPICE native IBIS + S-element")
        ax.plot(nt, signal(n, sig), "--", lw=1.5, label="ngspice pybis + BBS SPICE")
        ax.set_ylabel("V")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.grid(True, color="#d7dde6")
        ax.legend(frameon=False, fontsize=8)
    axes[-1].set_xlabel("Time (ns)")
    fig.suptitle("io_buf over Agilent_E5071B.s4p: HSPICE native IBIS/S-param vs ngspice pybis/BBS", fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_side(h: dict[str, np.ndarray], n: dict[str, np.ndarray], node: str, title: str, path: Path) -> None:
    ht = signal(h, "time") * 1e9
    nt = signal(n, "time") * 1e9
    fig, ax = plt.subplots(figsize=(10.5, 5.4), constrained_layout=True)
    ax.plot(ht, signal(h, f"v({node})"), lw=2.0, label="HSPICE native IBIS + S-element")
    ax.plot(nt, signal(n, f"v({node})"), "--", lw=1.7, label="ngspice pybis + BBS SPICE")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, color="#d7dde6")
    ax.legend(frameon=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def write_readme(h_code: int, n_code: int, rows: list[dict[str, object]]) -> None:
    metric_lines = [
        "| Node | RMSE V | Max Abs V | Active RMSE V | Active Max Abs V | HSPICE range V | ngspice range V |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        metric_lines.append(
            "| {node} | {rmse_v:.6g} | {maxabs_v:.6g} | {active_rmse_v:.6g} | {active_maxabs_v:.6g} | {hlo:.6g}..{hhi:.6g} | {nlo:.6g}..{nhi:.6g} |".format(
                node=row["node"],
                rmse_v=float(row["rmse_v"]),
                maxabs_v=float(row["maxabs_v"]),
                active_rmse_v=float(row["active_rmse_v"]),
                active_maxabs_v=float(row["active_maxabs_v"]),
                hlo=float(row["hspice_min_v"]),
                hhi=float(row["hspice_max_v"]),
                nlo=float(row["ngspice_min_v"]),
                nhi=float(row["ngspice_max_v"]),
            )
        )
    text = [
        "# Agilent Channel io_buf Transient: HSPICE IBIS vs ngspice pybis/BBS",
        "",
        "This run compares the requested nonlinear-driver transient setup:",
        "",
        "- HSPICE: native `io_buf.ibs` IBIS instance driving native S-parameter `Agilent_E5071B.s4p`.",
        "- ngspice: pybis-converted `io_buf.ibs` driver driving the BBS General SPICE conversion of the same Agilent channel.",
        "",
        "## Bench Setup",
        "",
        f"- IBIS source: `{IBIS}`",
        f"- Original channel: `{AGILENT_S4P}`",
        f"- BBS model: `{BBS_GSPICE}`",
        f"- Port convention: `p1` driven Tx, `p3` observed RX, `p2` and `p4` unused/terminated.",
        f"- Terminations: `p2`, `p3`, and `p4` each to `{Z0:g} ohms`, matching the Agilent Touchstone `R 75` reference.",
        f"- Stimulus: `0 -> 3.3 V` at `1 ns`, `3.3 -> 0 V` at `9 ns`, `{EDGE_S * 1e12:g} ps` edge.",
        f"- Transient: `.tran {TRAN_STEP} {TRAN_STOP}`.",
        "",
        "## Run Status",
        "",
        f"- HSPICE return code: `{h_code}`",
        f"- ngspice return code: `{n_code}`",
        "",
        "## Plots",
        "",
        "- `plots/01_all_overlay.png`",
        "- `plots/02_tx_p1_overlay.png`",
        "- `plots/03_rx_p3_overlay.png`",
        "- `plots/04_far_terminated_p4_overlay.png`",
        "",
        "## Metrics",
        "",
        *metric_lines,
        "",
        "## Artifacts",
        "",
        "- `hspice_native_ibis_sparam/agilent_io_buf_hspice.sp`",
        "- `hspice_native_ibis_sparam/agilent_io_buf_hspice.tr0`",
        "- `ngspice_pybis_bbs/agilent_io_buf_ngspice.sp`",
        "- `ngspice_pybis_bbs/agilent_io_buf_ngspice.raw`",
        "- `ngspice_pybis_bbs/driver_OutputInput_Typical.sub`",
        "- `ngspice_pybis_bbs/Agilent_E5071B_GSPICE.txt`",
        "",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(text), encoding="utf-8")


def main() -> None:
    for path in [HSPICE_DIR, NGSPICE_DIR, PLOTS_DIR, ARTIFACTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    copy2(IBIS, HSPICE_DIR / "io_buf.ibs")
    copy2(IBIS, NGSPICE_DIR / "io_buf.ibs")
    copy2(IBIS, ARTIFACTS_DIR / "io_buf.ibs")
    copy2(AGILENT_S4P, HSPICE_DIR / "Agilent_E5071B.s4p")
    copy2(AGILENT_S4P, ARTIFACTS_DIR / "Agilent_E5071B.s4p")
    copy2(BBS_GSPICE, NGSPICE_DIR / "Agilent_E5071B_GSPICE.txt")
    copy2(BBS_GSPICE, ARTIFACTS_DIR / "Agilent_E5071B_GSPICE.txt")

    driver_sub = NGSPICE_DIR / "driver_OutputInput_Typical.sub"
    convert_ibis_to_pybis(
        ibis_path=NGSPICE_DIR / "io_buf.ibs",
        output_path=driver_sub,
        component_name="MCM Driver 1",
        model_name="driver",
        io_type="Output",
        subcircuit_type="InputDriven",
        corner="Typical",
    )

    write_text(NGSPICE_DIR / "agilent_bbs_wrapper.sp", ngspice_wrapper())
    write_text(HSPICE_DIR / "agilent_io_buf_hspice.sp", hspice_deck())
    write_text(NGSPICE_DIR / "agilent_io_buf_ngspice.sp", ngspice_deck())

    h_code = run_process(
        ["hspice", "-i", "agilent_io_buf_hspice.sp", "-o", "agilent_io_buf_hspice"],
        HSPICE_DIR,
        HSPICE_DIR / "hspice_stdout.log",
        timeout_s=300,
    )
    n_code = run_process(
        [str(NGSPICE_EXE), "-b", "-r", "agilent_io_buf_ngspice.raw", "-o", "agilent_io_buf_ngspice.log", "agilent_io_buf_ngspice.sp"],
        NGSPICE_DIR,
        NGSPICE_DIR / "ngspice_stdout.log",
        timeout_s=600,
    )

    if h_code != 0 or n_code != 0:
        write_readme(h_code, n_code, [])
        raise SystemExit(f"simulation failed: hspice={h_code}, ngspice={n_code}")

    h = parse_hspice_tr0(HSPICE_DIR / "agilent_io_buf_hspice.tr0")
    n = parse_ngspice_raw(NGSPICE_DIR / "agilent_io_buf_ngspice.raw")
    rows = metric_rows(h, n)
    write_csv(OUT_DIR / "metrics.csv", rows)
    write_waveforms(OUT_DIR / "aligned_waveforms.csv", h, n)

    plot_overlay(h, n, PLOTS_DIR / "01_all_overlay.png")
    plot_side(h, n, "p1", "TX side p1: io_buf output / channel input", PLOTS_DIR / "02_tx_p1_overlay.png")
    plot_side(h, n, "p3", "RX side p3: matched 75 ohm output", PLOTS_DIR / "03_rx_p3_overlay.png")
    plot_side(h, n, "p4", "Far terminated port p4", PLOTS_DIR / "04_far_terminated_p4_overlay.png")
    write_readme(h_code, n_code, rows)

    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"HSPICE_TR0={HSPICE_DIR / 'agilent_io_buf_hspice.tr0'}")
    print(f"NGSPICE_RAW={NGSPICE_DIR / 'agilent_io_buf_ngspice.raw'}")


if __name__ == "__main__":
    main()
