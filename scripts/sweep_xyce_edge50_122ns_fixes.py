"""Targeted Xyce pybis fix sweep for the edge50 PRBS62 122 ns stall.

This script reuses the focused PRBS62/loss5 deck from
``probe_xyce_edge50_122ns_failure.py`` and applies small, isolated changes:

- solver/time-integration options only
- transient setup only
- subckt delay parameter only
- more-smoothed model substitutions for comparison

The purpose is to verify whether the edge50 stall is solved by simulator setup
or by relaxing the pybis control model itself.
"""

from __future__ import annotations

import csv
import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")
BASE_DECK = (
    ROOT
    / "results"
    / "xyce_edge50_122ns_failure_probe_2026-05-12"
    / "runs"
    / "prbs62_loss5_fail"
    / "prbs62_loss5_fail.cir"
)
OUT_DIR = ROOT / "results" / "xyce_edge50_122ns_fix_sweep_2026-05-12"

BASE_TIMEINT = (
    ".options timeint method=trap maxord=1 erroption=1 delmax=20p "
    "nlmin=3 nlmax=8 timestepsreversal=1"
)
BASE_INCLUDE = (
    ".include '../../../../xyce_pybis/"
    "driver_OutputInput_Typical_xyce_relaxed92_edge50_tailflat4p2.sub'"
)
BASE_XDRV = "XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical"
BASE_TRAN = ".tran 1.000000000e-11 1.240000000e-07 uic"


@dataclass(frozen=True)
class Variant:
    key: str
    note: str
    replacements: tuple[tuple[str, str], ...]
    timeout_s: float = 90.0


VARIANTS = [
    Variant(
        "trap_nl50",
        "isolation: trap order 1, nlmax 50, timestep reversal kept enabled",
        (
            (
                BASE_TIMEINT,
                ".options timeint method=trap maxord=1 erroption=1 delmax=20p "
                "nlmin=3 nlmax=50 timestepsreversal=1",
            ),
        ),
    ),
    Variant(
        "gear1_nl8",
        "minimal solver fix: Gear order 1 with original nlmax 8",
        (
            (
                BASE_TIMEINT,
                ".options timeint method=gear maxord=1 erroption=1 delmax=20p "
                "nlmin=3 nlmax=8 timestepsreversal=1",
            ),
        ),
    ),
    Variant(
        "gear2_nl8",
        "isolation: Gear order 2 but original nlmax 8",
        (
            (
                BASE_TIMEINT,
                ".options timeint method=gear maxord=2 erroption=1 delmax=20p "
                "nlmin=3 nlmax=8 timestepsreversal=1",
            ),
        ),
    ),
    Variant(
        "gear1_nl50",
        "isolation: Gear order 1 and nlmax 50",
        (
            (
                BASE_TIMEINT,
                ".options timeint method=gear maxord=1 erroption=1 delmax=20p "
                "nlmin=3 nlmax=50 timestepsreversal=1",
            ),
        ),
    ),
    Variant(
        "gear2_nl50",
        "solver only: Gear order 2 and more nonlinear iterations",
        (
            (
                BASE_TIMEINT,
                ".options timeint method=gear maxord=2 erroption=1 delmax=20p "
                "nlmin=3 nlmax=50 timestepsreversal=1",
            ),
        ),
    ),
    Variant(
        "trap_nl50_no_reverse",
        "solver only: keep trap, allow more nonlinear iterations, disable timestep reversal",
        (
            (
                BASE_TIMEINT,
                ".options timeint method=trap maxord=1 erroption=1 delmax=20p "
                "nlmin=3 nlmax=50 timestepsreversal=0",
            ),
        ),
    ),
    Variant(
        "no_uic",
        "setup only: let Xyce calculate the operating point before transient",
        ((BASE_TRAN, ".tran 1.000000000e-11 1.240000000e-07"),),
    ),
    Variant(
        "edge_delay20p",
        "model parameter only: increase internal edge-detect T-line delay from 10 ps to 20 ps",
        ((BASE_XDRV, BASE_XDRV + " params: edge_delay=20p"),),
    ),
    Variant(
        "edge15_model",
        "model comparison: existing edge15_flat4p2 smoothing",
        (
            (
                BASE_INCLUDE,
                ".include '../../../../xyce_pybis/"
                "driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub'",
            ),
        ),
    ),
    Variant(
        "tanh15_model",
        "model comparison: existing broad tanh15 smoothing",
        (
            (
                BASE_INCLUDE,
                ".include '../../../../xyce_pybis/driver_OutputInput_Typical_xyce_relaxed15.sub'",
            ),
        ),
    ),
]


def write_variant_deck(variant: Variant) -> Path:
    text = BASE_DECK.read_text(encoding="ascii")
    for old, new in variant.replacements:
        if old not in text:
            raise RuntimeError(f"{variant.key}: pattern not found: {old}")
        text = text.replace(old, new, 1)

    run_dir = OUT_DIR / "runs" / variant.key
    run_dir.mkdir(parents=True, exist_ok=True)
    deck = run_dir / f"{variant.key}.cir"
    deck.write_text(
        "* Xyce edge50 122 ns fix sweep\n"
        f"* Variant: {variant.key}\n"
        f"* Note: {variant.note}\n\n"
        + text,
        encoding="ascii",
    )
    return deck


def run_xyce(deck: Path, timeout_s: float) -> dict[str, object]:
    output = Path(str(deck) + ".csv")
    log = deck.with_suffix(".log")
    if output.exists():
        output.unlink()

    started = time.time()
    timed_out = False
    try:
        proc = subprocess.run(
            [str(XYCE), deck.name],
            cwd=deck.parent,
            text=True,
            capture_output=True,
            timeout=timeout_s,
        )
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
        f"RETURN_CODE: {return_code}\nTIMED_OUT: {timed_out}\n"
        f"WALL_S: {wall_s:.3f}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}\n",
        encoding="utf-8",
    )
    return {
        "return_code": return_code,
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(deck.relative_to(ROOT)),
        "output": str(output.relative_to(ROOT)),
        "log": str(log.relative_to(ROOT)),
        "output_exists": output.exists(),
    }


def load_xyce_csv(path: Path) -> tuple[list[str], np.ndarray]:
    if not path.exists():
        return [], np.empty((0, 0))
    with path.open(newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return [], np.empty((0, 0))
        rows = []
        for row in reader:
            try:
                rows.append([float(x) for x in row])
            except ValueError:
                continue
    if not rows:
        return header, np.empty((0, len(header)))
    return [h.lower() for h in header], np.asarray(rows, dtype=float)


def value_at(header: list[str], arr: np.ndarray, name: str) -> float:
    if arr.size == 0:
        return math.nan
    try:
        idx = header.index(name.lower())
    except ValueError:
        return math.nan
    return float(arr[-1, idx])


def summarize_waveform(row: dict[str, object], stop_ns: float = 124.0) -> None:
    output = ROOT / str(row["output"])
    header, arr = load_xyce_csv(output)
    row["points"] = int(arr.shape[0])
    if arr.size == 0:
        row["t_end_ns"] = math.nan
        row["completed"] = False
        return

    time_col = arr[:, 0]
    row["t_end_ns"] = float(time_col[-1] * 1e9)
    row["completed"] = bool(row["t_end_ns"] >= stop_ns - 1e-6)
    row["last_pad_v"] = value_at(header, arr, "v(pad)")
    row["last_n10b_v"] = value_at(header, arr, "v(n10b)")
    row["last_nx_ns"] = value_at(header, arr, "v(xdrv:nx)")
    row["last_ku"] = value_at(header, arr, "v(xdrv:ku)")
    row["last_kd"] = value_at(header, arr, "v(xdrv:kd)")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_readme(rows: list[dict[str, object]]) -> None:
    lines = [
        "# Xyce Edge50 122 ns Fix Sweep",
        "",
        "Targeted sweep using the same PRBS62 / 2 ns UI / coarse 30 cm RLGC / loss x5 deck",
        "that stalls with `edge50_flat4p2` at about 122.26 ns.",
        "",
        "| Variant | Completed | End ns | Return | Timeout | Wall s | Last NX ns | Last Ku | Last Kd | Note |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        fmt_row = dict(row)
        for key in ("t_end_ns", "wall_s", "last_nx_ns", "last_ku", "last_kd"):
            value = fmt_row.get(key, math.nan)
            fmt_row[key] = float(value) if value != "" else math.nan
        lines.append(
            "| {variant} | {completed} | {t_end_ns:.3f} | {return_code} | {timed_out} | "
            "{wall_s:.2f} | {last_nx_ns:.3f} | {last_ku:.6g} | {last_kd:.6g} | {note} |".format(
                **fmt_row
            )
        )
    lines.extend(
        [
            "",
            "A variant that still ends near 122.26 ns is reproducing the same stall.",
            "A variant that reaches 124 ns completed the focused PRBS62 case.",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not XYCE.exists():
        raise FileNotFoundError(XYCE)
    if not BASE_DECK.exists():
        raise FileNotFoundError(BASE_DECK)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        print(f"Running {variant.key}", flush=True)
        deck = write_variant_deck(variant)
        row = {"variant": variant.key, "note": variant.note}
        row.update(run_xyce(deck, variant.timeout_s))
        summarize_waveform(row)
        rows.append(row)

    write_csv(OUT_DIR / "fix_sweep_summary.csv", rows)
    write_readme(rows)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
