from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_agilent_ibis_bbs_transient as base  # noqa: E402


OUT_DIR = ROOT / "results" / "agilent_io_buf_ibis_bbs_pulsetrain_2026-06-19"
HSPICE_DIR = OUT_DIR / "hspice_native_ibis_sparam"
NGSPICE_DIR = OUT_DIR / "ngspice_pybis_bbs"
PLOTS_DIR = OUT_DIR / "plots"
ARTIFACTS_DIR = OUT_DIR / "artifacts"
PROFILE = "fast_1ns"

EDGE_S = 5e-12
VDD = 3.3
Z0 = 75.0
SRC_SERIES_OHM = 0.0
FIRST_RISE_S = 1e-9
HIGH_S = 1e-9
LOW_S = 1e-9
PULSE_COUNT = 10
TRAN_STEP = "2p"
TRAN_STOP_S = FIRST_RISE_S + PULSE_COUNT * (HIGH_S + LOW_S) + 3e-9
ZOOM_NS = (15.0, 22.0)


def configure_profile(profile: str) -> None:
    global OUT_DIR, HSPICE_DIR, NGSPICE_DIR, PLOTS_DIR, ARTIFACTS_DIR
    global PROFILE, EDGE_S, HIGH_S, LOW_S, PULSE_COUNT, TRAN_STOP_S, ZOOM_NS, SRC_SERIES_OHM

    PROFILE = profile
    EDGE_S = 5e-12
    SRC_SERIES_OHM = 0.0
    if profile == "fast_1ns":
        OUT_DIR = ROOT / "results" / "agilent_io_buf_ibis_bbs_pulsetrain_2026-06-19"
        HIGH_S = 1e-9
        LOW_S = 1e-9
        PULSE_COUNT = 10
        ZOOM_NS = (15.0, 22.0)
    elif profile == "settled_5ns":
        OUT_DIR = ROOT / "results" / "agilent_io_buf_ibis_bbs_pulsetrain_settled_2026-06-19"
        HIGH_S = 5e-9
        LOW_S = 5e-9
        PULSE_COUNT = 4
        ZOOM_NS = (21.0, 36.0)
    elif profile == "settled_5ns_slow500ps_src75":
        OUT_DIR = ROOT / "results" / "agilent_io_buf_ibis_bbs_pulsetrain_damped_2026-06-19"
        EDGE_S = 500e-12
        SRC_SERIES_OHM = Z0
        HIGH_S = 5e-9
        LOW_S = 5e-9
        PULSE_COUNT = 4
        ZOOM_NS = (21.0, 36.0)
    else:
        raise ValueError(f"unknown profile {profile!r}")

    TRAN_STOP_S = FIRST_RISE_S + PULSE_COUNT * (HIGH_S + LOW_S) + 3e-9
    HSPICE_DIR = OUT_DIR / "hspice_native_ibis_sparam"
    NGSPICE_DIR = OUT_DIR / "ngspice_pybis_bbs"
    PLOTS_DIR = OUT_DIR / "plots"
    ARTIFACTS_DIR = OUT_DIR / "artifacts"


def pwl_points() -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = [(0.0, 0.0), (FIRST_RISE_S, 0.0)]
    t = FIRST_RISE_S
    for _ in range(PULSE_COUNT):
        points.append((t + EDGE_S, VDD))
        t += HIGH_S
        points.append((t, VDD))
        points.append((t + EDGE_S, 0.0))
        t += LOW_S
        points.append((t, 0.0))
    points.append((TRAN_STOP_S, 0.0))
    return points


def pwl_text() -> str:
    lines = ["PWL("]
    for idx, (time_s, value_v) in enumerate(pwl_points()):
        suffix = ")" if idx == len(pwl_points()) - 1 else ""
        lines.append(f"+ {time_s:.12g} {value_v:.12g}{suffix}")
    return "\n".join(lines)


def driver_output_node() -> str:
    return "drv_out" if SRC_SERIES_OHM > 0 else "p1"


def source_series_text() -> str:
    if SRC_SERIES_OHM <= 0:
        return ""
    return f"Rsrc  drv_out  p1  {SRC_SERIES_OHM:g}\n"


def hspice_deck() -> str:
    return f"""* HSPICE: io_buf native IBIS driving Agilent_E5071B.s4p, repeated pulses
* Port convention: p1=Tx driven by IBIS, p2=near-side unused, p3=RX observed, p4=far-side unused.
* All non-driven channel ports are matched to {Z0:g} ohms, matching the Touchstone R 75 reference.
.option post=2 probe accurate
.option ingold=2
.temp 27

VPU  pu_ref  0  DC {VDD:g}
VPD  pd_ref  0  DC 0
VPC  pc_ref  0  DC {VDD:g}
VGC  gc_ref  0  DC 0

Vin  in_dig  0  {pwl_text()}
Ven  en_sig  0  DC {VDD:g}

BIBIS pu_ref pd_ref {driver_output_node()} in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2

Rdig  dig_q  0  1k
{source_series_text()}

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
.tran {TRAN_STEP} {TRAN_STOP_S:.12g}
.end
"""


def ngspice_deck() -> str:
    return f"""* ngspice: pybis io_buf driving BBS converted Agilent_E5071B channel, repeated pulses
* Port convention matches HSPICE deck: p1=Tx, p3=RX observed.
.temp 27
.options method=gear maxord=2 reltol=2e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin  in_dig  0  {pwl_text()}
Ven  en_sig  0  DC {VDD:g}
Vdd  vdd     0  DC {VDD:g}

.include 'driver_OutputInput_Typical.sub'
XDRV  {driver_output_node()}  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
{source_series_text()}

.include 'agilent_bbs_wrapper.sp'
Xchannel  p1  p2  p3  p4  s_equivalent
Rterm_p2  p2  0  {Z0:g}
Rterm_p3  p3  0  {Z0:g}
Rterm_p4  p4  0  {Z0:g}

.save V(in_dig) V(p1) V(p2) V(p3) V(p4) V(xdrv.ku) V(xdrv.kd)
.tran {TRAN_STEP} {TRAN_STOP_S:.12g}
.end
"""


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


def metric_rows(h: dict[str, np.ndarray], n: dict[str, np.ndarray]) -> list[dict[str, object]]:
    ht = base.signal(h, "time")
    nt = base.signal(n, "time")
    rows = []
    active = (ht >= 0.8e-9) & (ht <= (TRAN_STOP_S - 0.2e-9))
    steady = (ht >= 15e-9) & (ht <= 22e-9)
    for node in ["p1", "p2", "p3", "p4", "in_dig"]:
        hs = base.signal(h, f"v({node})")
        ni = base.interp(nt, base.signal(n, f"v({node})"), ht)
        diff = ni - hs
        rows.append(
            {
                "node": node,
                "rmse_v": float(np.sqrt(np.mean(diff**2))),
                "maxabs_v": float(np.max(np.abs(diff))),
                "active_rmse_v": float(np.sqrt(np.mean(diff[active] ** 2))),
                "active_maxabs_v": float(np.max(np.abs(diff[active]))),
                "steady_rmse_v": float(np.sqrt(np.mean(diff[steady] ** 2))),
                "steady_maxabs_v": float(np.max(np.abs(diff[steady]))),
                "hspice_min_v": float(np.min(hs)),
                "hspice_max_v": float(np.max(hs)),
                "ngspice_min_v": float(np.min(ni)),
                "ngspice_max_v": float(np.max(ni)),
            }
        )
    return rows


def plot_overlay(h: dict[str, np.ndarray], n: dict[str, np.ndarray], path: Path, *, zoom: tuple[float, float] | None = None) -> None:
    ht = base.signal(h, "time") * 1e9
    nt = base.signal(n, "time") * 1e9
    fig, axes = plt.subplots(4, 1, figsize=(11.0, 10.0), sharex=True, constrained_layout=True)
    specs = [
        ("v(in_dig)", "Input pulse train"),
        ("v(p1)", "TX / channel port 1"),
        ("v(p3)", "RX / channel port 3"),
        ("v(p2)", "Terminated port 2"),
    ]
    for ax, (sig, title) in zip(axes, specs):
        ax.plot(ht, base.signal(h, sig), lw=1.8, label="HSPICE native IBIS + S-element")
        ax.plot(nt, base.signal(n, sig), "--", lw=1.5, label="ngspice pybis + BBS SPICE")
        ax.set_ylabel("V")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.grid(True, color="#d7dde6")
        ax.legend(frameon=False, fontsize=8)
        if zoom:
            ax.set_xlim(*zoom)
    axes[-1].set_xlabel("Time (ns)")
    title = "io_buf over Agilent_E5071B.s4p pulse train"
    if zoom:
        title += f" ({zoom[0]:g}-{zoom[1]:g} ns zoom)"
    fig.suptitle(title, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_side(h: dict[str, np.ndarray], n: dict[str, np.ndarray], node: str, title: str, path: Path, *, zoom: tuple[float, float] | None = None) -> None:
    ht = base.signal(h, "time") * 1e9
    nt = base.signal(n, "time") * 1e9
    fig, ax = plt.subplots(figsize=(10.5, 5.4), constrained_layout=True)
    ax.plot(ht, base.signal(h, f"v({node})"), lw=2.0, label="HSPICE native IBIS + S-element")
    ax.plot(nt, base.signal(n, f"v({node})"), "--", lw=1.7, label="ngspice pybis + BBS SPICE")
    if zoom:
        ax.set_xlim(*zoom)
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
        "| Node | Active RMSE V | Active Max Abs V | Steady RMSE V | Steady Max Abs V | HSPICE range V | ngspice range V |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        metric_lines.append(
            "| {node} | {active_rmse_v:.6g} | {active_maxabs_v:.6g} | {steady_rmse_v:.6g} | {steady_maxabs_v:.6g} | {hlo:.6g}..{hhi:.6g} | {nlo:.6g}..{nhi:.6g} |".format(
                node=row["node"],
                active_rmse_v=float(row["active_rmse_v"]),
                active_maxabs_v=float(row["active_maxabs_v"]),
                steady_rmse_v=float(row["steady_rmse_v"]),
                steady_maxabs_v=float(row["steady_maxabs_v"]),
                hlo=float(row["hspice_min_v"]),
                hhi=float(row["hspice_max_v"]),
                nlo=float(row["ngspice_min_v"]),
                nhi=float(row["ngspice_max_v"]),
            )
        )
    text = [
        "# Agilent Channel io_buf Pulse Train: HSPICE IBIS vs ngspice pybis/BBS",
        "",
        "This is the repeated-pulse version of the Agilent channel transient comparison. It uses the same models and 75 ohm matched terminations as the single-pulse run, but drives multiple pulses so the RX response is dominated by repeated excitation instead of one isolated ring-down.",
        "",
        "## Bench Setup",
        "",
        f"- Profile: `{PROFILE}`.",
        f"- Pulse train: `{PULSE_COUNT}` pulses, `{HIGH_S * 1e9:g} ns` high, `{LOW_S * 1e9:g} ns` low.",
        f"- Edge rate: `{EDGE_S * 1e12:g} ps`.",
        f"- Source series resistor: `{SRC_SERIES_OHM:g} ohms` between the IBIS output and channel p1.",
        f"- Terminations: `p2`, `p3`, and `p4` each to `{Z0:g} ohms`, matching the Agilent Touchstone `R 75` reference.",
        "- Port convention: `p1` driven Tx, `p3` observed RX, `p2` and `p4` unused/terminated.",
        f"- Transient: `.tran {TRAN_STEP} {TRAN_STOP_S:.12g}`.",
        "",
        "## Run Status",
        "",
        f"- HSPICE return code: `{h_code}`",
        f"- ngspice return code: `{n_code}`",
        "",
        "## Plots",
        "",
        "- `plots/01_all_pulsetrain_overlay.png`",
        "- `plots/02_all_pulsetrain_zoom.png`",
        "- `plots/03_tx_p1_zoom.png`",
        "- `plots/04_rx_p3_zoom.png`",
        "",
        "## Metrics",
        "",
        *metric_lines,
        "",
        "## Interpretation",
        "",
        "This does not remove the channel's natural decay; it keeps exciting the channel before the previous response fully dies out. That makes the overlay easier to compare for repeated digital activity, but it is still a band-pass/coupled channel response rather than a DC-settling digital through path.",
        "",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(text), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repeated-pulse Agilent io_buf HSPICE-vs-ngspice comparison.")
    parser.add_argument(
        "--profile",
        choices=["fast_1ns", "settled_5ns", "settled_5ns_slow500ps_src75"],
        default="fast_1ns",
    )
    args = parser.parse_args()
    configure_profile(args.profile)

    for path in [HSPICE_DIR, NGSPICE_DIR, PLOTS_DIR, ARTIFACTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    base.copy2(base.IBIS, HSPICE_DIR / "io_buf.ibs")
    base.copy2(base.IBIS, NGSPICE_DIR / "io_buf.ibs")
    base.copy2(base.IBIS, ARTIFACTS_DIR / "io_buf.ibs")
    base.copy2(base.AGILENT_S4P, HSPICE_DIR / "Agilent_E5071B.s4p")
    base.copy2(base.AGILENT_S4P, ARTIFACTS_DIR / "Agilent_E5071B.s4p")
    base.copy2(base.BBS_GSPICE, NGSPICE_DIR / "Agilent_E5071B_GSPICE.txt")
    base.copy2(base.BBS_GSPICE, ARTIFACTS_DIR / "Agilent_E5071B_GSPICE.txt")

    base.convert_ibis_to_pybis(
        ibis_path=NGSPICE_DIR / "io_buf.ibs",
        output_path=NGSPICE_DIR / "driver_OutputInput_Typical.sub",
        component_name="MCM Driver 1",
        model_name="driver",
        io_type="Output",
        subcircuit_type="InputDriven",
        corner="Typical",
    )

    base.write_text(NGSPICE_DIR / "agilent_bbs_wrapper.sp", base.ngspice_wrapper())
    base.write_text(HSPICE_DIR / "agilent_io_buf_hspice_pulsetrain.sp", hspice_deck())
    base.write_text(NGSPICE_DIR / "agilent_io_buf_ngspice_pulsetrain.sp", ngspice_deck())

    h_code = base.run_process(
        ["hspice", "-i", "agilent_io_buf_hspice_pulsetrain.sp", "-o", "agilent_io_buf_hspice_pulsetrain"],
        HSPICE_DIR,
        HSPICE_DIR / "hspice_stdout.log",
        timeout_s=420,
    )
    n_code = base.run_process(
        [
            str(base.NGSPICE_EXE),
            "-b",
            "-r",
            "agilent_io_buf_ngspice_pulsetrain.raw",
            "-o",
            "agilent_io_buf_ngspice_pulsetrain.log",
            "agilent_io_buf_ngspice_pulsetrain.sp",
        ],
        NGSPICE_DIR,
        NGSPICE_DIR / "ngspice_stdout.log",
        timeout_s=900,
    )

    if h_code != 0 or n_code != 0:
        write_readme(h_code, n_code, [])
        raise SystemExit(f"simulation failed: hspice={h_code}, ngspice={n_code}")

    h = base.parse_hspice_tr0(HSPICE_DIR / "agilent_io_buf_hspice_pulsetrain.tr0")
    n = base.parse_ngspice_raw(NGSPICE_DIR / "agilent_io_buf_ngspice_pulsetrain.raw")
    rows = metric_rows(h, n)
    write_csv(OUT_DIR / "metrics.csv", rows)
    base.write_waveforms(OUT_DIR / "aligned_waveforms.csv", h, n)

    plot_overlay(h, n, PLOTS_DIR / "01_all_pulsetrain_overlay.png")
    plot_overlay(h, n, PLOTS_DIR / "02_all_pulsetrain_zoom.png", zoom=ZOOM_NS)
    plot_side(h, n, "p1", "TX side p1 pulse train zoom", PLOTS_DIR / "03_tx_p1_zoom.png", zoom=ZOOM_NS)
    plot_side(h, n, "p3", "RX side p3 pulse train zoom", PLOTS_DIR / "04_rx_p3_zoom.png", zoom=ZOOM_NS)
    write_readme(h_code, n_code, rows)

    print(f"OUT_DIR={OUT_DIR}")
    print(f"README={OUT_DIR / 'README.md'}")
    print(f"HSPICE_TR0={HSPICE_DIR / 'agilent_io_buf_hspice_pulsetrain.tr0'}")
    print(f"NGSPICE_RAW={NGSPICE_DIR / 'agilent_io_buf_ngspice_pulsetrain.raw'}")


if __name__ == "__main__":
    main()
