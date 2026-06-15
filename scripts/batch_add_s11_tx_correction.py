from __future__ import annotations

import argparse
import csv
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def aggregate_comparison(path: Path) -> dict[str, object]:
    rows = read_csv(path)
    out: dict[str, object] = {"comparison_rows": len(rows), "pass_count": sum(1 for row in rows if row.get("case_class") == "PASS")}
    for key in ("rx_active_rmse_v", "rx_active_maxabs_v", "tx_active_rmse_v", "tx_active_maxabs_v", "rx_rise50_delta_ps", "rx_fall50_delta_ps"):
        values = [float(row[key]) for row in rows if row.get(key, "") not in ("", "nan")]
        if values:
            out[f"max_{key}"] = max(abs(value) for value in values)
            out[f"mean_{key}"] = sum(values) / len(values)
    out["all_pass"] = out["comparison_rows"] > 0 and out["comparison_rows"] == out["pass_count"]
    return out


def strength_label(value: float) -> str:
    return f"strength_{value:.3f}".replace(".", "p").replace("-", "m")


def select_rows(rows: list[dict[str, str]], include_duplicates: bool) -> list[dict[str, str]]:
    selected = [row for row in rows if row.get("status") == "pass"]
    if include_duplicates:
        return sorted(selected, key=lambda row: row.get("channel_name", ""))
    unique: dict[str, dict[str, str]] = {}
    for row in selected:
        name = row.get("channel_name", "")
        key = name.replace("_5F3N_t", "_t").replace("_8F_t", "_t")
        saved = unique.get(key)
        if saved is None or ("5F3N" in name and "5F3N" not in saved.get("channel_name", "")):
            unique[key] = row
    return sorted(unique.values(), key=lambda row: row.get("channel_name", ""))


def run_strength(row: dict[str, str], args: argparse.Namespace, strength: float, target_dir: Path, base_model: Path) -> dict[str, object]:
    source_dir = Path(row["out_dir"])
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "add_s11_tx_correction.py"),
        "--hspice-dir",
        str(source_dir / "hspice_native"),
        "--base-model",
        str(base_model),
        "--out-dir",
        str(target_dir),
        "--stop-ns",
        str(row.get("stop_ns") or 35.0),
        "--branches",
        str(args.branches),
        "--tail-branches",
        str(args.tail_branches),
        "--strength",
        str(strength),
        "--timeout",
        str(args.timeout),
    ]
    target_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False, timeout=args.timeout * 4)
    (target_dir / "driver_stdout.txt").write_text(completed.stdout, encoding="utf-8", errors="replace")
    (target_dir / "driver_stderr.txt").write_text(completed.stderr, encoding="utf-8", errors="replace")

    result: dict[str, object] = {
        "channel_name": row["channel_name"],
        "return_code": completed.returncode,
        "strength": strength,
        "base_model": str(base_model),
        "out_dir": str(target_dir),
    }
    proto_csv = target_dir / "comparison" / "comparison.csv"
    if proto_csv.exists():
        for key, value in aggregate_comparison(proto_csv).items():
            result[f"s11_{key}"] = value
    result["status"] = "pass" if completed.returncode == 0 and str(result.get("s11_all_pass")).lower() == "true" else "needs_review"
    return result


def choose_result(results: list[dict[str, object]]) -> dict[str, object]:
    passing = [row for row in results if row.get("status") == "pass"]
    if passing:
        return sorted(
            passing,
            key=lambda row: (
                -float(row.get("strength") or 0.0),
                float(row.get("s11_max_tx_active_rmse_v") or 1e9),
            ),
        )[0]
    return sorted(
        results,
        key=lambda row: (
            -int(float(row.get("s11_pass_count") or 0)),
            float(row.get("s11_max_rx_active_rmse_v") or 1e9),
            float(row.get("s11_max_tx_active_rmse_v") or 1e9),
        ),
    )[0]


def write_report(out_dir: Path, selected: list[dict[str, object]], sweep: list[dict[str, object]], strengths: list[float]) -> None:
    pass_count = sum(1 for row in selected if row.get("status") == "pass")
    lines = [
        "# S11 Strength Sweep",
        "",
        f"- Channels: `{len(selected)}`",
        f"- Selected PASS: `{pass_count}/{len(selected)}`",
        f"- Strengths tried: `{', '.join(f'{value:g}' for value in strengths)}`",
        "",
        "| channel | selected strength | status | baseline TX RMSE (V) | selected TX RMSE (V) | selected RX RMSE (V) | selected rise delta (ps) | selected fall delta (ps) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in selected:
        lines.append(
            f"| `{row.get('channel_name', '')}` | {row.get('selected_strength', '')} | `{row.get('status', '')}` | "
            f"{row.get('baseline_max_tx_active_rmse_v', '')} | {row.get('selected_max_tx_active_rmse_v', '')} | "
            f"{row.get('selected_max_rx_active_rmse_v', '')} | {row.get('selected_max_rx_rise50_delta_ps', '')} | "
            f"{row.get('selected_max_rx_fall50_delta_ps', '')} |"
        )
    lines.extend(
        [
            "",
            "## Sweep Rows",
            "",
            "| channel | strength | status | TX RMSE (V) | RX RMSE (V) | rise delta (ps) | fall delta (ps) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sweep:
        lines.append(
            f"| `{row.get('channel_name', '')}` | {row.get('strength', '')} | `{row.get('status', '')}` | "
            f"{row.get('s11_max_tx_active_rmse_v', '')} | {row.get('s11_max_rx_active_rmse_v', '')} | "
            f"{row.get('s11_max_rx_rise50_delta_ps', '')} | {row.get('s11_max_rx_fall50_delta_ps', '')} |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch augment accepted S31 models with S11-like TX corrections.")
    parser.add_argument("--summary", type=Path, default=ROOT / "results" / "sparam_cisco_delay_parallel_batch_2026-06-08" / "batch_summary.csv")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "sparam_cisco_s11_proto_2026-06-09")
    parser.add_argument("--include-duplicates", action="store_true")
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--tail-branches", type=int, default=1)
    parser.add_argument("--strength", type=float, default=None, help="Run one correction strength instead of a sweep.")
    parser.add_argument("--strengths", type=float, nargs="+", default=[0.0, 0.25, 0.5, 0.75, 1.0])
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    rows = select_rows(read_csv(args.summary.resolve()), args.include_duplicates)
    strengths = [args.strength] if args.strength is not None else args.strengths
    args.out_dir.mkdir(parents=True, exist_ok=True)
    selected_results: list[dict[str, object]] = []
    sweep_results: list[dict[str, object]] = []
    for idx, row in enumerate(rows, start=1):
        name = row["channel_name"]
        source_dir = Path(row["out_dir"])
        accepted_model = source_dir / "trim_sweep" / row.get("accepted_label", "") / "models" / "s_equivalent_delay_reduced.sp"
        base_model = accepted_model if accepted_model.exists() else source_dir / "models" / "s_equivalent_delay_parallel.sp"
        print(f"[{idx}/{len(rows)}] {name}")

        channel_results: list[dict[str, object]] = []
        accepted_csv = source_dir / "trim_sweep" / row["accepted_label"] / "comparison" / "comparison.csv"
        baseline: dict[str, object] = {}
        if accepted_csv.exists():
            for key, value in aggregate_comparison(accepted_csv).items():
                baseline[f"baseline_{key}"] = value

        for strength in strengths:
            target_dir = args.out_dir.resolve() / name / strength_label(float(strength))
            result = run_strength(row, args, float(strength), target_dir, base_model)
            result.update(baseline)
            channel_results.append(result)
            sweep_results.append(result)
            write_csv(args.out_dir / "s11_strength_sweep.csv", sweep_results)
            print(
                " ",
                strength,
                result["status"],
                "tx",
                result.get("baseline_max_tx_active_rmse_v"),
                "->",
                result.get("s11_max_tx_active_rmse_v"),
            )

        chosen = choose_result(channel_results)
        selected: dict[str, object] = {
            "channel_name": name,
            "status": chosen.get("status"),
            "selected_strength": chosen.get("strength"),
            "selected_out_dir": chosen.get("out_dir"),
            "base_model": chosen.get("base_model"),
        }
        selected.update(baseline)
        for key, value in chosen.items():
            if key.startswith("s11_"):
                selected[f"selected_{key[4:]}"] = value
        selected_results.append(selected)
        write_csv(args.out_dir / "s11_selected_summary.csv", selected_results)
        write_csv(args.out_dir / "s11_batch_summary.csv", selected_results)
        write_report(args.out_dir.resolve(), selected_results, sweep_results, [float(value) for value in strengths])
        print(
            name,
            "selected",
            selected.get("selected_strength"),
            selected.get("status"),
            "tx",
            selected.get("baseline_max_tx_active_rmse_v"),
            "->",
            selected.get("selected_max_tx_active_rmse_v"),
        )

    write_csv(args.out_dir / "s11_strength_sweep.csv", sweep_results)
    write_csv(args.out_dir / "s11_selected_summary.csv", selected_results)
    write_csv(args.out_dir / "s11_batch_summary.csv", selected_results)
    write_report(args.out_dir.resolve(), selected_results, sweep_results, [float(value) for value in strengths])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
