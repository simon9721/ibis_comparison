"""Validate promising edge50 fixes on the PRBS80 coarse RLGC stress deck."""

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
    / "edge_family_stress_crossflow_coarse10_80b_edge50_2026-05-11"
    / "runs"
    / "ui2_len30cm_loss5_coarse10"
    / "xyce_pybis"
    / "ui2_len30cm_loss5_coarse10_xyce_pybis.cir"
)
OUT_DIR = ROOT / "results" / "xyce_edge50_prbs80_fix_validation_2026-05-12"

BASE_TIMEINT = (
    ".options timeint method=trap maxord=1 erroption=1 delmax=20p "
    "nlmin=3 nlmax=8 timestepsreversal=1"
)
GEAR2_TIMEINT = (
    ".options timeint method=gear maxord=2 erroption=1 delmax=20p "
    "nlmin=3 nlmax=50 timestepsreversal=1"
)
BASE_XDRV = "XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical"
EDGE_DELAY20_XDRV = BASE_XDRV + " params: edge_delay=20p"


@dataclass(frozen=True)
class Variant:
    key: str
    note: str
    replacements: tuple[tuple[str, str], ...]
    timeout_s: float = 180.0


VARIANTS = [
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
        "gear2_nl50",
        "solver-only fix: Gear order 2, nlmax 50",
        ((BASE_TIMEINT, GEAR2_TIMEINT),),
    ),
    Variant(
        "edge_delay20p",
        "model-parameter fix: internal edge delay 20 ps",
        ((BASE_XDRV, EDGE_DELAY20_XDRV),),
    ),
    Variant(
        "gear2_edge_delay20p",
        "combined solver plus model-parameter fix",
        ((BASE_TIMEINT, GEAR2_TIMEINT), (BASE_XDRV, EDGE_DELAY20_XDRV)),
    ),
]


def write_deck(variant: Variant) -> Path:
    text = BASE_DECK.read_text(encoding="ascii")
    text = text.replace("../../../../../xyce_pybis/", "../../../../xyce_pybis/")
    for old, new in variant.replacements:
        if old not in text:
            raise RuntimeError(f"{variant.key}: pattern not found: {old}")
        text = text.replace(old, new, 1)

    run_dir = OUT_DIR / "runs" / variant.key
    run_dir.mkdir(parents=True, exist_ok=True)
    deck = run_dir / f"{variant.key}.cir"
    deck.write_text(
        "* Xyce edge50 PRBS80 fix validation\n"
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
        return [h.lower() for h in header], np.empty((0, len(header)))
    return [h.lower() for h in header], np.asarray(rows, dtype=float)


def value_at(header: list[str], arr: np.ndarray, name: str) -> float:
    if arr.size == 0:
        return math.nan
    try:
        idx = header.index(name.lower())
    except ValueError:
        return math.nan
    return float(arr[-1, idx])


def summarize(row: dict[str, object], stop_ns: float = 160.0) -> None:
    header, arr = load_xyce_csv(ROOT / str(row["output"]))
    row["points"] = int(arr.shape[0])
    if arr.size == 0:
        row["t_end_ns"] = math.nan
        row["completed"] = False
        return
    row["t_end_ns"] = float(arr[-1, 0] * 1e9)
    row["completed"] = bool(row["t_end_ns"] >= stop_ns - 1e-6)
    row["last_pad_v"] = value_at(header, arr, "v(pad)")
    row["last_n10b_v"] = value_at(header, arr, "v(n10b)")
    row["last_nx_ns"] = value_at(header, arr, "v(xdrv:nx)")
    row["last_ku"] = value_at(header, arr, "v(xdrv:ku)")
    row["last_kd"] = value_at(header, arr, "v(xdrv:kd)")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
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
        "# Xyce Edge50 PRBS80 Fix Validation",
        "",
        "Validation of promising PRBS62 fixes on the original 80-bit coarse RLGC stress deck.",
        "",
        "| Variant | Completed | End ns | Return | Timeout | Wall s | Last NX ns | Note |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        fmt = dict(row)
        for key in ("t_end_ns", "wall_s", "last_nx_ns"):
            value = fmt.get(key, math.nan)
            fmt[key] = float(value) if value != "" else math.nan
        lines.append(
            "| {variant} | {completed} | {t_end_ns:.3f} | {return_code} | {timed_out} | "
            "{wall_s:.2f} | {last_nx_ns:.3f} | {note} |".format(**fmt)
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "Use `.options timeint method=gear maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1` for Xyce pybis PRBS/RLGC stress decks. This is a simulator setup fix, not a pybis model edit.",
            "",
            "## Key Files",
            "",
            "- `plots/prbs80_gear_fix_122ns_window.png`: baseline trap timeout vs Gear pass around the original 122 ns stall.",
            "- `plots/prbs80_gear_fix_full_rx_overlay.png`: full receiver waveform through 160 ns.",
            "- `gear_fix_difference_metrics.csv`: pre-timeout baseline-vs-Gear and Gear1-vs-Gear2 difference metrics.",
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
        deck = write_deck(variant)
        row = {"variant": variant.key, "note": variant.note}
        row.update(run_xyce(deck, variant.timeout_s))
        summarize(row)
        rows.append(row)

    write_csv(OUT_DIR / "prbs80_fix_validation_summary.csv", rows)
    write_readme(rows)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
