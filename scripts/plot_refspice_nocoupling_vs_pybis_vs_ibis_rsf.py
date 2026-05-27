"""
Overlay pad waveforms for:
  - transistor reference SPICE with explicit n2/n3->out parasitic caps removed
  - converted IBIS-SPICE (pybis2spice) with zero package R/L/C
  - native IBIS VT waveforms stitched into the same RSF timing
"""

from pathlib import Path

import matplotlib.pyplot as plt

from plot_validation_results import parse_ngspice_raw
from plot_refspice_vs_pybis_vs_ibis_rsf import (
    IBIS_PATH,
    EXPECTED_STOP_NS,
    check_raw,
    build_stitched_ibis_rsf,
    choose_fixture_waveform,
    ns,
    parse_ibis_waveforms,
    style_axis,
)


ROOT = Path(__file__).resolve().parent.parent
RAW_REF = ROOT / "ngspice_refspice" / "tb_validation_refspice_rsf_nocoupling_batch.raw"
RAW_PYBIS = ROOT / "ngspice_pybis" / "tb_validation_rfr_ngspice_pybis_12n_batch.raw"
OUT_DIR = ROOT / "plots" / "validation"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ref = parse_ngspice_raw(RAW_REF)
    ref_last = check_raw(ref, "refspice no-coupling RSF")

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

    ibis_time_s = ref["time"][ref_mask]
    ibis_pad = build_stitched_ibis_rsf(ibis_time_s, rise_wf, fall_wf)

    plt.rcParams.update({
        "figure.figsize": (11, 5.5),
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })

    for tag, xlim, title in [
        ("pad", None, "RSF Pad Overlay: refspice(no explicit coupling caps) vs pybis(no package) vs IBIS VT"),
        ("rise_zoom", (0.95, 4.5), "RSF Rise Zoom: refspice(no explicit coupling caps) vs pybis(no package) vs IBIS VT"),
        ("fall_zoom", (8.95, 11.2), "RSF Fall Zoom: refspice(no explicit coupling caps) vs pybis(no package) vs IBIS VT"),
    ]:
        fig, ax = plt.subplots()
        ax.plot(time_ref_ns[ref_mask], ref["v(pad_ref)"][ref_mask], label="Reference SPICE pad (no explicit coupling caps)", linewidth=2.0)
        ax.plot(time_pybis_ns[pybis_mask], pybis["v(pad)"][pybis_mask], label="Converted IBIS-SPICE pad (no package)", linewidth=2.0, linestyle="--")
        ax.plot(ns(ibis_time_s), ibis_pad, label="IBIS VT waveform (Rfix=50, Vfix=0)", linewidth=2.0, linestyle=":")
        ax.plot(time_ref_ns[ref_mask], ref["v(in_dig)"][ref_mask], "--", label="Input", linewidth=1.5, alpha=0.8, color="gray")
        if xlim is not None:
            ax.set_xlim(*xlim)
        style_axis(ax, title)
        ax.legend(loc="best")
        fig.tight_layout()
        out = OUT_DIR / f"refspice_nocoupling_vs_pybis_vs_ibis_rsf_{tag}.png"
        fig.savefig(out, dpi=180, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
