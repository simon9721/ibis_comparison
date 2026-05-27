from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import struct

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "plots"
CSV_PATH = ROOT / "timing_offset_constancy.csv"
TXT_PATH = ROOT / "timing_offset_constancy_summary.txt"

THRESHOLD_V = 0.75
EDGE_SEQUENCE = ["rise", "fall", "rise", "fall", "rise", "fall"]


@dataclass
class BenchNode:
    bench: str
    node_label: str
    raw_ref: Path
    raw_pybis: Path
    sig_ref: str
    sig_pybis: str


BENCHES = [
    BenchNode(
        bench="simple_fixture",
        node_label="pad",
        raw_ref=ROOT / "tb_simple_multiedge_refspice_45n_batch.raw",
        raw_pybis=ROOT / "tb_simple_multiedge_pybis_45n_batch.raw",
        sig_ref="v(pad_ref)",
        sig_pybis="v(pad)",
    ),
    BenchNode(
        bench="simple_fixture",
        node_label="load",
        raw_ref=ROOT / "tb_simple_multiedge_refspice_45n_batch.raw",
        raw_pybis=ROOT / "tb_simple_multiedge_pybis_45n_batch.raw",
        sig_ref="v(ntst_ref)",
        sig_pybis="v(ntst)",
    ),
    BenchNode(
        bench="actual_channel",
        node_label="tx_pad",
        raw_ref=ROOT / "tb_channel_multiedge_refspice_45n_batch.raw",
        raw_pybis=ROOT / "tb_channel_multiedge_pybis_45n_batch.raw",
        sig_ref="v(tx_out_ref)",
        sig_pybis="v(tx_out)",
    ),
    BenchNode(
        bench="actual_channel",
        node_label="rx_load",
        raw_ref=ROOT / "tb_channel_multiedge_refspice_45n_batch.raw",
        raw_pybis=ROOT / "tb_channel_multiedge_pybis_45n_batch.raw",
        sig_ref="v(n10b)",
        sig_pybis="v(n10b)",
    ),
]


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


def find_crossings(time_ns: np.ndarray, signal: np.ndarray, threshold: float, edge_types: list[str]):
    crossings = []
    start_idx = 1
    for edge_type in edge_types:
        found = None
        for i in range(start_idx, len(signal)):
            y0 = signal[i - 1]
            y1 = signal[i]
            if edge_type == "rise" and y0 < threshold <= y1:
                x0 = time_ns[i - 1]
                x1 = time_ns[i]
                found = x0 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
                start_idx = i + 1
                break
            if edge_type == "fall" and y0 > threshold >= y1:
                x0 = time_ns[i - 1]
                x1 = time_ns[i]
                found = x0 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
                start_idx = i + 1
                break
        if found is None:
            raise RuntimeError(f"Could not find {edge_type} crossing at {threshold} V")
        crossings.append(found)
    return np.asarray(crossings, dtype=float)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for bench in BENCHES:
        ref = parse_ngspice_raw(bench.raw_ref)
        py = parse_ngspice_raw(bench.raw_pybis)

        t_ref = ref["time"] * 1e9
        t_py = py["time"] * 1e9

        x_ref = find_crossings(t_ref, ref[bench.sig_ref], THRESHOLD_V, EDGE_SEQUENCE)
        x_py = find_crossings(t_py, py[bench.sig_pybis], THRESHOLD_V, EDGE_SEQUENCE)
        delta = x_py - x_ref

        for idx, edge_type in enumerate(EDGE_SEQUENCE, start=1):
            results.append(
                {
                    "bench": bench.bench,
                    "node": bench.node_label,
                    "edge_index": idx,
                    "edge_type": edge_type,
                    "threshold_v": THRESHOLD_V,
                    "ref_cross_ns": float(x_ref[idx - 1]),
                    "pybis_cross_ns": float(x_py[idx - 1]),
                    "pybis_minus_ref_ns": float(delta[idx - 1]),
                }
            )

    with CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "bench",
                "node",
                "edge_index",
                "edge_type",
                "threshold_v",
                "ref_cross_ns",
                "pybis_cross_ns",
                "pybis_minus_ref_ns",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    grouped = {}
    for row in results:
        key = (row["bench"], row["node"])
        grouped.setdefault(key, []).append(row["pybis_minus_ref_ns"])

    lines = []
    lines.append(f"Threshold used: {THRESHOLD_V:.3f} V")
    lines.append("")
    lines.append("Per-bench delay constancy summary (pybis crossing time minus refspice crossing time):")
    lines.append("")

    for (bench_name, node_name), values in grouped.items():
        arr = np.asarray(values, dtype=float)
        lines.append(f"{bench_name} / {node_name}")
        lines.append(f"  mean delay : {np.mean(arr):.6f} ns")
        lines.append(f"  std dev    : {np.std(arr):.6f} ns")
        lines.append(f"  min delay  : {np.min(arr):.6f} ns")
        lines.append(f"  max delay  : {np.max(arr):.6f} ns")
        lines.append(f"  span       : {(np.max(arr) - np.min(arr)):.6f} ns")
        lines.append("")

    TXT_PATH.write_text("\n".join(lines))

    plt.rcParams.update(
        {
            "figure.figsize": (11, 8),
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
        }
    )

    fig, axes = plt.subplots(2, 2, sharex=True, sharey=False)
    axes = axes.ravel()

    panel_order = [
        ("simple_fixture", "pad"),
        ("simple_fixture", "load"),
        ("actual_channel", "tx_pad"),
        ("actual_channel", "rx_load"),
    ]

    for ax, key in zip(axes, panel_order):
        arr = np.asarray(grouped[key], dtype=float)
        ax.plot(range(1, len(arr) + 1), arr, marker="o", linewidth=1.8)
        ax.axhline(np.mean(arr), color="tab:red", linestyle="--", linewidth=1.2, label=f"mean={np.mean(arr):.3f} ns")
        ax.set_title(f"{key[0]} / {key[1]}")
        ax.set_xlabel("Transition Index")
        ax.set_ylabel("pybis - refspice delay (ns)")
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(1, len(arr) + 1))
        ax.legend(loc="best")

    fig.suptitle("Timing Offset Constancy Across Multiple Transitions")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT_DIR / "timing_offset_constancy.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote: {CSV_PATH}")
    print(f"Wrote: {TXT_PATH}")
    print(f"Wrote: {OUT_DIR / 'timing_offset_constancy.png'}")


if __name__ == "__main__":
    main()
