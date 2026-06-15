from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compare_sparam_transient_audits import compare_case  # noqa: E402
from run_ngspice_sparam_model_audit import DEFAULT_NGSPICE  # noqa: E402


CASES = ["audit_amp1p5_edge5_r50", "audit_amp1p5_edge50_r50", "audit_amp1p5_edge500_r50"]


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


def write_trimmed_model(base: Path, out: Path, trim_ps: float) -> float:
    text = base.read_text(encoding="ascii")
    match = re.search(r"(TD=)([0-9.]+)n", text)
    if not match:
        raise ValueError(f"Could not find TD=<value>n in {base}")
    base_delay_ns = float(match.group(2))
    new_delay_ns = base_delay_ns + trim_ps * 1e-3
    text = text[: match.start(2)] + f"{new_delay_ns:.12g}" + text[match.end(2) :]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="ascii")
    return new_delay_ns


def run_ngspice_audit(ngspice: Path, model: Path, out_dir: Path, stop_ns: float, timeout: int) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_ngspice_sparam_model_audit.py"),
            "--model",
            str(model.resolve()),
            "--ports",
            "4",
            "--out-dir",
            str(out_dir.resolve()),
            "--stop-ns",
            str(stop_ns),
            "--timeout",
            str(timeout),
            "--ngspice",
            str(ngspice.resolve()),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout + 60,
        check=False,
    )
    (out_dir / "driver_stdout.txt").write_text(completed.stdout, encoding="utf-8", errors="replace")
    (out_dir / "driver_stderr.txt").write_text(completed.stderr, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(f"ngspice audit driver failed rc={completed.returncode}: {completed.stderr[-1000:]}")


def compare(hspice_dir: Path, ng_dir: Path, out_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in CASES:
        rows.append(compare_case(case, hspice_dir / f"{case}_hspice.tr0", ng_dir / f"{case}.raw", 4, out_dir, "ngspice delay-reduced", argparse.Namespace(rx_active_rmse_pass_v=0.02, rx_active_maxabs_pass_v=0.075, tx_active_rmse_pass_v=0.08, delay_pass_ps=25.0)))
    write_csv(out_dir / "comparison.csv", rows)
    return rows


def summarize(rows: list[dict[str, object]], trim_ps: float, delay_ns: float) -> dict[str, object]:
    out: dict[str, object] = {"trim_ps": trim_ps, "delay_ns": delay_ns, "cases": len(rows)}
    for key in ("rx_active_rmse_v", "rx_active_maxabs_v", "rx_rise50_delta_ps", "rx_fall50_delta_ps", "tx_active_rmse_v"):
        values = [float(row[key]) for row in rows if row.get(key, "") != ""]
        out[f"max_{key}"] = max(abs(v) for v in values) if values else ""
        out[f"mean_{key}"] = sum(values) / len(values) if values else ""
    out["pass_count"] = sum(1 for row in rows if row.get("case_class") == "PASS")
    out["all_pass"] = out["pass_count"] == len(rows)
    return out


def write_report(out_dir: Path, summary: list[dict[str, object]]) -> None:
    best = sorted(
        summary,
        key=lambda row: (
            not bool(row.get("all_pass")),
            -int(row.get("pass_count") or 0),
            float(row["max_rx_active_rmse_v"]),
            abs(float(row["mean_rx_rise50_delta_ps"])),
        ),
    )[0]
    lines = [
        "# Delay Trim Sweep",
        "",
        f"Accepted trim: `{best['trim_ps']}` ps, delay `{float(best['delay_ns']):.6g}` ns.",
        "",
        "| trim (ps) | delay (ns) | max RX RMSE (V) | max RX maxabs (V) | mean rise delta (ps) | mean fall delta (ps) | pass count |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {float(row['trim_ps']):.4g} | {float(row['delay_ns']):.6g} | "
            f"{float(row['max_rx_active_rmse_v']):.4g} | {float(row['max_rx_active_maxabs_v']):.4g} | "
            f"{float(row['mean_rx_rise50_delta_ps']):.4g} | {float(row['mean_rx_fall50_delta_ps']):.4g} | {row['pass_count']} |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sweep explicit-delay trim for a generated reduced S-parameter ngspice model.")
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--hspice-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--stop-ns", type=float, default=35.0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--trims-ps", type=float, nargs="+", default=[-100, -80, -60, -40, -20, 0, 20])
    args = parser.parse_args()

    summary: list[dict[str, object]] = []
    for trim in args.trims_ps:
        label = f"trim_{trim:+.0f}ps".replace("+", "p").replace("-", "m")
        case_dir = args.out_dir.resolve() / label
        model = case_dir / "models" / "s_equivalent_delay_reduced.sp"
        delay_ns = write_trimmed_model(args.base_model.resolve(), model, trim)
        ng_dir = case_dir / "ngspice"
        run_ngspice_audit(args.ngspice.resolve(), model, ng_dir, args.stop_ns, args.timeout)
        rows = compare(args.hspice_dir.resolve(), ng_dir, case_dir / "comparison")
        summary.append(summarize(rows, trim, delay_ns))
        print(label, summary[-1])
    write_csv(args.out_dir.resolve() / "trim_summary.csv", summary)
    write_report(args.out_dir.resolve(), summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
