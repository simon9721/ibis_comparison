"""
Overlay pad waveforms for:
  - transistor reference SPICE
  - converted IBIS-SPICE (pybis2spice)
  - native IBIS VT waveforms stitched into the same RSF timing

This is intentionally a pad-voltage comparison, not a far-end load comparison,
because the IBIS [Rising/Falling Waveform] data is a fixture-level waveform.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
RAW_REF = ROOT / "ngspice_refspice" / "tb_validation_refspice_rsf_batch.raw"
RAW_PYBIS = ROOT / "ngspice_pybis" / "tb_validation_rfr_ngspice_pybis_12n_batch.raw"
IBIS_PATH = ROOT / "models" / "io_buf.ibs"
OUT_DIR = ROOT / "plots" / "validation"

EXPECTED_STOP_NS = 12.0
MIN_VALID_STOP_NS = 11.0
TARGET_R_FIX = 50.0
TARGET_V_FIX = 0.0

# Simple RSF bench timing
RISE_START_NS = 1.0
FALL_START_NS = 9.0


@dataclass
class IbisWaveform:
    kind: str
    r_fix: float
    v_fix: float
    time_s: np.ndarray
    v_typ: np.ndarray


def ns(time_s):
    return time_s * 1e9


def style_axis(ax, title, ylabel="V"):
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def check_raw(data, label, min_ns=MIN_VALID_STOP_NS):
    if len(data["time"]) == 0:
        raise RuntimeError(f"{label}: no data points found in raw file.")
    last_t = float(data["time"][-1]) * 1e9
    if last_t < min_ns:
        raise RuntimeError(
            f"{label}: ended at {last_t:.3f} ns, expected >= {min_ns:.0f} ns. "
            "Refusing to generate a misleading plot."
        )
    return last_t


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
                v_fix_str = stripped.split("=", 1)[1].strip().rstrip("Vv")
                v_fix = float(v_fix_str)
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


def choose_fixture_waveform(waveforms: list[IbisWaveform], kind: str, target_r_fix=TARGET_R_FIX, target_v_fix=TARGET_V_FIX):
    candidates = [wf for wf in waveforms if wf.kind == kind]
    if not candidates:
        raise RuntimeError(f"No {kind} waveform found in {IBIS_PATH}")

    def score(wf: IbisWaveform):
        return (abs(wf.r_fix - target_r_fix), abs(wf.v_fix - target_v_fix))

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


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ref = parse_ngspice_raw(RAW_REF)
    ref_last = check_raw(ref, "refspice RSF")

    pybis = parse_ngspice_raw(RAW_PYBIS)
    pybis_last = check_raw(pybis, "pybis RSF")

    waveforms = parse_ibis_waveforms(IBIS_PATH)
    rise_wf = choose_fixture_waveform(waveforms, "Rising")
    fall_wf = choose_fixture_waveform(waveforms, "Falling")

    t_max_ns = min(ref_last, pybis_last, EXPECTED_STOP_NS)

    time_ref_ns = ns(ref["time"])
    time_pybis_ns = ns(pybis["time"])

    ref_mask = time_ref_ns <= t_max_ns + 0.001
    pybis_mask = time_pybis_ns <= t_max_ns + 0.001

    # Use the refspice time base for the stitched IBIS overlay.
    ibis_time_s = ref["time"][ref_mask]
    ibis_pad = build_stitched_ibis_rsf(ibis_time_s, rise_wf, fall_wf)

    plt.rcParams.update({
        "figure.figsize": (11, 5.5),
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    # Full RSF overlay
    fig, ax = plt.subplots()
    ax.plot(time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask], label="Reference SPICE pad", linewidth=2.0)
    ax.plot(time_pybis_ns[pybis_mask], pybis["v(pad)"][pybis_mask], label="Converted IBIS-SPICE pad", linewidth=2.0, linestyle="--")
    ax.plot(ns(ibis_time_s), ibis_pad, label="IBIS VT waveform (Rfix=50, Vfix=0)", linewidth=2.0, linestyle=":")
    ax.plot(time_ref_ns[ref_mask], ref["v(in_dig)"][ref_mask], "--", label="Input", linewidth=1.5, alpha=0.8, color="gray")
    style_axis(ax, "RSF Pad Overlay: Reference SPICE vs Converted IBIS-SPICE vs IBIS VT")
    ax.legend(loc="best")
    fig.tight_layout()
    out_full = OUT_DIR / "refspice_vs_pybis_vs_ibis_rsf_pad.png"
    fig.savefig(out_full, dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Rise zoom
    fig_rise, ax_rise = plt.subplots()
    ax_rise.plot(time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask], label="Reference SPICE pad", linewidth=2.0)
    ax_rise.plot(time_pybis_ns[pybis_mask], pybis["v(pad)"][pybis_mask], label="Converted IBIS-SPICE pad", linewidth=2.0, linestyle="--")
    ax_rise.plot(ns(ibis_time_s), ibis_pad, label="IBIS VT waveform (Rfix=50, Vfix=0)", linewidth=2.0, linestyle=":")
    ax_rise.plot(time_ref_ns[ref_mask], ref["v(in_dig)"][ref_mask], "--", label="Input", linewidth=1.5, alpha=0.8, color="gray")
    ax_rise.set_xlim(0.95, 4.5)
    style_axis(ax_rise, "RSF Rise Zoom")
    ax_rise.legend(loc="best")
    fig_rise.tight_layout()
    out_rise = OUT_DIR / "refspice_vs_pybis_vs_ibis_rsf_rise_zoom.png"
    fig_rise.savefig(out_rise, dpi=180, bbox_inches="tight")
    plt.close(fig_rise)

    # Fall zoom
    fig_fall, ax_fall = plt.subplots()
    ax_fall.plot(time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask], label="Reference SPICE pad", linewidth=2.0)
    ax_fall.plot(time_pybis_ns[pybis_mask], pybis["v(pad)"][pybis_mask], label="Converted IBIS-SPICE pad", linewidth=2.0, linestyle="--")
    ax_fall.plot(ns(ibis_time_s), ibis_pad, label="IBIS VT waveform (Rfix=50, Vfix=0)", linewidth=2.0, linestyle=":")
    ax_fall.plot(time_ref_ns[ref_mask], ref["v(in_dig)"][ref_mask], "--", label="Input", linewidth=1.5, alpha=0.8, color="gray")
    ax_fall.set_xlim(8.95, 11.2)
    style_axis(ax_fall, "RSF Fall Zoom")
    ax_fall.legend(loc="best")
    fig_fall.tight_layout()
    out_fall = OUT_DIR / "refspice_vs_pybis_vs_ibis_rsf_fall_zoom.png"
    fig_fall.savefig(out_fall, dpi=180, bbox_inches="tight")
    plt.close(fig_fall)

    print(f"Selected rising waveform: R_fixture={rise_wf.r_fix}, V_fixture={rise_wf.v_fix}")
    print(f"Selected falling waveform: R_fixture={fall_wf.r_fix}, V_fixture={fall_wf.v_fix}")
    print(f"Saved: {out_full}")
    print(f"Saved: {out_rise}")
    print(f"Saved: {out_fall}")


if __name__ == "__main__":
    main()
