"""Sweep Xyce pybis model variants on the compact stressed context case."""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_edge_family_stress_crossflow as base  # noqa: E402
from eye_diagram import load_waveform, sanitize_waveform  # noqa: E402

XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")
OUT_DIR = ROOT / "results" / "xyce_pybis_context38_variant_sweep_2026-05-11"
CASE = base.COARSE_CASES[0]


@dataclass(frozen=True)
class Variant:
    key: str
    model_file: str
    note: str


VARIANTS = [
    Variant(
        "edge15_flat4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub",
        "current accepted PRBS/RLGC continuation setup",
    ),
    Variant(
        "tanh10",
        "driver_OutputInput_Typical_xyce_relaxed10.sub",
        "global tanh10 smoothing",
    ),
    Variant(
        "tanh15",
        "driver_OutputInput_Typical_xyce_relaxed15.sub",
        "global tanh15 smoothing",
    ),
    Variant(
        "tanh30",
        "driver_OutputInput_Typical_xyce_relaxed30.sub",
        "global tanh30 smoothing",
    ),
    Variant(
        "tailflat4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_tailflat4p2.sub",
        "tail-table flattening only",
    ),
    Variant(
        "edge20_flat4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_edge20_tailflat4p2.sub",
        "edge/latch tanh20 plus flat tail",
    ),
    Variant(
        "edge30_flat4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_edge30_tailflat4p2.sub",
        "edge/latch tanh30 plus flat tail",
    ),
    Variant(
        "edge50_flat4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_edge50_tailflat4p2.sub",
        "less-smoothed edge controls plus flat tail",
    ),
    Variant(
        "edge55_flat4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_edge55_tailflat4p2.sub",
        "edge/latch tanh55 plus flat tail",
    ),
    Variant(
        "edge60_flat4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_edge60_tailflat4p2.sub",
        "edge/latch tanh60 plus flat tail",
    ),
    Variant(
        "edge75_flat4p2",
        "driver_OutputInput_Typical_xyce_relaxed92_edge75_tailflat4p2.sub",
        "edge/latch tanh75 plus flat tail",
    ),
]


def reset_out_dir() -> None:
    resolved = OUT_DIR.resolve()
    expected_parent = (ROOT / "results").resolve()
    if resolved.parent != expected_parent:
        raise RuntimeError(f"Refusing to remove unexpected output dir: {resolved}")
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "plots").mkdir(parents=True, exist_ok=True)


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


def output_progress(path: Path) -> tuple[int, float, float, float]:
    if not path.exists():
        return 0, float("nan"), float("nan"), float("nan")
    try:
        data = load_waveform(path, fmt="xyce")
        time_vec, _ = sanitize_waveform(data["time"], data["time"])
        _, v_out = sanitize_waveform(data["time"], data["v(n10b)"])
        return (
            len(time_vec),
            float(time_vec[-1] * 1e9),
            float(np.min(v_out)),
            float(np.max(v_out)),
        )
    except Exception:
        return 0, float("nan"), float("nan"), float("nan")


def run_variant(variant: Variant, timeout_s: float) -> dict[str, object]:
    run_dir = OUT_DIR / "runs" / variant.key
    run_dir.mkdir(parents=True, exist_ok=True)
    template_flow = base.Flow("xyce_pybis", "Xyce", variant.note, "xyce", "#d62728")
    deck_text, _ = base.make_deck(CASE, template_flow, run_dir)
    deck_text = deck_text.replace(
        "driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub",
        variant.model_file,
    )
    deck = run_dir / f"{CASE.key}_{variant.key}.cir"
    deck.write_text(deck_text, encoding="ascii")
    output = run_dir / f"{deck.name}.csv"
    output.unlink(missing_ok=True)
    log = run_dir / f"{CASE.key}_{variant.key}.log"

    started = time.time()
    try:
        proc = subprocess.run(
            [str(XYCE), deck.name],
            cwd=run_dir,
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

    log.write_text(
        "COMMAND: " + str(XYCE) + " " + deck.name + "\n"
        f"VARIANT: {variant.key}\nMODEL: {variant.model_file}\n"
        f"RETURN_CODE: {return_code}\nTIMED_OUT: {timed_out}\n"
        f"WALL_SECONDS: {wall_s:.3f}\n\n"
        "STDOUT:\n" + stdout + "\n\nSTDERR:\n" + stderr,
        encoding="utf-8",
    )

    points, t_end_ns, v_min, v_max = output_progress(output)
    row: dict[str, object] = {
        "variant": variant.key,
        "model_file": variant.model_file,
        "note": variant.note,
        "return_code": return_code,
        "timed_out": timed_out,
        "wall_s": wall_s,
        "points": points,
        "t_end_ns": t_end_ns,
        "completed": t_end_ns >= CASE.stop_s * 1e9 - 1e-3,
        "v_min": v_min,
        "v_max": v_max,
        "deck": str(deck.relative_to(ROOT)).replace("\\", "/"),
        "output": str(output.relative_to(ROOT)).replace("\\", "/"),
        "log": str(log.relative_to(ROOT)).replace("\\", "/"),
    }

    if row["return_code"] == 0 and row["completed"]:
        flow = base.Flow(f"xyce_pybis_{variant.key}", "Xyce", variant.note, "xyce", "#d62728")
        try:
            events, summary, _ = base.analyze_output(CASE, flow, output)
            write_csv(OUT_DIR / f"{variant.key}_events.csv", events)
            write_csv(OUT_DIR / f"{variant.key}_summary.csv", summary)
        except Exception as exc:
            row["analysis_error"] = str(exc)
    return row


def write_readme(rows: list[dict[str, object]]) -> None:
    lines = [
        "# Xyce pybis Context38 Variant Sweep",
        "",
        "Same compact stressed context stimulus as the coarse cross-flow test:",
        "",
        "- 2 ns UI",
        "- 30 cm total RLGC delay/loss represented as 10 coarse sections",
        "- R/G loss x5",
        "- context38 deterministic bit pattern covering all rise/fall contexts",
        "",
        "| Variant | Return | Timed out | t end | Completed | Wall s | Note |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {variant} | {return_code} | {timed_out} | {t_end_ns:.2f} ns | "
            "{completed} | {wall_s:.2f} | {note} |".format(**row)
        )
    lines.extend(
        [
            "",
            "Passing variants also get `*_summary.csv`, `*_events.csv`, and plots under `plots/`.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    if not XYCE.exists():
        raise FileNotFoundError(XYCE)
    base.configure_suite(["--suite", "coarse10_context"])
    base.OUT_DIR = OUT_DIR
    reset_out_dir()
    rows = []
    for variant in VARIANTS:
        print(f"Running {variant.key}", flush=True)
        rows.append(run_variant(variant, timeout_s=60.0))
    write_csv(OUT_DIR / "xyce_pybis_context38_variant_sweep.csv", rows)
    write_readme(rows)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
