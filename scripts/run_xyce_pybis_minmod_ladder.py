"""Build a focused Xyce pybis minimum-modification ladder.

By default this script consolidates existing Xyce pybis experiment metrics into
one clean matrix. Use ``--run-missing`` when you want it to run missing Xyce
matrix points through the existing tail-fix harness.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_xyce_pybis_tail_fixes import (  # noqa: E402
    CANDIDATES,
    CHANNEL_BENCHES,
    Candidate,
    Bench,
    compare_to_ref,
    csv_path,
    load_xyce_csv,
    run_one,
)


PLOTS_DIR = ROOT / "plots" / "xyce_pybis"
OUT_DIR = ROOT / "results" / "xyce_pybis_minmod_ladder_2026-05-11"

BENCH_ORDER = [
    "channel_pulsetrain_200p",
    "channel_bitpattern_200p",
    "channel_prbs7_200n",
    "channel_prbs7_1000n",
]

BENCH_LABELS = {
    "channel_pulsetrain_200p": "pulse train\n40 ns",
    "channel_bitpattern_200p": "bit pattern\n45 ns",
    "channel_prbs7_200n": "PRBS7\n200 ns",
    "channel_prbs7_1000n": "PRBS7\n1000 ns",
}

LADDER = [
    {
        "candidate": "direct200",
        "title": "direct Xyce syntax port, tanh200 gates",
        "modification": "syntax port only",
    },
    {
        "candidate": "tanh100",
        "title": "all gates tanh100",
        "modification": "very mild global smoothing",
    },
    {
        "candidate": "tanh92",
        "title": "all gates tanh92",
        "modification": "mild global smoothing",
    },
    {
        "candidate": "flat4p2",
        "title": "KUR/KDR flat tail after 4.2 ns",
        "modification": "tail table only",
    },
    {
        "candidate": "edge50",
        "title": "edge/latch tanh50 only",
        "modification": "localized edge smoothing only",
    },
    {
        "candidate": "edge50_flat4p2",
        "title": "edge/latch tanh50 plus 4.2 ns flat tail",
        "modification": "localized edge smoothing plus tail",
    },
    {
        "candidate": "edge52_flat4p2",
        "title": "edge/latch tanh52 plus 4.2 ns flat tail",
        "modification": "near-edge50 stress point",
    },
    {
        "candidate": "edge15_flat4p2",
        "title": "edge/latch tanh15 plus 4.2 ns flat tail",
        "modification": "current full PRBS/RLGC practical pass",
    },
    {
        "candidate": "tanh15",
        "title": "all gates tanh15",
        "modification": "older broad smoothing fallback",
    },
]


def str_bool(value: object) -> bool | None:
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def float_or_blank(value: object) -> float | str:
    if value is None or value == "":
        return ""
    try:
        return float(value)
    except (TypeError, ValueError):
        return ""


def candidate_title(name: str) -> str:
    for row in LADDER:
        if row["candidate"] == name:
            return row["title"]
    return name


def candidate_modification(name: str) -> str:
    for row in LADDER:
        if row["candidate"] == name:
            return row["modification"]
    return ""


def put_best(
    rows: dict[tuple[str, str], dict[str, object]],
    row: dict[str, object],
) -> None:
    key = (str(row["candidate"]), str(row["bench"]))
    old = rows.get(key)
    if old is None:
        rows[key] = row
        return

    old_complete = str_bool(old.get("completed"))
    new_complete = str_bool(row.get("completed"))
    old_t = float_or_blank(old.get("t_end_ns"))
    new_t = float_or_blank(row.get("t_end_ns"))
    old_rmse = old.get("rmse_mv", "")
    new_rmse = row.get("rmse_mv", "")

    if new_complete is True and old_complete is not True:
        rows[key] = row
    elif new_complete == old_complete:
        if new_t != "" and (old_t == "" or float(new_t) > float(old_t)):
            rows[key] = row
        elif new_t == old_t and new_rmse != "" and old_rmse == "":
            rows[key] = row


def normalize_tailfix_row(row: dict[str, str], source: str) -> dict[str, object]:
    return {
        "candidate": row.get("candidate", ""),
        "candidate_title": row.get("candidate_title", ""),
        "modification": candidate_modification(row.get("candidate", "")),
        "bench": row.get("bench", ""),
        "completed": row.get("completed", ""),
        "target_ns": "",
        "t_end_ns": row.get("t_end_ns", ""),
        "rmse_mv": row.get("rmse_mv", ""),
        "max_abs_mv": row.get("max_abs_mv", ""),
        "source": source,
        "deck": row.get("deck", ""),
        "output": row.get("output", ""),
        "note": "",
    }


def load_tailfix_metrics(rows: dict[tuple[str, str], dict[str, object]]) -> None:
    for path in sorted(PLOTS_DIR.glob("xyce_pybis_tailfix*_metrics.csv")):
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if "candidate" in row and "bench" in row:
                    put_best(rows, normalize_tailfix_row(row, path.name))

    summary = PLOTS_DIR / "xyce_pybis_tailfix_recommendation_summary.csv"
    if summary.exists():
        with summary.open(newline="") as f:
            for row in csv.DictReader(f):
                put_best(rows, normalize_tailfix_row(row, summary.name))


def normalize_minimal_sweep_row(row: dict[str, str]) -> dict[str, object]:
    name = row["case"].strip()
    if name == "direct tanh200":
        candidate = "direct200"
    else:
        candidate = name
    return {
        "candidate": candidate,
        "candidate_title": candidate_title(candidate),
        "modification": candidate_modification(candidate),
        "bench": "channel_pulsetrain_200p",
        "completed": row.get("complete", ""),
        "target_ns": row.get("target_ns", ""),
        "t_end_ns": row.get("t_end_ns", ""),
        "rmse_mv": "",
        "max_abs_mv": "",
        "source": "xyce_pybis_minimal_relaxation_sweep.csv",
        "deck": "",
        "output": "",
        "note": "minimal relaxation sweep",
    }


def normalize_prbs_relax_row(row: dict[str, str]) -> dict[str, object] | None:
    case = row["case"].strip()
    match = re.match(r"(?P<candidate>\S+)\s+PRBS(?P<stop>\d+)", case)
    if not match:
        return None
    stop = match.group("stop")
    if stop == "200":
        bench = "channel_prbs7_200n"
    elif stop == "1000":
        bench = "channel_prbs7_1000n"
    else:
        return None
    candidate = match.group("candidate")
    return {
        "candidate": candidate,
        "candidate_title": candidate_title(candidate),
        "modification": candidate_modification(candidate),
        "bench": bench,
        "completed": row.get("complete", ""),
        "target_ns": row.get("target_ns", ""),
        "t_end_ns": row.get("t_end_ns", ""),
        "rmse_mv": "",
        "max_abs_mv": "",
        "source": "xyce_pybis_prbs_relaxation_candidates.csv",
        "deck": "",
        "output": "",
        "note": "PRBS relaxation candidate sweep",
    }


def load_historical_rows() -> dict[tuple[str, str], dict[str, object]]:
    rows: dict[tuple[str, str], dict[str, object]] = {}
    load_tailfix_metrics(rows)

    minimal = PLOTS_DIR / "xyce_pybis_minimal_relaxation_sweep.csv"
    if minimal.exists():
        with minimal.open(newline="") as f:
            for row in csv.DictReader(f):
                put_best(rows, normalize_minimal_sweep_row(row))

    prbs = PLOTS_DIR / "xyce_pybis_prbs_relaxation_candidates.csv"
    if prbs.exists():
        with prbs.open(newline="") as f:
            for row in csv.DictReader(f):
                normalized = normalize_prbs_relax_row(row)
                if normalized is not None:
                    put_best(rows, normalized)
    return rows


def candidate_by_name(name: str) -> Candidate:
    if name == "direct200":
        return Candidate(
            name="direct200",
            title="direct Xyce syntax port, tanh200 gates",
            mode="base",
            include_file="driver_OutputInput_Typical.sub",
        )
    for candidate in CANDIDATES:
        if candidate.name == name:
            return candidate
    raise KeyError(name)


def bench_by_name(name: str) -> Bench:
    for bench in CHANNEL_BENCHES:
        if bench.name == name:
            return bench
    raise KeyError(name)


def summarize_existing(bench: Bench, candidate: Candidate) -> dict[str, object] | None:
    out = csv_path(bench, candidate)
    if not out.exists():
        return None
    try:
        data = load_xyce_csv(out)
        t = data["time"]
        y = data[bench.xyce_node]
        completed = float(t[-1] * 1e9) >= bench.target_ns - 0.05
        row: dict[str, object] = {
            "candidate": candidate.name,
            "candidate_title": candidate.title,
            "modification": candidate_modification(candidate.name),
            "bench": bench.name,
            "completed": completed,
            "target_ns": bench.target_ns,
            "t_end_ns": float(t[-1] * 1e9),
            "rmse_mv": "",
            "max_abs_mv": "",
            "source": "existing_csv",
            "deck": str((out.with_suffix("")).relative_to(ROOT)).replace("\\", "/"),
            "output": str(out.relative_to(ROOT)).replace("\\", "/"),
            "note": "summarized from existing CSV",
        }
        row.update(compare_to_ref(bench, data))
        row["vout_min"] = float(np.min(y))
        row["vout_max"] = float(np.max(y))
        return row
    except Exception as exc:
        return {
            "candidate": candidate.name,
            "candidate_title": candidate.title,
            "modification": candidate_modification(candidate.name),
            "bench": bench.name,
            "completed": False,
            "target_ns": bench.target_ns,
            "t_end_ns": "",
            "rmse_mv": "",
            "max_abs_mv": "",
            "source": "existing_csv",
            "deck": "",
            "output": str(out.relative_to(ROOT)).replace("\\", "/"),
            "note": f"could not summarize existing CSV: {exc}",
        }


def run_missing_rows(
    rows: dict[tuple[str, str], dict[str, object]],
    candidates: list[str],
    benches: list[str],
) -> None:
    for bench_name in benches:
        bench = bench_by_name(bench_name)
        for candidate_name in candidates:
            key = (candidate_name, bench_name)
            if key in rows:
                continue
            candidate = candidate_by_name(candidate_name)
            existing = summarize_existing(bench, candidate)
            if existing is not None:
                put_best(rows, existing)
                continue
            print(f"Running missing Xyce point: {candidate_name} on {bench_name}", flush=True)
            put_best(rows, run_one(bench, candidate))


def selected_rows(rows: dict[tuple[str, str], dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for ladder_row in LADDER:
        candidate = ladder_row["candidate"]
        for bench in BENCH_ORDER:
            row = rows.get((candidate, bench))
            if row is None and bench == "channel_prbs7_200n":
                longer = rows.get((candidate, "channel_prbs7_1000n"))
                if longer is not None and str_bool(longer.get("completed")) is True:
                    row = {
                        "candidate": candidate,
                        "candidate_title": ladder_row["title"],
                        "modification": ladder_row["modification"],
                        "bench": bench,
                        "completed": True,
                        "target_ns": 200.0,
                        "t_end_ns": 200.0,
                        "rmse_mv": "",
                        "max_abs_mv": "",
                        "source": longer.get("source", ""),
                        "deck": longer.get("deck", ""),
                        "output": longer.get("output", ""),
                        "note": "inferred pass from successful 1000 ns PRBS run",
                    }
            if row is None:
                row = {
                    "candidate": candidate,
                    "candidate_title": ladder_row["title"],
                    "modification": ladder_row["modification"],
                    "bench": bench,
                    "completed": "",
                    "target_ns": "",
                    "t_end_ns": "",
                    "rmse_mv": "",
                    "max_abs_mv": "",
                    "source": "",
                    "deck": "",
                    "output": "",
                    "note": "not tested in consolidated data",
                }
            else:
                row = dict(row)
                row.setdefault("candidate_title", ladder_row["title"])
                row.setdefault("modification", ladder_row["modification"])
            out.append(row)
    return out


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    fields = [
        "candidate",
        "candidate_title",
        "modification",
        "bench",
        "completed",
        "target_ns",
        "t_end_ns",
        "rmse_mv",
        "max_abs_mv",
        "source",
        "deck",
        "output",
        "note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def plot_matrix(rows: list[dict[str, object]], path: Path) -> None:
    cand_names = [row["candidate"] for row in LADDER]
    status = np.full((len(cand_names), len(BENCH_ORDER)), 0.5)
    labels = [["not run" for _ in BENCH_ORDER] for _ in cand_names]
    row_map = {(str(r["candidate"]), str(r["bench"])): r for r in rows}

    for r, candidate in enumerate(cand_names):
        for c, bench in enumerate(BENCH_ORDER):
            row = row_map[(candidate, bench)]
            completed = str_bool(row.get("completed"))
            if completed is True:
                status[r, c] = 1.0
            elif completed is False:
                status[r, c] = 0.0
            label_parts = []
            if row.get("t_end_ns") != "":
                label_parts.append(f"{float(row['t_end_ns']):.1f} ns")
            if row.get("rmse_mv") != "":
                label_parts.append(f"{float(row['rmse_mv']):.1f} mV")
            if completed is None and not label_parts:
                label_parts.append("not run")
            labels[r][c] = "\n".join(label_parts)

    cmap = matplotlib.colors.ListedColormap(["#d95f5f", "#dddddd", "#6abf69"])
    fig, ax = plt.subplots(figsize=(12, 6.8))
    ax.imshow(status, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for r in range(len(cand_names)):
        for c in range(len(BENCH_ORDER)):
            ax.text(c, r, labels[r][c], ha="center", va="center", fontsize=8)

    ax.set_xticks(np.arange(len(BENCH_ORDER)))
    ax.set_xticklabels([BENCH_LABELS[b] for b in BENCH_ORDER], fontsize=9)
    ax.set_yticks(np.arange(len(cand_names)))
    ax.set_yticklabels(cand_names, fontsize=9)
    ax.set_title("Xyce pybis minimum-modification ladder on 50 ohm RLGC benches")
    ax.set_xlabel("Bench")
    ax.set_ylabel("Candidate, ordered from least to most modification")
    ax.set_xticks(np.arange(-0.5, len(BENCH_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(cand_names), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def write_readme(rows: list[dict[str, object]], path: Path) -> None:
    def status(candidate: str, bench: str) -> str:
        row = next(r for r in rows if r["candidate"] == candidate and r["bench"] == bench)
        completed = str_bool(row.get("completed"))
        if completed is True:
            return "pass"
        if completed is False:
            t_end = row.get("t_end_ns", "")
            return f"fail/stop {float(t_end):.1f} ns" if t_end != "" else "fail"
        return "not tested"

    lines = [
        "# Xyce pybis Minimum-Modification Ladder",
        "",
        "This folder consolidates the current Xyce pybis modification ladder for",
        "the 50 ohm RLGC benches. Candidates are ordered from closest to the",
        "direct converted model to the current practical full-PRBS workaround.",
        "",
        "## Key Takeaways",
        "",
        f"- Direct tanh200 on the repeated RLGC pulse train: {status('direct200', 'channel_pulsetrain_200p')}.",
        f"- `tanh92` reaches the deterministic RLGC benches, but has no accepted full-PRBS pass.",
        f"- `edge50_flat4p2` passes 200 ns PRBS but stops on the 1000 ns run.",
        f"- `edge15_flat4p2` is the current full 1000 ns PRBS/RLGC pass.",
        f"- Broad all-`tanh15` also passes full PRBS, but with larger waveform error.",
        "",
        "## Files",
        "",
        "- `xyce_pybis_minmod_ladder_summary.csv`: consolidated table",
        "- `xyce_pybis_minmod_ladder_matrix.png`: pass/fail matrix",
        "",
        "Run missing points later with:",
        "",
        "```powershell",
        "python scripts\\run_xyce_pybis_minmod_ladder.py --run-missing",
        "```",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-missing",
        action="store_true",
        help="Run missing ladder points through Xyce using the existing tail-fix harness.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_historical_rows()
    if args.run_missing:
        run_missing_rows(rows, [r["candidate"] for r in LADDER], BENCH_ORDER)

    selected = selected_rows(rows)
    write_csv(selected, OUT_DIR / "xyce_pybis_minmod_ladder_summary.csv")
    plot_matrix(selected, OUT_DIR / "xyce_pybis_minmod_ladder_matrix.png")
    write_readme(selected, OUT_DIR / "README.md")

    print(f"Wrote {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
