"""One-command regression for the accepted PRBS7 + 50 ohm RLGC benchmark."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "final_prbs_rlgc_comparison_2026-05-11"
LOG_DIR = OUT_DIR / "regression_logs"

NGSPICE = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")
XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")

NG_REF_DIR = ROOT / "ngspice_refspice"
NG_REF_DECK = "tb_refspice_prbs7_new50ohm_batch.sp"
NG_REF_RAW = "tb_refspice_prbs7_new50ohm_batch.raw"

XY_REF_DIR = ROOT / "xyce_refspice"
XY_REF_DECK = "tb_refspice_prbs7_new50ohm_xyce.cir"
XY_REF_CSV = "tb_refspice_prbs7_new50ohm_xyce.cir.csv"


def run_logged(
    label: str,
    cmd: list[str],
    cwd: Path,
    timeout_s: float,
    log_path: Path,
) -> dict[str, object]:
    print(f"Running {label}...", flush=True)
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout_s,
            capture_output=True,
            text=True,
        )
        timed_out = False
        return_code: int | str = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = "timeout"
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

    wall_s = time.time() - started
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "COMMAND: " + " ".join(cmd) + "\n"
        f"CWD: {cwd}\n"
        f"RETURN_CODE: {return_code}\n"
        f"TIMED_OUT: {timed_out}\n"
        f"WALL_SECONDS: {wall_s:.3f}\n\n"
        "STDOUT:\n" + stdout + "\n\nSTDERR:\n" + stderr,
        encoding="utf-8",
    )
    print(f"  {label}: rc={return_code}, timeout={timed_out}, wall={wall_s:.2f}s", flush=True)
    return {
        "case": label,
        "return_code": return_code,
        "timed_out": timed_out,
        "wall_s": wall_s,
        "log": str(log_path.relative_to(ROOT)).replace("\\", "/"),
    }


def run_refspice(timeout_s: float) -> list[dict[str, object]]:
    (NG_REF_DIR / NG_REF_RAW).unlink(missing_ok=True)
    (XY_REF_DIR / XY_REF_CSV).unlink(missing_ok=True)

    return [
        run_logged(
            "ngspice_refspice",
            [str(NGSPICE), "-b", "-r", NG_REF_RAW, NG_REF_DECK],
            NG_REF_DIR,
            timeout_s,
            LOG_DIR / "ngspice_refspice.log",
        ),
        run_logged(
            "xyce_refspice",
            [str(XYCE), XY_REF_DECK],
            XY_REF_DIR,
            timeout_s,
            LOG_DIR / "xyce_refspice.log",
        ),
    ]


def run_pybis(timeout_s: float) -> dict[str, object]:
    return run_logged(
        "clean_pybis_pair",
        [sys.executable, "scripts\\run_clean_prbs_rlgc.py"],
        ROOT,
        timeout_s,
        LOG_DIR / "clean_pybis_pair.log",
    )


def build_final() -> dict[str, object]:
    return run_logged(
        "build_final_comparison",
        [sys.executable, "scripts\\build_final_prbs_rlgc_comparison.py"],
        ROOT,
        180.0,
        LOG_DIR / "build_final_comparison.log",
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def validate(
    ref_rmse_limit_mv: float,
    pybis_rmse_limit_mv: float,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    metrics = read_csv(OUT_DIR / "final_metrics_summary.csv")
    pairwise = read_csv(OUT_DIR / "pairwise_error_summary.csv")

    required = {
        "ngspice_refspice",
        "xyce_refspice",
        "ngspice_pybis",
        "xyce_pybis",
    }
    found = {row["key"] for row in metrics}
    missing = sorted(required - found)
    if missing:
        messages.append("Missing metrics for: " + ", ".join(missing))

    for row in metrics:
        key = row["key"]
        complete = str(row.get("completed_1000ns", "")).lower() == "true"
        if key in required and not complete:
            messages.append(f"{key} did not complete 1000 ns")

    for row in pairwise:
        comparison = row["comparison"]
        rmse = float(row["rmse_mV"])
        if "io_buf.sp" in comparison and rmse > ref_rmse_limit_mv:
            messages.append(
                f"{comparison} RMSE {rmse:.3f} mV exceeds {ref_rmse_limit_mv:.3f} mV"
            )
        if "pybis" in comparison and rmse > pybis_rmse_limit_mv:
            messages.append(
                f"{comparison} RMSE {rmse:.3f} mV exceeds {pybis_rmse_limit_mv:.3f} mV"
            )

    return not messages, messages


def write_regression_summary(
    command_rows: list[dict[str, object]],
    ok: bool,
    messages: list[str],
) -> None:
    summary_csv = OUT_DIR / "regression_summary.csv"
    fields = ["case", "return_code", "timed_out", "wall_s", "log"]
    with summary_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(command_rows)

    metrics = read_csv(OUT_DIR / "final_metrics_summary.csv")
    pairwise = read_csv(OUT_DIR / "pairwise_error_summary.csv")

    lines = [
        "# Accepted PRBS/RLGC Regression Summary",
        "",
        f"Status: {'PASS' if ok else 'FAIL'}",
        "",
        "## Simulator Commands",
        "",
    ]
    for row in command_rows:
        lines.append(
            f"- {row['case']}: rc={row['return_code']}, "
            f"timeout={row['timed_out']}, wall_s={float(row['wall_s']):.2f}"
        )
    lines.extend(["", "## Pairwise Error", ""])
    for row in pairwise:
        lines.append(
            f"- {row['comparison']}: RMSE={float(row['rmse_mV']):.3f} mV, "
            f"max={float(row['max_abs_error_mV']):.3f} mV"
        )
    lines.extend(["", "## Completion", ""])
    for row in metrics:
        lines.append(
            f"- {row['label']}: complete={row['completed_1000ns']}, "
            f"t_end={float(row['t_end_ns']):.3f} ns"
        )
    if messages:
        lines.extend(["", "## Validation Messages", ""])
        lines.extend(f"- {message}" for message in messages)

    (OUT_DIR / "REGRESSION_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-sims",
        action="store_true",
        help="Do not rerun SPICE; rebuild plots/metrics from existing waveforms.",
    )
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--ref-rmse-limit-mv", type=float, default=10.0)
    parser.add_argument("--pybis-rmse-limit-mv", type=float, default=60.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    command_rows: list[dict[str, object]] = []
    if not args.skip_sims:
        command_rows.extend(run_refspice(args.timeout))
        command_rows.append(run_pybis(args.timeout))
    command_rows.append(build_final())

    command_ok = all(
        str(row["return_code"]) == "0" and str(row["timed_out"]).lower() == "false"
        for row in command_rows
    )
    metrics_ok, messages = validate(args.ref_rmse_limit_mv, args.pybis_rmse_limit_mv)
    ok = command_ok and metrics_ok
    if not command_ok:
        messages.append("One or more simulator/build commands failed or timed out")

    write_regression_summary(command_rows, ok, messages)
    print(f"Regression status: {'PASS' if ok else 'FAIL'}", flush=True)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}\\REGRESSION_SUMMARY.md", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
