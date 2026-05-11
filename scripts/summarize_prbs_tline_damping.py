from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "plots" / "xyce_pybis"


def read_metric_files() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in OUT_DIR.glob("xyce_pybis_prbs_tline_*_metrics.csv"):
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                row = dict(row)
                row["metric_file"] = str(path.relative_to(ROOT)).replace("\\", "/")
                rows.append(row)
    return rows


def stop_from_file(path_text: str) -> str:
    name = Path(path_text).name
    # xyce_pybis_prbs_tline_200n_riso2_metrics.csv
    parts = name.replace("xyce_pybis_prbs_tline_", "").replace("_metrics.csv", "").split("_")
    return parts[0]


def norm_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out = []
    for row in rows:
        riso = row.get("riso_ohm", "")
        if riso == "":
            riso = 0.0
        else:
            riso = float(riso)
        out.append(
            {
                "stop": stop_from_file(row["metric_file"]),
                "simulator": row.get("simulator", ""),
                "candidate": row.get("candidate", ""),
                "riso_ohm": riso,
                "completed": str(row.get("completed", "")).lower() == "true",
                "t_end_ns": float(row["t_end_ns"]) if row.get("t_end_ns") else np.nan,
                "wall_s": float(row["wall_s"]) if row.get("wall_s") else np.nan,
                "rmse_mv": float(row["ntst_rmse_mv"]) if row.get("ntst_rmse_mv") else np.nan,
                "metric_file": row["metric_file"],
            }
        )
    return out


def write_summary(rows: list[dict[str, object]]) -> Path:
    out = OUT_DIR / "xyce_pybis_prbs_tline_damping_summary.csv"
    keys = ["stop", "simulator", "candidate", "riso_ohm", "completed", "t_end_ns", "wall_s", "rmse_mv", "metric_file"]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    return out


def plot_summary(rows: list[dict[str, object]]) -> Path:
    out = OUT_DIR / "xyce_pybis_prbs_tline_damping_summary.png"
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)

    configs = [
        ("ngspice", "direct", "ngspice direct pybis"),
        ("xyce", "edge50_flat4p2", "Xyce edge50_flat4p2"),
    ]
    markers = {"100n": "o", "120n": "s", "130n": "^", "200n": "D"}

    for ax, (sim, candidate, title) in zip(axes, configs):
        subset = [r for r in rows if r["simulator"] == sim and r["candidate"] == candidate]
        for stop in sorted({str(r["stop"]) for r in subset}):
            stop_rows = sorted([r for r in subset if r["stop"] == stop], key=lambda r: float(r["riso_ohm"]))
            if not stop_rows:
                continue
            x = [float(r["riso_ohm"]) for r in stop_rows]
            y = [float(r["t_end_ns"]) for r in stop_rows]
            ax.plot(x, y, marker=markers.get(stop, "o"), linewidth=1.1, label=stop)
            for xi, yi, r in zip(x, y, stop_rows):
                if bool(r["completed"]):
                    ax.scatter([xi], [yi], s=70, facecolors="none", edgecolors="green", linewidths=1.5)
                else:
                    ax.scatter([xi], [yi], s=45, color="tab:red", marker="x")
        ax.set_title(title)
        ax.set_xlabel("Driver-to-line RISO [ohm]")
        ax.grid(True, alpha=0.25)
        ax.legend(title="stop", fontsize=8)
    axes[0].set_ylabel("Final simulated time [ns]")
    fig.suptitle("PRBS7 + ideal 30 ps 50-ohm T-line damping sweep")
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def main() -> int:
    rows = norm_rows(read_metric_files())
    summary = write_summary(rows)
    plot = plot_summary(rows)
    print(summary.relative_to(ROOT))
    print(plot.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
