"""Sweep io_buf.sp input slew and compare refspice timing to io_buf.ibs VT tables.

This checks whether the large io_buf refspice-vs-pybis delay can be explained
by the input stimulus used during IBIS waveform characterization. The pybis
model replays the IBIS VT tables, so a table that includes delay from a slow
characterization input edge will look late compared with a fast transistor
bench.
"""

from __future__ import annotations

from pathlib import Path
import csv
import re
import subprocess

import matplotlib.pyplot as plt
import numpy as np

from analyze_refspice_pybis_correlation import (
    OUT_DIR as CORR_DIR,
    Case,
    choose_waveform,
    crossing_time,
    parse_ibis_waveforms,
    parse_ngspice_raw,
    raw_time_ns,
    waveform_threshold,
)


ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "clean_ibis_vs_pybis_matched_pkg"
OUT_DIR = CORR_DIR / "io_buf_input_slew_sweep"
NGSPICE = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"

SLEWS = ["5p", "50p", "100p", "250p", "500p", "750p", "1n", "1.25n", "1.5n", "2n"]
SLEW_NS = {
    "5p": 0.005,
    "50p": 0.050,
    "100p": 0.100,
    "250p": 0.250,
    "500p": 0.500,
    "750p": 0.750,
    "1n": 1.000,
    "1.25n": 1.250,
    "1.5n": 1.500,
    "2n": 2.000,
}


def make_deck(slew: str) -> Path:
    template = (PKG / "tb_refspice_rsf_14n_batch.sp").read_text()
    deck = re.sub(r"PULSE\(0 3\.3 1n 5p 5p 8n 20n\)", f"PULSE(0 3.3 1n {slew} {slew} 8n 20n)", template)
    deck = deck.replace(".tran 10p 14n", ".tran 10p 18n")
    out = OUT_DIR / f"io_buf_refspice_slew_{slew.replace('.', 'p')}.sp"
    out.write_text(deck)
    return out


def run_deck(deck: Path) -> Path:
    raw = deck.with_suffix(".raw")
    cmd = [str(NGSPICE), "-b", "-r", str(raw), str(deck)]
    subprocess.run(cmd, cwd=PKG, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return raw


def analyze_raw(raw: Path, slew: str) -> list[dict[str, object]]:
    case = Case(
        name="io_buf",
        package_dir=PKG,
        ibis_file="io_buf.ibs",
        pybis_raw="tb_ibis_vs_pybis_rsf_12n_batch.raw",
        ref_raw="tb_refspice_rsf_14n_batch.raw",
        input_threshold=1.4,
        rise_search_ns=(0.9, 1.0 + SLEW_NS[slew] + 0.5),
        fall_search_ns=(8.9, 9.0 + 2 * SLEW_NS[slew] + 1.0),
    )
    waveforms = parse_ibis_waveforms(PKG / "io_buf.ibs")
    wf_by_edge = {
        "rising": choose_waveform(waveforms, "rising", 50.0, 0.0),
        "falling": choose_waveform(waveforms, "falling", 50.0, 0.0),
    }

    data = parse_ngspice_raw(raw)
    t = raw_time_ns(data)
    vin = data["v(in_dig)"]
    pad = data["v(pad_ref)"]

    rise_start_ns = 1.0
    fall_start_ns = 1.0 + SLEW_NS[slew] + 8.0
    rows: list[dict[str, object]] = []

    for edge, search, edge_start in (
        ("rising", case.rise_search_ns, rise_start_ns),
        ("falling", case.fall_search_ns, fall_start_ns),
    ):
        input_cross = crossing_time(t, vin, case.input_threshold, edge, search)
        wf = wf_by_edge[edge]
        for pct in (0.25, 0.50, 0.75):
            threshold = waveform_threshold(wf, pct)
            ibis_dt = crossing_time(wf.time_ns, wf.v_typ, threshold, edge)
            out_cross = crossing_time(t, pad, threshold, edge, (search[0], search[1] + 4.0))
            rows.append(
                {
                    "slew": slew,
                    "slew_ns": SLEW_NS[slew],
                    "edge": edge,
                    "threshold_pct": pct,
                    "threshold_v": threshold,
                    "ibis_after_start_ps": ibis_dt * 1000.0,
                    "ref_after_input_start_ps": (out_cross - edge_start) * 1000.0,
                    "ref_after_threshold_ps": (out_cross - input_cross) * 1000.0,
                    "ref_minus_ibis_from_start_ps": (out_cross - edge_start - ibis_dt) * 1000.0,
                    "ref_minus_ibis_from_threshold_ps": (out_cross - input_cross - ibis_dt) * 1000.0,
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_plot(rows: list[dict[str, object]]) -> None:
    plt.rcParams.update({"figure.figsize": (11, 7), "axes.titlesize": 11, "legend.fontsize": 8.5})
    fig, axes = plt.subplots(2, 1, sharex=True)

    for ax, edge in zip(axes, ("rising", "falling")):
        for pct in (0.25, 0.50, 0.75):
            subset = [r for r in rows if r["edge"] == edge and r["threshold_pct"] == pct]
            x = np.asarray([float(r["slew_ns"]) for r in subset])
            y_start = np.asarray([float(r["ref_minus_ibis_from_start_ps"]) for r in subset])
            y_thr = np.asarray([float(r["ref_minus_ibis_from_threshold_ps"]) for r in subset])
            ax.plot(x, y_start, marker="o", label=f"{pct:.0%}, from input start")
            ax.plot(x, y_thr, marker="x", linestyle="--", label=f"{pct:.0%}, from threshold")
        ax.axhline(0.0, color="#333333", linewidth=0.9)
        ax.grid(True, alpha=0.3)
        ax.set_ylabel("refspice - IBIS (ps)")
        ax.set_title(f"io_buf {edge}: refspice timing error vs IBIS table")
        ax.legend(loc="best", ncol=2)

    axes[-1].set_xlabel("Input rise/fall time used in refspice bench (ns)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "io_buf_input_slew_refspice_vs_ibis.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    for slew in SLEWS:
        deck = make_deck(slew)
        raw = run_deck(deck)
        rows.extend(analyze_raw(raw, slew))

    write_csv(OUT_DIR / "io_buf_input_slew_refspice_vs_ibis.csv", rows)
    make_plot(rows)
    print(f"Wrote {OUT_DIR / 'io_buf_input_slew_refspice_vs_ibis.csv'}")
    print(f"Wrote {OUT_DIR / 'io_buf_input_slew_refspice_vs_ibis.png'}")


if __name__ == "__main__":
    main()
