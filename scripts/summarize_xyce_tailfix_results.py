from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from test_xyce_pybis_tail_fixes import (
    CANDIDATES,
    CHANNEL_BENCHES,
    NGSPICE_DIR,
    OUT_DIR,
    ROOT,
    SPISIM_BENCHES,
    col,
    csv_path,
    load_ngspice_raw,
    load_xyce_csv,
    ns,
)


METRIC_FILES = [
    "xyce_pybis_tailfix_metrics.csv",
    "xyce_pybis_tailfix_channel_metrics.csv",
    "xyce_pybis_tailfix_prbs_probe_hard4p2.csv",
    "xyce_pybis_tailfix_prbs200_hybrid_metrics.csv",
    "xyce_pybis_tailfix_prbs200_edgefactor_metrics.csv",
    "xyce_pybis_tailfix_prbs200_edge55_metrics.csv",
    "xyce_pybis_tailfix_prbs200_edge52_metrics.csv",
    "xyce_pybis_tailfix_prbs1000_edge50_flat_metrics.csv",
    "xyce_pybis_tailfix_prbs300_deepedge_metrics.csv",
    "xyce_pybis_tailfix_prbs1000_compare_tanh15_metrics.csv",
    "xyce_pybis_tailfix_tline_hybrid_winners_metrics.csv",
    "xyce_pybis_tailfix_channel_hybrid_winners_metrics.csv",
    "xyce_pybis_tailfix_tline_compare_edge15_metrics.csv",
    "xyce_pybis_tailfix_channel_compare_edge15_metrics.csv",
    "xyce_pybis_tailfix_tline_mixed_edge15_metrics.csv",
]

BENCH_ORDER = [
    "spisim_pulse200p",
    "spisim_rfr200p",
    "channel_pulsetrain_200p",
    "channel_bitpattern_200p",
    "channel_prbs7_200n",
    "channel_prbs7_300n",
    "channel_prbs7_1000n",
]

CANDIDATE_ORDER = [
    "tanh92",
    "hard4p2",
    "flat4p2",
    "edge50",
    "edge50_flat4p2",
    "edge52_flat4p2",
    "edge15_flat4p2",
    "edge15_sel75_flat4p2",
    "edge15_sel50_flat4p2",
    "tanh15",
    "ctrl15_flat4p2",
]


def read_rows() -> dict[tuple[str, str], dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for name in METRIC_FILES:
        path = OUT_DIR / name
        if not path.exists():
            continue
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                rows[(row["bench"], row["candidate"])] = row
    return rows


def write_summary(rows: dict[tuple[str, str], dict[str, str]]) -> Path:
    selected = []
    for candidate in CANDIDATE_ORDER:
        for bench in BENCH_ORDER:
            row = rows.get((bench, candidate))
            if row:
                selected.append(row)

    keys = [
        "candidate",
        "candidate_title",
        "bench",
        "completed",
        "t_end_ns",
        "wall_s",
        "rmse_mv",
        "max_abs_mv",
        "model",
        "deck",
        "output",
    ]
    out = OUT_DIR / "xyce_pybis_tailfix_recommendation_summary.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in selected:
            writer.writerow({key: row.get(key, "") for key in keys})
    return out


def as_bool(text: str) -> bool:
    return str(text).lower() == "true"


def plot_matrix(rows: dict[tuple[str, str], dict[str, str]]) -> Path:
    out = OUT_DIR / "xyce_pybis_tailfix_recommendation_matrix.png"
    matrix = np.full((len(CANDIDATE_ORDER), len(BENCH_ORDER)), np.nan)
    labels = [["" for _ in BENCH_ORDER] for _ in CANDIDATE_ORDER]

    for r, candidate in enumerate(CANDIDATE_ORDER):
        for c, bench in enumerate(BENCH_ORDER):
            row = rows.get((bench, candidate))
            if not row:
                continue
            passed = as_bool(row.get("completed", ""))
            matrix[r, c] = 1.0 if passed else 0.0
            if row.get("rmse_mv"):
                labels[r][c] = f"{float(row['rmse_mv']):.1f}mV"
            elif row.get("t_end_ns"):
                labels[r][c] = f"{float(row['t_end_ns']):.1f}ns"
            if not passed and row.get("t_end_ns"):
                labels[r][c] += f"\n{float(row['t_end_ns']):.1f}ns"

    fig, ax = plt.subplots(figsize=(13, 7))
    cmap = matplotlib.colors.ListedColormap(["#e57373", "#81c784"])
    ax.imshow(np.nan_to_num(matrix, nan=0.5), cmap=cmap, vmin=0, vmax=1, aspect="auto")

    for r in range(len(CANDIDATE_ORDER)):
        for c in range(len(BENCH_ORDER)):
            if np.isnan(matrix[r, c]):
                ax.add_patch(plt.Rectangle((c - 0.5, r - 0.5), 1, 1, color="#eeeeee", zorder=-1))
                continue
            ax.text(c, r, labels[r][c], ha="center", va="center", fontsize=8, color="#111111")

    ax.set_xticks(np.arange(len(BENCH_ORDER)))
    ax.set_xticklabels(
        [
            "T-line\npulse",
            "T-line\nRFR",
            "channel\npulse",
            "channel\nbits",
            "PRBS\n200 ns",
            "PRBS\n300 ns",
            "PRBS\n1000 ns",
        ],
        fontsize=9,
    )
    ax.set_yticks(np.arange(len(CANDIDATE_ORDER)))
    ax.set_yticklabels(CANDIDATE_ORDER, fontsize=9)
    ax.set_title("Xyce pybis tail-fix experiments: pass/fail and RMSE vs ngspice")
    ax.set_xlabel("Validation bench")
    ax.set_ylabel("Candidate model")
    ax.set_xticks(np.arange(-0.5, len(BENCH_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(CANDIDATE_ORDER), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def candidate(name: str):
    return next(c for c in CANDIDATES if c.name == name)


def bench(name: str):
    for item in SPISIM_BENCHES + CHANNEL_BENCHES:
        if item.name == name:
            return item
    raise KeyError(name)


def plot_prbs_overlay() -> Path:
    out = OUT_DIR / "xyce_pybis_tailfix_prbs1000_edge15_vs_tanh15.png"
    ref = load_ngspice_raw(NGSPICE_DIR / "tb_pybis_prbs7_new50ohm.raw")
    b = bench("channel_prbs7_1000n")
    candidates = [candidate("tanh15"), candidate("edge15_flat4p2")]

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=False)
    windows = [(0, 250), (900, 1000)]
    for ax, (lo, hi) in zip(axes, windows):
        t_ref = ns(col(ref, "time"))
        y_ref = col(ref, "v(n10b)")
        mask = (t_ref >= lo) & (t_ref <= hi)
        ax.plot(t_ref[mask], y_ref[mask], color="black", linewidth=1.0, label="ngspice direct pybis")
        for cand in candidates:
            data = load_xyce_csv(csv_path(b, cand))
            t = ns(col(data, "time"))
            y = col(data, "v(n10b)")
            m = (t >= lo) & (t <= hi)
            ax.plot(t[m], y[m], linewidth=0.9, label=cand.name)
        ax.set_xlim(lo, hi)
        ax.set_ylabel("V(n10b) [V]")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8, ncol=3)
    axes[0].set_title("Full PRBS1000: localized edge15+tail-flat vs older all-tanh15 fallback")
    axes[-1].set_xlabel("Time [ns]")
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def plot_rfr_overlay() -> Path:
    out = OUT_DIR / "xyce_pybis_tailfix_rfr_key_candidates.png"
    ref = load_ngspice_raw(NGSPICE_DIR / "tb_spisim_val_rfr200p_ngspice_pybis.raw")
    b = bench("spisim_rfr200p")
    candidates = [candidate("hard4p2"), candidate("edge50_flat4p2"), candidate("edge15_flat4p2")]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(ns(col(ref, "time")), col(ref, "v(ntst)"), color="black", linewidth=1.2, label="ngspice direct pybis")
    for cand in candidates:
        data = load_xyce_csv(csv_path(b, cand))
        ax.plot(ns(col(data, "time")), col(data, "v(ntst)"), linewidth=1.0, label=cand.name)
    ax.set_title("SPISim-style RFR200p T-line: key passing Xyce candidates")
    ax.set_xlabel("Time [ns]")
    ax.set_ylabel("V(ntst) [V]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def main() -> int:
    rows = read_rows()
    summary = write_summary(rows)
    matrix = plot_matrix(rows)
    prbs = plot_prbs_overlay()
    rfr = plot_rfr_overlay()
    for path in [summary, matrix, prbs, rfr]:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
