from __future__ import annotations

import csv
import math
import subprocess
from pathlib import Path

import run_edge_family_stress_crossflow as base

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "ngspice_kukd_ab_context38_2026-05-11"


def write_baseline_from_git(dest: Path) -> None:
    spec = "3e0bf44:ngspice_pybis/driver_OutputInput_Typical.sub"
    proc = subprocess.run(
        ["git", "show", spec],
        cwd=ROOT,
        capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(f"failed to read baseline model from git: {proc.stderr.decode(errors='ignore')}")
    dest.write_bytes(proc.stdout)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_variant(case: base.StressCase, variant_key: str, model_file: Path) -> dict[str, object]:
    flow = base.Flow(f"ngspice_pybis_{variant_key}", "ngspice", f"pybis {variant_key}", "ngspice", "#ff7f0e")
    run_dir = OUT_DIR / "runs" / variant_key
    run_dir.mkdir(parents=True, exist_ok=True)

    deck_text, raw_name = base.make_deck(case, base.Flow("ngspice_pybis", "ngspice", "pybis", "ngspice", "#ff7f0e"), run_dir)
    default_inc = base.rel_include(ROOT / "ngspice_pybis" / "driver_OutputInput_Typical.sub", run_dir)
    model_inc = base.rel_include(model_file, run_dir)
    deck_text = deck_text.replace(default_inc, model_inc)

    deck = run_dir / f"{case.key}_{variant_key}.sp"
    raw = run_dir / raw_name.replace("ngspice_pybis", f"ngspice_pybis_{variant_key}")
    log = run_dir / f"{case.key}_{variant_key}.log"

    deck.write_text(deck_text, encoding="ascii")
    raw.unlink(missing_ok=True)

    cmd = [str(base.NGSPICE), "-b", "-r", raw.name, deck.name]
    proc = subprocess.run(cmd, cwd=run_dir, capture_output=True, text=True)
    log.write_text(
        "COMMAND: " + " ".join(cmd) + "\n"
        f"RETURN_CODE: {proc.returncode}\n\n"
        "STDOUT:\n" + (proc.stdout or "") + "\n\nSTDERR:\n" + (proc.stderr or ""),
        encoding="utf-8",
    )

    row: dict[str, object] = {
        "variant": variant_key,
        "model": str(model_file.relative_to(ROOT)).replace("\\", "/"),
        "return_code": proc.returncode,
        "output_exists": raw.exists(),
        "raw": str(raw.relative_to(ROOT)).replace("\\", "/"),
        "log": str(log.relative_to(ROOT)).replace("\\", "/"),
    }

    if proc.returncode == 0 and raw.exists():
        events, summary, _ = base.analyze_output(case, flow, raw)
        write_csv(OUT_DIR / f"{variant_key}_events.csv", events)
        write_csv(OUT_DIR / f"{variant_key}_summary.csv", summary)

        rise_10to11 = [
            e for e in events if e.get("direction") == "rise" and e.get("context") == "10->11"
        ]
        delays = [float(e["output_50_delay_ps"]) for e in rise_10to11 if math.isfinite(float(e["output_50_delay_ps"]))]
        row["rise_10to11_count"] = len(delays)
        row["rise_10to11_min_ps"] = min(delays) if delays else float("nan")
        row["rise_10to11_max_ps"] = max(delays) if delays else float("nan")
        row["rise_10to11_values_ps"] = ";".join(f"{v:.3f}" for v in delays)
    return row


def main() -> int:
    base.configure_suite(["--suite", "coarse10_context"])
    case = base.CASES[0]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    baseline_model = OUT_DIR / "driver_OutputInput_Typical_pre_kukd_3e0bf44.sub"
    write_baseline_from_git(baseline_model)
    current_model = ROOT / "ngspice_pybis" / "driver_OutputInput_Typical.sub"

    rows = [
        run_variant(case, "baseline_pre_kukd", baseline_model),
        run_variant(case, "current_kukd", current_model),
    ]
    write_csv(OUT_DIR / "ab_run_summary.csv", rows)
    print("Wrote", OUT_DIR)
    for row in rows:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
