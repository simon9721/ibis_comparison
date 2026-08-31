#!/usr/bin/env python3
"""Is the silicon Ku target reachable, or is Ku/Kd itself the limit?

Silicon Ku/Kd is by construction the coefficient trajectory that reproduces the
transistor exactly through the IBIS output equation. So the format is not in
question -- the only question is whether a given algorithm produces that
trajectory. This measures how far each algorithm lands from it.

Gaps are the mean |dKu| against silicon, taken only where silicon's own Ku is
slow-moving (|dKu/dt| < 0.5 per ns). Fast edges are excluded because the
extraction is unreliable within roughly 200 ps of one, which
kukd_load_transfer_test and kukd_fixture_variants both established.

The result contradicts the impression that silicon and native IBIS agree.
They agree closely on 4 of 17 cases, three of which are io_buf short-high -- the
cases the offset investigation has been staring at. Elsewhere native IBIS is off
by 0.01 to 0.31, and the shipped gate-state model is closer to silicon than
native IBIS on 8 of 17, by as much as a hundredfold on inv_chain short-high.

    py -3.14 scripts/build_kukd_headroom_figure.py
"""
from __future__ import annotations

import argparse
import csv
import glob
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".codex_deps" / "presentation" / "python"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

RECOVERY = ROOT / "results" / "silicon_kukd_recovery_uniform_2026-08-27" / "waveforms"
OUT = ROOT / "results" / "silicon_kukd_figures_2026-08-27"

NATIVE = "#2B6CA3"
MODEL = "#C05621"
SLOW_LIMIT = 0.5
DPI = 175


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    values = np.array([[float(x) if x not in ("", "nan") else np.nan for x in r]
                       for r in rows[1:]])
    return {name: values[:, i] for i, name in enumerate(rows[0])}


def gaps() -> list[tuple[str, float, float]]:
    out = []
    for path in sorted(glob.glob(str(RECOVERY / "*.csv"))):
        d = load(Path(path))
        t = d["time_ns"]
        slow = np.isfinite(d["silicon_ku"]) & (
            np.abs(np.gradient(d["silicon_ku"], t)) < SLOW_LIMIT)
        out.append((
            Path(path).stem.replace("_", " "),
            float(np.abs(d["silicon_ku"][slow] - d["native_ku"][slow]).mean()),
            float(np.abs(d["silicon_ku"][slow] - d["model_ku"][slow]).mean()),
        ))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    rows = gaps()
    rows.sort(key=lambda r: r[1], reverse=True)
    labels = [r[0] for r in rows]
    native = np.array([r[1] for r in rows])
    model = np.array([r[2] for r in rows])
    y = np.arange(len(rows))

    fig, axis = plt.subplots(figsize=(12.8, 8.4))
    axis.barh(y + 0.20, native, height=0.38, color=NATIVE, label="native IBIS")
    axis.barh(y - 0.20, model, height=0.38, color=MODEL, label="gate-state, as shipped")
    axis.set_yticks(y)
    axis.set_yticklabels(labels, fontsize=10.5)
    axis.invert_yaxis()
    axis.set_xlabel("mean |Ku − silicon Ku|, away from fast edges", fontsize=12.5)
    axis.set_xlim(0, max(native.max(), model.max()) * 1.08)
    axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8, axis="x")
    axis.tick_params(labelsize=11)
    for spine in axis.spines.values():
        spine.set_color("#3A4753")
    axis.set_title("How far each build lands from the silicon coefficients",
                   fontsize=15.5, fontweight="bold", pad=11)
    axis.legend(fontsize=12, loc="lower right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(out / "13_distance_from_silicon_ku.png", dpi=DPI)
    plt.close(fig)

    print(f"{'case':<28}{'native':>9}{'model':>9}   closer")
    for label, n, m in rows:
        print(f"{label:<28}{n:9.4f}{m:9.4f}   {'model' if m < n else 'native'}")
    print(f"\n  silicon and native agree within 0.02 on {(native < 0.02).sum()} of {len(rows)}")
    print(f"  the model is closer to silicon than native IBIS on "
          f"{(model < native).sum()} of {len(rows)}")
    print(f"\nwrote {(out / '13_distance_from_silicon_ku.png').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
