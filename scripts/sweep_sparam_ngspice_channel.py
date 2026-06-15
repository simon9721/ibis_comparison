from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eye_diagram import parse_ngspice_raw  # noqa: E402


DEFAULT_NGSPICE = Path(
    r"\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin\ngspice_con.exe"
)
CASE_DIR = ROOT / "hspice" / "sparam_ngspice" / "channel_sweep"
DEFAULT_MODEL = ROOT / "hspice" / "sparam_ngspice" / "Clarity_example.sp"


@dataclass(frozen=True)
class SweepCase:
    name: str
    rsrc_ohm: float | None
    edge_ps: float
    amplitude_v: float
    stop_ns: float = 12.0


def fmt(value: float) -> str:
    return f"{value:.12g}"


def include_path(from_dir: Path, target: Path) -> str:
    return os.path.relpath(target.resolve(), from_dir.resolve()).replace("\\", "/")


def write_deck(case: SweepCase, case_dir: Path, model_spice: Path) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    deck = case_dir / f"{case.name}.sp"
    edge = case.edge_ps * 1e-12
    stop = case.stop_ns * 1e-9
    amp = case.amplitude_v

    if case.rsrc_ohm is None:
        source = [
            f"Vin  pad  0  PWL(0 0 1n 0 {fmt(1e-9 + edge)} {fmt(amp)} 9n {fmt(amp)} {fmt(9e-9 + edge)} 0)",
        ]
        save = ".save V(pad) V(ntst)"
    else:
        source = [
            f"Vin   src  0    PWL(0 0 1n 0 {fmt(1e-9 + edge)} {fmt(amp)} 9n {fmt(amp)} {fmt(9e-9 + edge)} 0)",
            f"Rsrc  src  pad  {fmt(case.rsrc_ohm)}",
        ]
        save = ".save V(src) V(pad) V(ntst)"

    text = "\n".join(
        [
            f"* Channel-only ngspice sweep case: {case.name}",
            ".temp 27",
            ".options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12",
            "",
            *source,
            "",
            f".include '{include_path(case_dir, model_spice)}'",
            "Xchannel  pad  ntst  s_equivalent",
            "Rterm  ntst  0  50",
            "",
            save,
            f".tran 10p {fmt(stop)}",
            ".end",
            "",
        ]
    )
    deck.write_text(text, encoding="ascii")
    return deck


def run_case(ngspice: Path, case: SweepCase, case_dir: Path, model_spice: Path) -> dict[str, object]:
    deck = write_deck(case, case_dir, model_spice)
    raw = deck.with_suffix(".raw")
    log = deck.with_suffix(".log")
    completed = subprocess.run(
        [str(ngspice), "-b", "-o", log.name, "-r", raw.name, deck.name],
        cwd=case_dir,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    row: dict[str, object] = {
        "case": case.name,
        "rsrc_ohm": "ideal" if case.rsrc_ohm is None else case.rsrc_ohm,
        "edge_ps": case.edge_ps,
        "amplitude_v": case.amplitude_v,
        "return_code": completed.returncode,
        "deck": str(deck.relative_to(ROOT)).replace("\\", "/"),
        "raw": str(raw.relative_to(ROOT)).replace("\\", "/"),
        "log": str(log.relative_to(ROOT)).replace("\\", "/"),
    }
    try:
        data = parse_ngspice_raw(raw)
        time = data["time"]
        row["points"] = len(time)
        row["stop_ns"] = float(time[-1] * 1e9)
        for signal in ("v(pad)", "v(ntst)"):
            values = data[signal]
            row[f"{signal}_min_v"] = float(np.nanmin(values))
            row[f"{signal}_max_v"] = float(np.nanmax(values))
            row[f"{signal}_finite"] = bool(np.all(np.isfinite(values)))
        row["finite_reasonable"] = (
            row["return_code"] == 0
            and float(row["stop_ns"]) >= case.stop_ns * 0.999
            and abs(float(row["v(pad)_min_v"])) < 10
            and abs(float(row["v(pad)_max_v"])) < 10
            and abs(float(row["v(ntst)_min_v"])) < 10
            and abs(float(row["v(ntst)_max_v"])) < 10
        )
    except Exception as exc:
        row["parse_error"] = str(exc)
    if log.exists():
        text = log.read_text(encoding="utf-8", errors="replace")
        trouble = ""
        for line in text.splitlines():
            if "Timestep too small" in line or "trouble with node" in line or "Error" in line:
                trouble = line
        row["last_trouble"] = trouble
    return row


def cases() -> list[SweepCase]:
    selected: list[SweepCase] = []
    for rsrc in [None, 0.1, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0]:
        label = "ideal" if rsrc is None else f"r{int(rsrc) if rsrc.is_integer() else str(rsrc).replace('.', 'p')}"
        selected.append(SweepCase(f"amp1p5_edge5_{label}", rsrc, 5.0, 1.5))
    for edge in [50.0, 500.0]:
        selected.append(SweepCase(f"amp1p5_edge{int(edge)}_ideal", None, edge, 1.5))
        selected.append(SweepCase(f"amp1p5_edge{int(edge)}_r50", 50.0, edge, 1.5))
    for amp in [0.05, 0.1, 0.5]:
        selected.append(SweepCase(f"amp{str(amp).replace('.', 'p')}_edge5_ideal", None, 5.0, amp))
        selected.append(SweepCase(f"amp{str(amp).replace('.', 'p')}_edge5_r50", 50.0, 5.0, amp))
    return selected


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sweep ngspice channel-only stability for Clarity_example.sp.")
    parser.add_argument("--ngspice", type=Path, default=Path(os.environ.get("NGSPICE_EXE", DEFAULT_NGSPICE)))
    parser.add_argument("--case-dir", type=Path, default=CASE_DIR)
    parser.add_argument("--model-spice", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()

    case_dir = args.case_dir.resolve()
    model_spice = args.model_spice.resolve()
    rows = [run_case(args.ngspice, case, case_dir, model_spice) for case in cases()]
    write_csv(case_dir / "summary.csv", rows)
    for row in rows:
        print(
            f"{row['case']}: rc={row['return_code']} stop={row.get('stop_ns', '')} "
            f"reasonable={row.get('finite_reasonable', '')} {row.get('last_trouble', '')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
