from __future__ import annotations

from pathlib import Path
import struct
import sys

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
PYBIS_REPO = ROOT.parents[3] / "spice" / "pybis2spice"
if str(PYBIS_REPO) not in sys.path:
    sys.path.insert(0, str(PYBIS_REPO))

from pybis2spice import pybis2spice as pb  # noqa: E402


RAW_PYBIS = ROOT / "tb_ibis_vs_pybis_rsf_6p5n_batch.raw"
RAW_REF = ROOT / "tb_refspice_rsf_7n_batch.raw"
IBIS_PATH = ROOT / "t2b_0615_v5.ibs"
OUT_DIR = ROOT / "plots"

TARGET_R_FIX = 50.0
TARGET_V_FIX = 0.0
RISE_START_NS = 1.0
FALL_START_NS = 4.0
EXPECTED_STOP_NS = 6.5
MIN_VALID_STOP_NS = 6.0

def parse_ngspice_raw(path: Path):
    data = path.read_bytes()
    marker = b"Binary:\n"
    idx = data.find(marker)
    if idx < 0:
        raise RuntimeError(f"Binary marker not found in {path}")

    header = data[:idx].decode("latin1")
    lines = header.splitlines()

    nvars = None
    npts = None
    variables = []
    reading_vars = False

    for line in lines:
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":", 1)[1])
        elif line.strip() == "Variables:":
            reading_vars = True
        elif reading_vars and line.startswith("\t"):
            variables.append(line.split()[1])

    if nvars is None or npts is None or len(variables) != nvars:
        raise RuntimeError(f"Could not parse ngspice raw header for {path}")

    payload = data[idx + len(marker):]
    values = struct.unpack("<" + "d" * (nvars * npts), payload[: 8 * nvars * npts])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))
    return {name: arr[:, i] for i, name in enumerate(variables)}


def choose_fixture_waveform(data_model, kind: str):
    candidates = data_model.vt_rising if kind == "Rising" else data_model.vt_falling
    if not candidates:
        raise RuntimeError(f"No {kind} waveform found in {IBIS_PATH}")

    def score(wf):
        return (abs(float(wf.r_fix) - TARGET_R_FIX), abs(float(wf.v_fix[0]) - TARGET_V_FIX))

    return min(candidates, key=score)


def build_stitched_ibis_rsf(time_s: np.ndarray, rise_wf, fall_wf):
    out = np.empty_like(time_s)

    rise_time = np.asarray(rise_wf.data[:, 0], dtype=float)
    rise_v = np.asarray(rise_wf.data[:, 1], dtype=float)
    fall_time = np.asarray(fall_wf.data[:, 0], dtype=float)
    fall_v = np.asarray(fall_wf.data[:, 1], dtype=float)

    rise_end_v = float(rise_v[-1])
    fall_end_v = float(fall_v[-1])
    low_v = float(rise_v[0])

    for idx, t in enumerate(time_s):
        t_ns = t * 1e9
        if t_ns < RISE_START_NS:
            out[idx] = low_v
            continue

        if t_ns < FALL_START_NS:
            dt_s = t - (RISE_START_NS * 1e-9)
            if dt_s <= rise_time[-1]:
                out[idx] = np.interp(dt_s, rise_time, rise_v)
            else:
                out[idx] = rise_end_v
            continue

        dt_s = t - (FALL_START_NS * 1e-9)
        if dt_s <= fall_time[-1]:
            out[idx] = np.interp(dt_s, fall_time, fall_v)
        else:
            out[idx] = fall_end_v

    return out


def ns(time_s):
    return time_s * 1e9


def style_axis(ax, title, ylabel="V"):
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def check_raw(data, label):
    if len(data["time"]) == 0:
        raise RuntimeError(f"{label}: no data points found in ngspice raw file.")
    last_t = float(data["time"][-1]) * 1e9
    if last_t < MIN_VALID_STOP_NS:
        raise RuntimeError(
            f"{label}: simulation ended at {last_t:.3f} ns, expected >= {MIN_VALID_STOP_NS:.1f} ns."
        )
    return min(last_t, EXPECTED_STOP_NS)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pybis = parse_ngspice_raw(RAW_PYBIS)
    ref = parse_ngspice_raw(RAW_REF)
    t_max_ns = min(check_raw(pybis, "pybis"), check_raw(ref, "refspice"))

    ibis = pb.get_ibis_model_ecdtools(str(IBIS_PATH))
    data_model = pb.DataModel(ibis, "driver2", "invchain")
    rise_wf = choose_fixture_waveform(data_model, "Rising")
    fall_wf = choose_fixture_waveform(data_model, "Falling")

    time_pybis_ns = ns(pybis["time"])
    time_ref_ns = ns(ref["time"])
    pybis_mask = time_pybis_ns <= t_max_ns + 0.001
    ref_mask = time_ref_ns <= t_max_ns + 0.001
    ibis_time_s = pybis["time"][pybis_mask]
    ibis_pad = build_stitched_ibis_rsf(ibis_time_s, rise_wf, fall_wf)

    plt.rcParams.update(
        {
            "figure.figsize": (11, 5.5),
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
        }
    )

    fig, ax = plt.subplots()
    ax.plot(time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask], label="Reference SPICE pad", linewidth=2.0)
    ax.plot(time_pybis_ns[pybis_mask], pybis["v(pad)"][pybis_mask], label="Converted pybis pad", linewidth=2.0, linestyle="--")
    ax.plot(ns(ibis_time_s), ibis_pad, label="IBIS VT waveform (Rfix=50, Vfix=0)", linewidth=2.0, linestyle=":")
    ax.plot(time_pybis_ns[pybis_mask], pybis["v(in_dig)"][pybis_mask], label="Input", linewidth=1.4, linestyle=":", color="gray")
    style_axis(ax, "Reference SPICE vs pybis vs IBIS Pad Overlay")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "refspice_vs_pybis_vs_ibis_rsf_pad.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig_rise, ax_rise = plt.subplots()
    ax_rise.plot(time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask], label="Reference SPICE pad", linewidth=2.0)
    ax_rise.plot(time_pybis_ns[pybis_mask], pybis["v(pad)"][pybis_mask], label="Converted pybis pad", linewidth=2.0, linestyle="--")
    ax_rise.plot(ns(ibis_time_s), ibis_pad, label="IBIS VT waveform (Rfix=50, Vfix=0)", linewidth=2.0, linestyle=":")
    ax_rise.plot(time_pybis_ns[pybis_mask], pybis["v(in_dig)"][pybis_mask], label="Input", linewidth=1.4, linestyle=":", color="gray")
    ax_rise.set_xlim(0.95, 2.9)
    style_axis(ax_rise, "Reference SPICE vs pybis vs IBIS Rise Zoom")
    ax_rise.legend(loc="best")
    fig_rise.tight_layout()
    fig_rise.savefig(OUT_DIR / "refspice_vs_pybis_vs_ibis_rsf_rise_zoom.png", dpi=180, bbox_inches="tight")
    plt.close(fig_rise)

    fig_fall, ax_fall = plt.subplots()
    ax_fall.plot(time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask], label="Reference SPICE pad", linewidth=2.0)
    ax_fall.plot(time_pybis_ns[pybis_mask], pybis["v(pad)"][pybis_mask], label="Converted pybis pad", linewidth=2.0, linestyle="--")
    ax_fall.plot(ns(ibis_time_s), ibis_pad, label="IBIS VT waveform (Rfix=50, Vfix=0)", linewidth=2.0, linestyle=":")
    ax_fall.plot(time_pybis_ns[pybis_mask], pybis["v(in_dig)"][pybis_mask], label="Input", linewidth=1.4, linestyle=":", color="gray")
    ax_fall.set_xlim(3.95, 5.9)
    style_axis(ax_fall, "Reference SPICE vs pybis vs IBIS Fall Zoom")
    ax_fall.legend(loc="best")
    fig_fall.tight_layout()
    fig_fall.savefig(OUT_DIR / "refspice_vs_pybis_vs_ibis_rsf_fall_zoom.png", dpi=180, bbox_inches="tight")
    plt.close(fig_fall)

    fig_load, ax_load = plt.subplots()
    ax_load.plot(time_ref_ns[ref_mask], ref["v(ntst_ref)"][ref_mask], label="Reference SPICE load", linewidth=2.0)
    ax_load.plot(time_pybis_ns[pybis_mask], pybis["v(ntst)"][pybis_mask], label="Converted pybis load", linewidth=2.0, linestyle="--")
    ax_load.plot(time_pybis_ns[pybis_mask], pybis["v(in_dig)"][pybis_mask], label="Input", linewidth=1.4, linestyle=":", color="gray")
    style_axis(ax_load, "Reference SPICE vs pybis Load Overlay")
    ax_load.legend(loc="best")
    fig_load.tight_layout()
    fig_load.savefig(OUT_DIR / "refspice_vs_pybis_rsf_load.png", dpi=180, bbox_inches="tight")
    plt.close(fig_load)

    err = pybis["v(pad)"][pybis_mask] - ibis_pad
    print(f"Selected rising waveform: R_fixture={float(rise_wf.r_fix)}, V_fixture={float(rise_wf.v_fix[0])}")
    print(f"Selected falling waveform: R_fixture={float(fall_wf.r_fix)}, V_fixture={float(fall_wf.v_fix[0])}")
    print(f"Max abs pad error over plotted window: {np.max(np.abs(err)):.6f} V")
    print(f"RMS pad error over plotted window: {np.sqrt(np.mean(err**2)):.6f} V")
    print(f"Saved: {OUT_DIR / 'refspice_vs_pybis_vs_ibis_rsf_pad.png'}")
    print(f"Saved: {OUT_DIR / 'refspice_vs_pybis_vs_ibis_rsf_rise_zoom.png'}")
    print(f"Saved: {OUT_DIR / 'refspice_vs_pybis_vs_ibis_rsf_fall_zoom.png'}")
    print(f"Saved: {OUT_DIR / 'refspice_vs_pybis_rsf_load.png'}")


if __name__ == "__main__":
    main()
