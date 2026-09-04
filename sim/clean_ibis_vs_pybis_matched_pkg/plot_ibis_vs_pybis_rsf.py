from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
RAW_PYBIS = ROOT / "tb_ibis_vs_pybis_rsf_12n_batch.raw"
RAW_REF = ROOT / "tb_refspice_rsf_14n_batch.raw"
IBIS_PATH = ROOT / "io_buf.ibs"
OUT_DIR = ROOT / "plots"

TARGET_R_FIX = 50.0
TARGET_V_FIX = 0.0
RISE_START_NS = 1.0
FALL_START_NS = 9.0
EXPECTED_STOP_NS = 12.0
MIN_VALID_STOP_NS = 11.0


@dataclass
class IbisWaveform:
    kind: str
    r_fix: float
    v_fix: float
    time_s: np.ndarray
    v_typ: np.ndarray


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
    if npts == 0:
        npts = len(payload) // (8 * nvars)
    values = struct.unpack("<" + "d" * (nvars * npts), payload[: 8 * nvars * npts])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))
    return {name: arr[:, i] for i, name in enumerate(variables)}


def parse_ibis_waveforms(path: Path):
    text = path.read_text()
    lines = text.splitlines()
    waveforms: list[IbisWaveform] = []

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped not in ("[Rising Waveform]", "[Falling Waveform]"):
            i += 1
            continue

        kind = "Rising" if "Rising" in stripped else "Falling"
        i += 1

        r_fix = None
        v_fix = None
        samples = []

        while i < len(lines):
            raw = lines[i]
            stripped = raw.strip()
            if not stripped:
                i += 1
                continue
            if stripped.startswith("[") and "Waveform" in stripped:
                break
            if stripped.startswith("[") and "Waveform" not in stripped:
                break
            if stripped.startswith("|"):
                i += 1
                continue
            if stripped.lower().startswith("r_fixture"):
                r_fix = float(stripped.split("=", 1)[1].strip())
                i += 1
                continue
            if stripped.lower().startswith("v_fixture"):
                v_fix = float(stripped.split("=", 1)[1].strip().rstrip("Vv"))
                i += 1
                continue

            parts = stripped.split()
            if len(parts) >= 2 and parts[0].endswith("n"):
                try:
                    time_ns = float(parts[0][:-1])
                    v_typ = float(parts[1])
                except ValueError:
                    i += 1
                    continue
                samples.append((time_ns * 1e-9, v_typ))
            i += 1

        if r_fix is None or v_fix is None or not samples:
            raise RuntimeError(f"Failed to parse a complete {kind} waveform block from {path}")

        arr = np.asarray(samples, dtype=float)
        waveforms.append(
            IbisWaveform(
                kind=kind,
                r_fix=float(r_fix),
                v_fix=float(v_fix),
                time_s=arr[:, 0],
                v_typ=arr[:, 1],
            )
        )

    return waveforms


def choose_fixture_waveform(waveforms: list[IbisWaveform], kind: str):
    candidates = [wf for wf in waveforms if wf.kind == kind]
    if not candidates:
        raise RuntimeError(f"No {kind} waveform found in {IBIS_PATH}")

    def score(wf: IbisWaveform):
        return (abs(wf.r_fix - TARGET_R_FIX), abs(wf.v_fix - TARGET_V_FIX))

    return min(candidates, key=score)


def build_stitched_ibis_rsf(time_s: np.ndarray, rise_wf: IbisWaveform, fall_wf: IbisWaveform):
    out = np.empty_like(time_s)

    rise_end_v = float(rise_wf.v_typ[-1])
    fall_end_v = float(fall_wf.v_typ[-1])
    low_v = float(rise_wf.v_typ[0])

    for idx, t in enumerate(time_s):
        t_ns = t * 1e9
        if t_ns < RISE_START_NS:
            out[idx] = low_v
            continue

        if t_ns < FALL_START_NS:
            dt_s = t - (RISE_START_NS * 1e-9)
            if dt_s <= rise_wf.time_s[-1]:
                out[idx] = np.interp(dt_s, rise_wf.time_s, rise_wf.v_typ)
            else:
                out[idx] = rise_end_v
            continue

        dt_s = t - (FALL_START_NS * 1e-9)
        if dt_s <= fall_wf.time_s[-1]:
            out[idx] = np.interp(dt_s, fall_wf.time_s, fall_wf.v_typ)
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
            f"{label}: simulation ended at {last_t:.3f} ns, expected >= {MIN_VALID_STOP_NS:.0f} ns."
        )
    return min(last_t, EXPECTED_STOP_NS)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pybis = parse_ngspice_raw(RAW_PYBIS)
    ref = parse_ngspice_raw(RAW_REF)
    t_max_ns = min(check_raw(pybis, "pybis"), check_raw(ref, "refspice"))

    waveforms = parse_ibis_waveforms(IBIS_PATH)
    rise_wf = choose_fixture_waveform(waveforms, "Rising")
    fall_wf = choose_fixture_waveform(waveforms, "Falling")

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
    ax_rise.set_xlim(0.95, 4.5)
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
    ax_fall.set_xlim(8.95, 11.2)
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
    print(f"Selected rising waveform: R_fixture={rise_wf.r_fix}, V_fixture={rise_wf.v_fix}")
    print(f"Selected falling waveform: R_fixture={fall_wf.r_fix}, V_fixture={fall_wf.v_fix}")
    print(f"Max abs pad error over plotted window: {np.max(np.abs(err)):.6f} V")
    print(f"RMS pad error over plotted window: {np.sqrt(np.mean(err**2)):.6f} V")
    print(f"Saved: {OUT_DIR / 'refspice_vs_pybis_vs_ibis_rsf_pad.png'}")
    print(f"Saved: {OUT_DIR / 'refspice_vs_pybis_vs_ibis_rsf_rise_zoom.png'}")
    print(f"Saved: {OUT_DIR / 'refspice_vs_pybis_vs_ibis_rsf_fall_zoom.png'}")
    print(f"Saved: {OUT_DIR / 'refspice_vs_pybis_rsf_load.png'}")


if __name__ == "__main__":
    main()
