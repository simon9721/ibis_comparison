from __future__ import annotations

import csv
import os
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
from hspice_reference_cache import cache_dir, reference_signature, restore as restore_hspice_cache, save as save_hspice_cache  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402


OUT_DIR = ROOT / "results" / "io_buf_switching_coeff_overlay_2026-06-18"
HSPICE_DIR = OUT_DIR / "hspice_native_ibis"
NGSPICE_DIR = OUT_DIR / "ngspice_pybis"
PLOTS_DIR = OUT_DIR / "plots"
DEFAULT_IBIS = ROOT / "hspice" / "sparam" / "io_buf.ibs"
DEFAULT_NGSPICE = default_ngspice(console=True)
DEFAULT_HSPICE = default_hspice()


def clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def run_process(cmd: list[str], cwd: Path, log_path: Path, timeout_s: int = 180) -> int:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_s,
    )
    log_path.write_text("COMMAND: " + " ".join(cmd) + "\n\n" + proc.stdout, encoding="utf-8")
    return int(proc.returncode)


def make_hspice_deck() -> str:
    return """* io_buf native IBIS HSPICE switching coefficient extraction
* Based on ibis_switching_coeff_tb.sp, adapted to io_buf.ibs and 3.3 V logic.
.title io_buf HSPICE native IBIS Ku/Kd extraction
.option post=2 probe accurate
.option ingold=2
.temp 27

Vin in_dig 0 PWL(
+ 0n      0
+ 5n      0
+ 5.001n  3.3
+ 15n     3.3
+ 15.001n 0
+ 25n     0 )

Ven en_sig 0 DC 3.3
VPU pu_ref 0 DC 3.3
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC 3.3
VGC gc_ref 0 DC 0

BIBIS pu_ref pd_ref pad_ibis in_dig en_sig dig_q pc_ref gc_ref
+ file='io_buf.ibs'
+ model='driver'
+ typ=typ
+ power=off
+ interpol=1
+ ramp_rwf=2
+ ramp_fwf=2
+ xv_pu=ku
+ xv_pd=kd

Rdig dig_q 0 1k
Rload pad_ibis 0 50
Cload pad_ibis 0 2p

.probe tran V(in_dig) V(pad_ibis) V(dig_q) V(ku) V(kd)
.tran 1p 25n
.end
"""


def make_ngspice_deck() -> str:
    return """* io_buf pybis/ngspice switching coefficient extraction
.title io_buf ngspice pybis Ku/Kd extraction
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin in_dig 0 PWL(
+ 0n      0
+ 5n      0
+ 5.001n  3.3
+ 15n     3.3
+ 15.001n 0
+ 25n     0 )

Ven en_sig 0 DC 3.3
Vdd vdd 0 DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV pad in_dig en_sig vdd 0 driver_OutputInput_Typical

Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd)
.tran 1p 25n
.end
"""


def find_signal(data: dict[str, np.ndarray], *names: str) -> np.ndarray:
    normalized = {key.lower().replace(":", "."): key for key in data}
    for name in names:
        key = normalized.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(data[key], dtype=float)
    available = ", ".join(sorted(data.keys()))
    raise KeyError(f"Missing signal {names}; available: {available}")


def to_ns(t_s: np.ndarray) -> np.ndarray:
    return np.asarray(t_s, dtype=float) * 1e9


def interp_to(t_src_ns: np.ndarray, y_src: np.ndarray, t_dst_ns: np.ndarray) -> np.ndarray:
    return np.interp(t_dst_ns, t_src_ns, y_src)


def active_mask(t_ns: np.ndarray) -> np.ndarray:
    return ((t_ns >= 4.8) & (t_ns <= 8.5)) | ((t_ns >= 14.8) & (t_ns <= 18.5))


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def maxabs(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs(a - b)))


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


def write_waveform_csv(path: Path, traces: dict[str, np.ndarray]) -> None:
    keys = list(traces)
    n = len(traces[keys[0]])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for i in range(n):
            writer.writerow([traces[key][i] for key in keys])


def plot_outputs(
    h_t: np.ndarray,
    h_pad: np.ndarray,
    h_ku: np.ndarray,
    h_kd: np.ndarray,
    n_t: np.ndarray,
    n_pad: np.ndarray,
    n_ku: np.ndarray,
    n_kd: np.ndarray,
) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    def style(ax, ylabel: str) -> None:
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.28)

    fig, axes = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True)
    axes[0].plot(h_t, h_pad, lw=2.0, label="HSPICE native IBIS pad")
    axes[0].plot(n_t, n_pad, lw=1.7, ls="--", label="ngspice pybis pad")
    style(axes[0], "Pad voltage (V)")
    axes[0].legend(loc="best")
    axes[1].plot(h_t, h_ku, lw=2.0, label="HSPICE Ku")
    axes[1].plot(h_t, h_kd, lw=2.0, label="HSPICE Kd")
    axes[1].plot(n_t, n_ku, lw=1.7, ls="--", label="ngspice pybis Ku")
    axes[1].plot(n_t, n_kd, lw=1.7, ls="--", label="ngspice pybis Kd")
    style(axes[1], "Coefficient")
    axes[1].set_xlabel("Time (ns)")
    axes[1].set_ylim(-0.08, 1.08)
    axes[1].legend(loc="best", ncol=2)
    fig.suptitle("io_buf: HSPICE native IBIS vs ngspice pybis")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(PLOTS_DIR / "00_waveform_and_switching_coefficients_overlay.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 4.7))
    ax.plot(h_t, h_pad, lw=2.0, label="HSPICE native IBIS")
    ax.plot(n_t, n_pad, lw=1.8, ls="--", label="ngspice pybis")
    style(ax, "Pad voltage (V)")
    ax.set_xlabel("Time (ns)")
    ax.set_title("io_buf pad waveform overlay")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "01_pad_waveform_overlay.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 4.7))
    ax.plot(h_t, h_ku, lw=2.0, label="HSPICE Ku")
    ax.plot(h_t, h_kd, lw=2.0, label="HSPICE Kd")
    ax.plot(n_t, n_ku, lw=1.8, ls="--", label="ngspice pybis Ku")
    ax.plot(n_t, n_kd, lw=1.8, ls="--", label="ngspice pybis Kd")
    style(ax, "Coefficient")
    ax.set_xlabel("Time (ns)")
    ax.set_ylim(-0.08, 1.08)
    ax.set_title("io_buf switching coefficient overlay")
    ax.legend(loc="best", ncol=2)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "02_switching_coefficients_overlay.png", dpi=180)
    plt.close(fig)

    for name, x0, x1 in (("rise", 4.9, 8.0), ("fall", 14.9, 18.0)):
        fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.0), sharex=True)
        axes[0].plot(h_t, h_pad, lw=2.0, label="HSPICE native IBIS")
        axes[0].plot(n_t, n_pad, lw=1.8, ls="--", label="ngspice pybis")
        axes[0].set_xlim(x0, x1)
        style(axes[0], "Pad voltage (V)")
        axes[0].legend(loc="best")
        axes[1].plot(h_t, h_ku, lw=2.0, label="HSPICE Ku")
        axes[1].plot(h_t, h_kd, lw=2.0, label="HSPICE Kd")
        axes[1].plot(n_t, n_ku, lw=1.8, ls="--", label="ngspice pybis Ku")
        axes[1].plot(n_t, n_kd, lw=1.8, ls="--", label="ngspice pybis Kd")
        axes[1].set_xlim(x0, x1)
        axes[1].set_ylim(-0.08, 1.08)
        style(axes[1], "Coefficient")
        axes[1].set_xlabel("Time (ns)")
        axes[1].legend(loc="best", ncol=2)
        fig.suptitle(f"io_buf {name} transition zoom")
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(PLOTS_DIR / f"03_{name}_transition_zoom.png", dpi=180)
        plt.close(fig)


def write_readme(metrics: list[dict[str, object]]) -> None:
    lines = [
        "# io_buf Switching Coefficient Overlay",
        "",
        "This run compares the same `io_buf.ibs` through two flows:",
        "",
        "- HSPICE native IBIS B-element with `xv_pu=ku` and `xv_pd=kd`.",
        "- ngspice pybis2spice generated subcircuit with internal `V(xdrv.ku)` and `V(xdrv.kd)` nodes.",
        "",
        "Both use a 0/3.3 V PWL rise-then-fall input and a simple 50 ohm + 2 pF pad load.",
        "",
        "## Key Outputs",
        "",
        "- `plots/00_waveform_and_switching_coefficients_overlay.png`",
        "- `plots/01_pad_waveform_overlay.png`",
        "- `plots/02_switching_coefficients_overlay.png`",
        "- `plots/03_rise_transition_zoom.png`",
        "- `plots/03_fall_transition_zoom.png`",
        "- `metrics_summary.csv`",
        "- `aligned_waveforms.csv`",
        "",
        "## Metrics",
        "",
        "| Quantity | RMSE | Max abs |",
        "|---|---:|---:|",
    ]
    for row in metrics:
        lines.append(f"| {row['quantity']} | {row['rmse']:.6g} | {row['max_abs']:.6g} |")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "HSPICE's coefficients are the simulator's internal IBIS switching functions exposed through `xv_pu/xv_pd`.",
            "The pybis coefficients are the free-spice subcircuit's generated waveform coefficient nodes.",
            "Small timing differences are expected because HSPICE owns the native IBIS state machine, while pybis approximates it with explicit behavioral sources.",
        ]
    )
    write_text(OUT_DIR / "README.md", "\n".join(lines) + "\n")


def main() -> int:
    ibis_path = DEFAULT_IBIS
    ngspice = Path(os.environ.get("NGSPICE_EXE", str(DEFAULT_NGSPICE)))
    if not ibis_path.exists():
        raise FileNotFoundError(ibis_path)
    if not ngspice.exists():
        raise FileNotFoundError(f"ngspice executable not found: {ngspice}")

    for path in (OUT_DIR, HSPICE_DIR, NGSPICE_DIR, PLOTS_DIR):
        clean_dir(path)

    shutil.copy2(ibis_path, HSPICE_DIR / "io_buf.ibs")
    shutil.copy2(ibis_path, NGSPICE_DIR / "io_buf.ibs")

    subckt = NGSPICE_DIR / "driver_OutputInput_Typical.sub"
    convert_ibis_to_pybis(
        ibis_path=NGSPICE_DIR / "io_buf.ibs",
        output_path=subckt,
        component_name="MCM Driver 1",
        model_name="driver",
        io_type="Output",
        subcircuit_type="InputDriven",
        corner="Typical",
    )

    h_deck = HSPICE_DIR / "io_buf_hspice_native_ibis_switching.sp"
    n_deck = NGSPICE_DIR / "io_buf_ngspice_pybis_switching.sp"
    h_deck_text = make_hspice_deck()
    h_stem = "io_buf_hspice_native_ibis_switching"
    signature_id, signature = reference_signature(
        h_deck_text,
        [ibis_path],
        {"family": "io_buf_native_ibis", "case_id": "switching_overlay"},
    )
    h_cache = cache_dir("io_buf_native_ibis", "switching_overlay", signature_id)
    hspice_restored = restore_hspice_cache(h_cache, HSPICE_DIR, h_stem, h_deck_text)
    hspice_existing = (HSPICE_DIR / f"{h_stem}.tr0").exists()
    if hspice_existing and not hspice_restored:
        save_hspice_cache(h_cache, HSPICE_DIR, h_stem, h_deck_text, signature)
    if not hspice_restored:
        write_text(h_deck, h_deck_text)
    write_text(n_deck, make_ngspice_deck())

    if not hspice_restored and not hspice_existing:
        h_rc = run_process(
            [str(DEFAULT_HSPICE), "-i", h_deck.name, "-o", h_stem],
            HSPICE_DIR,
            HSPICE_DIR / "hspice_stdout.log",
            timeout_s=180,
        )
        if h_rc != 0:
            raise RuntimeError(f"HSPICE failed with return code {h_rc}; see {HSPICE_DIR / 'hspice_stdout.log'}")
        save_hspice_cache(h_cache, HSPICE_DIR, h_stem, h_deck_text, signature)

    n_raw = NGSPICE_DIR / "io_buf_ngspice_pybis_switching.raw"
    n_rc = run_process(
        [str(ngspice), "-b", "-r", n_raw.name, n_deck.name],
        NGSPICE_DIR,
        NGSPICE_DIR / "ngspice_stdout.log",
        timeout_s=180,
    )
    if n_rc != 0:
        raise RuntimeError(f"ngspice failed with return code {n_rc}; see {NGSPICE_DIR / 'ngspice_stdout.log'}")

    h_data = parse_hspice_tr0(HSPICE_DIR / "io_buf_hspice_native_ibis_switching.tr0")
    n_data = parse_ngspice_raw(n_raw)

    h_t = to_ns(find_signal(h_data, "time"))
    h_pad = find_signal(h_data, "v(pad_ibis)")
    h_ku = find_signal(h_data, "v(ku)")
    h_kd = find_signal(h_data, "v(kd)")
    n_t = to_ns(find_signal(n_data, "time"))
    n_pad = find_signal(n_data, "v(pad)")
    n_ku = find_signal(n_data, "v(xdrv.ku)")
    n_kd = find_signal(n_data, "v(xdrv.kd)")

    n_pad_i = interp_to(n_t, n_pad, h_t)
    n_ku_i = interp_to(n_t, n_ku, h_t)
    n_kd_i = interp_to(n_t, n_kd, h_t)
    mask = active_mask(h_t)
    metrics = [
        {"quantity": "pad_voltage_active_window_v", "rmse": rmse(h_pad[mask], n_pad_i[mask]), "max_abs": maxabs(h_pad[mask], n_pad_i[mask])},
        {"quantity": "ku_active_window", "rmse": rmse(h_ku[mask], n_ku_i[mask]), "max_abs": maxabs(h_ku[mask], n_ku_i[mask])},
        {"quantity": "kd_active_window", "rmse": rmse(h_kd[mask], n_kd_i[mask]), "max_abs": maxabs(h_kd[mask], n_kd_i[mask])},
        {"quantity": "ku_full", "rmse": rmse(h_ku, n_ku_i), "max_abs": maxabs(h_ku, n_ku_i)},
        {"quantity": "kd_full", "rmse": rmse(h_kd, n_kd_i), "max_abs": maxabs(h_kd, n_kd_i)},
    ]
    write_csv(OUT_DIR / "metrics_summary.csv", metrics)
    write_waveform_csv(
        OUT_DIR / "aligned_waveforms.csv",
        {
            "time_ns": h_t,
            "hspice_pad_v": h_pad,
            "ngspice_pybis_pad_v_interp": n_pad_i,
            "hspice_ku": h_ku,
            "ngspice_pybis_ku_interp": n_ku_i,
            "hspice_kd": h_kd,
            "ngspice_pybis_kd_interp": n_kd_i,
        },
    )
    plot_outputs(h_t, h_pad, h_ku, h_kd, n_t, n_pad, n_ku, n_kd)
    write_readme(metrics)

    print(f"OUT_DIR={OUT_DIR}")
    print(f"HSPICE_TR0={HSPICE_DIR / 'io_buf_hspice_native_ibis_switching.tr0'}")
    print(f"NGSPICE_RAW={n_raw}")
    print(f"PLOTS={PLOTS_DIR}")
    for row in metrics:
        print(f"{row['quantity']}: rmse={row['rmse']:.6g} max_abs={row['max_abs']:.6g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
