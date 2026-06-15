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


def run_command(args: list[str], timeout: int, log_dir: Path, label: str) -> int:
    log_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    (log_dir / f"{label}_stdout.txt").write_text(completed.stdout, encoding="utf-8", errors="replace")
    (log_dir / f"{label}_stderr.txt").write_text(completed.stderr, encoding="utf-8", errors="replace")
    return completed.returncode


def select_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows = read_csv(args.manifest.resolve())
    selected: list[dict[str, str]] = []
    explicit_ids = set(args.channel_id or [])
    explicit_paths = {str(Path(path).as_posix()) for path in (args.relative_path or [])}
    for row in rows:
        if explicit_ids and row.get("channel_id") not in explicit_ids:
            continue
        if explicit_paths and row.get("relative_path", "").replace("\\", "/") not in explicit_paths:
            continue
        if not explicit_ids and not explicit_paths:
            if row.get("dominant_path") != args.dominant_path:
                continue
            try:
                if float(row.get("dominant_peak_mag_db") or -1e9) < args.min_peak_db:
                    continue
            except ValueError:
                continue
        selected.append(row)
    selected.sort(key=lambda row: float(row.get("dominant_delay_ns") or 0.0))
    if args.max_channels:
        selected = selected[: args.max_channels]
    return selected


def choose_trim(summary_csv: Path) -> dict[str, str]:
    rows = read_csv(summary_csv)
    if not rows:
        return {}

    def sort_key(row: dict[str, str]):
        return (
            str(row.get("all_pass", "")).lower() != "true",
            -int(float(row.get("pass_count") or 0)),
            float(row.get("max_rx_active_rmse_v") or 1e9),
            abs(float(row.get("mean_rx_rise50_delta_ps") or 1e9)),
        )

    return sorted(rows, key=sort_key)[0]


def aggregate_comparison(comparison_csv: Path) -> dict[str, object]:
    rows = read_csv(comparison_csv)
    out: dict[str, object] = {
        "comparison_rows": len(rows),
        "comparison_pass_count": sum(1 for row in rows if row.get("case_class") == "PASS"),
    }
    for key in ("rx_active_rmse_v", "rx_active_maxabs_v", "rx_rise50_delta_ps", "rx_fall50_delta_ps", "tx_active_rmse_v"):
        values = [float(row[key]) for row in rows if row.get(key, "") not in ("", "nan")]
        if values:
            out[f"max_{key}"] = max(abs(value) for value in values)
            out[f"mean_{key}"] = sum(values) / len(values)
    out["comparison_all_pass"] = out["comparison_rows"] == out["comparison_pass_count"] and out["comparison_rows"] > 0
    return out


def channel_name(row: dict[str, str]) -> str:
    path = Path(row.get("relative_path") or row.get("path") or row.get("channel_id") or "channel")
    return path.stem


def run_channel(row: dict[str, str], args: argparse.Namespace) -> dict[str, object]:
    name = channel_name(row)
    channel_dir = args.out_dir.resolve() / name
    log_dir = channel_dir / "driver_logs"
    touchstone = ROOT / row["relative_path"]
    stop_ns = max(args.min_stop_ns, float(row.get("recommended_audit_stop_ns") or 0.0))
    initial_delay_ns = float(row.get("dominant_delay_ns") or 0.0)
    hspice_dir = channel_dir / "hspice_native"
    result: dict[str, object] = {
        "channel_id": row.get("channel_id", ""),
        "channel_name": name,
        "relative_path": row.get("relative_path", ""),
        "dominant_path": row.get("dominant_path", ""),
        "dominant_delay_ns": row.get("dominant_delay_ns", ""),
        "dominant_peak_mag_db": row.get("dominant_peak_mag_db", ""),
        "stop_ns": stop_ns,
        "initial_delay_ns": initial_delay_ns,
        "tail_branches": args.tail_branches,
        "out_dir": str(channel_dir.resolve()),
    }

    hspice_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_native_hspice_sparam_audit.py"),
        "--touchstone",
        str(touchstone),
        "--ports",
        "4",
        "--out-dir",
        str(hspice_dir),
        "--stop-ns",
        str(stop_ns),
        "--timeout",
        str(args.hspice_timeout),
    ]
    if args.reuse_existing:
        hspice_cmd.append("--reuse-existing")
    rc = run_command(hspice_cmd, args.hspice_timeout + 60, log_dir, "hspice")
    result["hspice_rc"] = rc
    if rc != 0:
        result["status"] = "hspice_failed"
        return result

    fit_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_delay_aware_parallel_sparam_model.py"),
        "--hspice-dir",
        str(hspice_dir),
        "--out-dir",
        str(channel_dir),
        "--initial-delay-ns",
        str(initial_delay_ns),
        "--stop-ns",
        str(stop_ns),
        "--branches",
        str(args.branches),
        "--tail-branches",
        str(args.tail_branches),
        "--timeout",
        str(args.ngspice_timeout),
    ]
    rc = run_command(fit_cmd, args.fit_timeout, log_dir, "fit_ngspice")
    result["fit_ngspice_rc"] = rc
    if rc != 0:
        result["status"] = "fit_or_ngspice_failed"
        return result

    initial_csv = channel_dir / "comparison" / "comparison.csv"
    if initial_csv.exists():
        initial = aggregate_comparison(initial_csv)
        result.update({f"initial_{key}": value for key, value in initial.items()})

    trim_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "sweep_delay_reduced_model_trim.py"),
        "--base-model",
        str(channel_dir / "models" / "s_equivalent_delay_parallel.sp"),
        "--hspice-dir",
        str(hspice_dir),
        "--out-dir",
        str(channel_dir / "trim_sweep"),
        "--stop-ns",
        str(stop_ns),
        "--timeout",
        str(args.ngspice_timeout),
        "--trims-ps",
        *[str(value) for value in args.trims_ps],
    ]
    rc = run_command(trim_cmd, args.trim_timeout, log_dir, "trim_sweep")
    result["trim_rc"] = rc
    if rc != 0:
        result["status"] = "trim_failed"
        return result

    accepted = choose_trim(channel_dir / "trim_sweep" / "trim_summary.csv")
    for key, value in accepted.items():
        result[f"accepted_{key}"] = value
    label = f"trim_{float(accepted.get('trim_ps', 0.0)):+.0f}ps".replace("+", "p").replace("-", "m")
    accepted_csv = channel_dir / "trim_sweep" / label / "comparison" / "comparison.csv"
    if accepted_csv.exists():
        accepted_metrics = aggregate_comparison(accepted_csv)
        result.update({f"accepted_{key}": value for key, value in accepted_metrics.items()})
    result["accepted_label"] = label
    result["status"] = "pass" if str(result.get("accepted_all_pass") or result.get("accepted_comparison_all_pass")).lower() == "true" else "needs_review"
    return result


def write_report(out_dir: Path, rows: list[dict[str, object]]) -> None:
    passed = [row for row in rows if row.get("status") == "pass"]
    lines = [
        "# Delay-parallel Batch Results",
        "",
        f"- Channels: {len(rows)}",
        f"- PASS: {len(passed)}",
        f"- Needs review/fail: {len(rows) - len(passed)}",
        "",
        "| channel | status | accepted trim (ps) | max RX RMSE (V) | max RX maxabs (V) | max rise delta (ps) | max fall delta (ps) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row.get('channel_name', '')}` | `{row.get('status', '')}` | "
            f"{row.get('accepted_trim_ps', '')} | {row.get('accepted_max_rx_active_rmse_v', '')} | "
            f"{row.get('accepted_max_rx_active_maxabs_v', '')} | {row.get('accepted_max_rx_rise50_delta_ps', '')} | "
            f"{row.get('accepted_max_rx_fall50_delta_ps', '')} |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-run the delay-parallel ngspice-vs-HSPICE flow on selected S-parameter channels.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "results" / "sparam_ngspice_flow_optimized_2026-06-08" / "manifest_delay_aware_required.csv")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--channel-id", action="append")
    parser.add_argument("--relative-path", action="append")
    parser.add_argument("--dominant-path", default="S31")
    parser.add_argument("--min-peak-db", type=float, default=-3.0)
    parser.add_argument("--max-channels", type=int, default=0)
    parser.add_argument("--min-stop-ns", type=float, default=35.0)
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--tail-branches", type=int, default=1)
    parser.add_argument("--hspice-timeout", type=int, default=420)
    parser.add_argument("--ngspice-timeout", type=int, default=180)
    parser.add_argument("--fit-timeout", type=int, default=900)
    parser.add_argument("--trim-timeout", type=int, default=900)
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Keep existing batch_summary.csv rows and skip channels that already passed.")
    parser.add_argument("--force", action="store_true", help="Rerun selected channels even if --resume finds an existing PASS row.")
    parser.add_argument("--trims-ps", type=float, nargs="+", default=[-30, -20, -15, -10, -5, 0, 5, 10, 15])
    args = parser.parse_args()

    selected = select_rows(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "selected_channels.csv", selected)
    rows: list[dict[str, object]] = []
    existing_by_id: dict[str, dict[str, object]] = {}
    summary_csv = args.out_dir / "batch_summary.csv"
    if args.resume and summary_csv.exists():
        rows = list(read_csv(summary_csv))
        existing_by_id = {str(row.get("channel_id", "")): row for row in rows if row.get("channel_id")}

    for idx, row in enumerate(selected, start=1):
        existing = existing_by_id.get(row.get("channel_id", ""))
        if existing and existing.get("status") == "pass" and not args.force:
            print(f"[{idx}/{len(selected)}] {row.get('relative_path')} -- skip existing PASS")
            continue

        print(f"[{idx}/{len(selected)}] {row.get('relative_path')}")
        result = run_channel(row, args)
        if existing:
            rows = [saved for saved in rows if saved.get("channel_id") != row.get("channel_id")]
        rows.append(result)
        write_csv(args.out_dir / "batch_summary.csv", rows)
        write_report(args.out_dir, rows)
        print(result.get("channel_name"), result.get("status"), result.get("accepted_trim_ps", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
