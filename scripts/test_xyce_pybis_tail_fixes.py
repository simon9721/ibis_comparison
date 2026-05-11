from __future__ import annotations

import argparse
import csv
import re
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
XYCE_DIR = ROOT / "xyce_pybis"
NGSPICE_DIR = ROOT / "ngspice_pybis"
OUT_DIR = ROOT / "plots" / "xyce_pybis"

XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")

BASE_MODEL = "driver_OutputInput_Typical_xyce_relaxed92.sub"
MAX_NX = "5.9639999999999995"
TABLE_ARG = f"table(min(max(V(NX), 0), {MAX_NX}),"

TIMEINT = ".options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1"
OUTPUT = ".options output initial_interval=10p"


@dataclass(frozen=True)
class Candidate:
    name: str
    title: str
    mode: str
    include_file: str
    cap: float | None = None
    softness: float | None = None
    control_factor: int | None = None
    control_scope: str = ""
    tail_mode: str = ""
    edge_factor: int | None = None
    selector_factor: int | None = None
    line_factor: int | None = None
    control_lines: tuple[int, ...] = ()


@dataclass(frozen=True)
class Bench:
    name: str
    title: str
    kind: str
    stop: str
    target_ns: float
    stimulus: str = ""
    ng_ref: str = ""
    ref_node: str = ""
    xyce_node: str = ""
    timeout_s: float = 60.0


CANDIDATES = [
    Candidate("tanh92", "baseline tanh92", "base", BASE_MODEL),
    Candidate("tanh50", "existing all-control tanh50", "base", "driver_OutputInput_Typical_xyce_relaxed50.sub"),
    Candidate("tanh15", "existing all-control tanh15", "base", "driver_OutputInput_Typical_xyce_relaxed15.sub"),
    Candidate(
        "hard4p1",
        "KUR/KDR arg hard cap 4.1 ns",
        "hard",
        "driver_OutputInput_Typical_xyce_relaxed92_tailhard4p1.sub",
        cap=4.1,
    ),
    Candidate(
        "hard4p2",
        "KUR/KDR arg hard cap 4.2 ns",
        "hard",
        "driver_OutputInput_Typical_xyce_relaxed92_tailhard4p2.sub",
        cap=4.2,
    ),
    Candidate(
        "flat4p1",
        "KUR/KDR table flat tail after 4.1 ns",
        "flat",
        "driver_OutputInput_Typical_xyce_relaxed92_tailflat4p1.sub",
        cap=4.1,
    ),
    Candidate(
        "flat4p2",
        "KUR/KDR table flat tail after 4.2 ns",
        "flat",
        "driver_OutputInput_Typical_xyce_relaxed92_tailflat4p2.sub",
        cap=4.2,
    ),
    Candidate(
        "soft4p2k5",
        "KUR/KDR arg soft cap 4.2 ns, k=5",
        "soft",
        "driver_OutputInput_Typical_xyce_relaxed92_tailsoft4p2k5.sub",
        cap=4.2,
        softness=5.0,
    ),
    Candidate(
        "soft4p2k10",
        "KUR/KDR arg soft cap 4.2 ns, k=10",
        "soft",
        "driver_OutputInput_Typical_xyce_relaxed92_tailsoft4p2k10.sub",
        cap=4.2,
        softness=10.0,
    ),
    Candidate(
        "soft4p2k20",
        "KUR/KDR arg soft cap 4.2 ns, k=20",
        "soft",
        "driver_OutputInput_Typical_xyce_relaxed92_tailsoft4p2k20.sub",
        cap=4.2,
        softness=20.0,
    ),
    Candidate(
        "edge75_flat4p2",
        "edge/latch tanh75 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge75_tailflat4p2.sub",
        cap=4.2,
        control_factor=75,
        control_scope="edge",
        tail_mode="flat",
    ),
    Candidate(
        "edge60_flat4p2",
        "edge/latch tanh60 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge60_tailflat4p2.sub",
        cap=4.2,
        control_factor=60,
        control_scope="edge",
        tail_mode="flat",
    ),
    Candidate(
        "edge55_flat4p2",
        "edge/latch tanh55 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge55_tailflat4p2.sub",
        cap=4.2,
        control_factor=55,
        control_scope="edge",
        tail_mode="flat",
    ),
    Candidate(
        "edge52_flat4p2",
        "edge/latch tanh52 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge52_tailflat4p2.sub",
        cap=4.2,
        control_factor=52,
        control_scope="edge",
        tail_mode="flat",
    ),
    Candidate(
        "b18_15_flat4p2",
        "B18 NX gate tanh15 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_b18_15_tailflat4p2.sub",
        cap=4.2,
        tail_mode="flat",
        line_factor=15,
        control_lines=(18,),
    ),
    Candidate(
        "b17b18_15_flat4p2",
        "B17/B18 latch+NX tanh15 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_b17b18_15_tailflat4p2.sub",
        cap=4.2,
        tail_mode="flat",
        line_factor=15,
        control_lines=(17, 18),
    ),
    Candidate(
        "b15b17b18_15_flat4p2",
        "B15/B17/B18 edge-latch tanh15 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_b15b17b18_15_tailflat4p2.sub",
        cap=4.2,
        tail_mode="flat",
        line_factor=15,
        control_lines=(15, 17, 18),
    ),
    Candidate(
        "b10b11_15_flat4p2",
        "B10/B11 threshold tanh15 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_b10b11_15_tailflat4p2.sub",
        cap=4.2,
        tail_mode="flat",
        line_factor=15,
        control_lines=(10, 11),
    ),
    Candidate(
        "edge30_flat4p2",
        "edge/latch tanh30 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge30_tailflat4p2.sub",
        cap=4.2,
        control_factor=30,
        control_scope="edge",
        tail_mode="flat",
    ),
    Candidate(
        "edge20_flat4p2",
        "edge/latch tanh20 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge20_tailflat4p2.sub",
        cap=4.2,
        control_factor=20,
        control_scope="edge",
        tail_mode="flat",
    ),
    Candidate(
        "edge15_flat4p2",
        "edge/latch tanh15 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge15_tailflat4p2.sub",
        cap=4.2,
        control_factor=15,
        control_scope="edge",
        tail_mode="flat",
    ),
    Candidate(
        "edge15_sel75_flat4p2",
        "edge/latch tanh15 + selector tanh75 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge15_sel75_tailflat4p2.sub",
        cap=4.2,
        tail_mode="flat",
        edge_factor=15,
        selector_factor=75,
    ),
    Candidate(
        "edge15_sel50_flat4p2",
        "edge/latch tanh15 + selector tanh50 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge15_sel50_tailflat4p2.sub",
        cap=4.2,
        tail_mode="flat",
        edge_factor=15,
        selector_factor=50,
    ),
    Candidate(
        "edge50",
        "edge/latch tanh50 only",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge50.sub",
        control_factor=50,
        control_scope="edge",
    ),
    Candidate(
        "edge50_flat4p2",
        "edge/latch tanh50 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_edge50_tailflat4p2.sub",
        cap=4.2,
        control_factor=50,
        control_scope="edge",
        tail_mode="flat",
    ),
    Candidate(
        "sel50_flat4p2",
        "Ku/Kd selector tanh50 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_sel50_tailflat4p2.sub",
        cap=4.2,
        control_factor=50,
        control_scope="selector",
        tail_mode="flat",
    ),
    Candidate(
        "ctrl75_flat4p2",
        "all control tanh75 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_ctrl75_tailflat4p2.sub",
        cap=4.2,
        control_factor=75,
        control_scope="all",
        tail_mode="flat",
    ),
    Candidate(
        "ctrl60_flat4p2",
        "all control tanh60 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_ctrl60_tailflat4p2.sub",
        cap=4.2,
        control_factor=60,
        control_scope="all",
        tail_mode="flat",
    ),
    Candidate(
        "ctrl50_flat4p2",
        "all control tanh50 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_ctrl50_tailflat4p2.sub",
        cap=4.2,
        control_factor=50,
        control_scope="all",
        tail_mode="flat",
    ),
    Candidate(
        "ctrl15_flat4p2",
        "all control tanh15 + KUR/KDR flat tail 4.2 ns",
        "hybrid",
        "driver_OutputInput_Typical_xyce_relaxed92_ctrl15_tailflat4p2.sub",
        cap=4.2,
        control_factor=15,
        control_scope="all",
        tail_mode="flat",
    ),
]


SPISIM_BENCHES = [
    Bench(
        name="spisim_pulse200p",
        title="SPISim-style T-line pulse, 200 ps edge",
        kind="spisim_tline",
        stimulus="PULSE(0 3.3 1n 200p 200p 1.5n 3n)",
        stop="20n",
        target_ns=20.0,
        ng_ref="tb_spisim_val_pulse200p_ngspice_pybis.raw",
        ref_node="v(ntst)",
        xyce_node="v(ntst)",
        timeout_s=45.0,
    ),
    Bench(
        name="spisim_rfr200p",
        title="SPISim-style T-line rise-fall-rise, 200 ps edge",
        kind="spisim_tline",
        stimulus="PWL(0 0 1n 0 1.2n 3.3 9n 3.3 9.2n 0 17n 0 17.2n 3.3 25n 3.3 25.2n 0)",
        stop="26n",
        target_ns=26.0,
        ng_ref="tb_spisim_val_rfr200p_ngspice_pybis.raw",
        ref_node="v(ntst)",
        xyce_node="v(ntst)",
        timeout_s=45.0,
    ),
]


CHANNEL_BENCHES = [
    Bench(
        name="channel_pulsetrain_200p",
        title="50-ohm channel pulse train, 200 ps edge",
        kind="channel_pulse",
        stimulus="PULSE(0 3.3 1.5n 200p 200p 2n 5n)",
        stop="40n",
        target_ns=40.0,
        ng_ref="tb_channel_pulsetrain_200p_ngspice_pybis.raw",
        ref_node="v(n10b)",
        xyce_node="v(n10b)",
        timeout_s=75.0,
    ),
    Bench(
        name="channel_bitpattern_200p",
        title="50-ohm channel deterministic bit pattern, 200 ps edge",
        kind="channel_bitpattern",
        stimulus="PWL(0 0 1.5n 0 1.7n 3.3 6.5n 3.3 6.7n 0 11.5n 0 11.7n 3.3 21.5n 3.3 21.7n 0 31.5n 0 31.7n 3.3 36.5n 3.3 36.7n 0 45n 0)",
        stop="45n",
        target_ns=45.0,
        ng_ref="tb_channel_bitpattern_200p_ngspice_pybis.raw",
        ref_node="v(n10b)",
        xyce_node="v(n10b)",
        timeout_s=90.0,
    ),
    Bench(
        name="channel_prbs7_80n",
        title="50-ohm channel PRBS7, first 80 ns",
        kind="channel_prbs",
        stop="80n",
        target_ns=80.0,
        ng_ref="tb_pybis_prbs7_new50ohm.raw",
        ref_node="v(n10b)",
        xyce_node="v(n10b)",
        timeout_s=70.0,
    ),
    Bench(
        name="channel_prbs7_200n",
        title="50-ohm channel PRBS7, first 200 ns",
        kind="channel_prbs",
        stop="200n",
        target_ns=200.0,
        ng_ref="tb_pybis_prbs7_new50ohm.raw",
        ref_node="v(n10b)",
        xyce_node="v(n10b)",
        timeout_s=150.0,
    ),
    Bench(
        name="channel_prbs7_300n",
        title="50-ohm channel PRBS7, first 300 ns",
        kind="channel_prbs",
        stop="300n",
        target_ns=300.0,
        ng_ref="tb_pybis_prbs7_new50ohm.raw",
        ref_node="v(n10b)",
        xyce_node="v(n10b)",
        timeout_s=140.0,
    ),
    Bench(
        name="channel_prbs7_1000n",
        title="50-ohm channel PRBS7, full 1000 ns",
        kind="channel_prbs",
        stop="1000n",
        target_ns=1000.0,
        ng_ref="tb_pybis_prbs7_new50ohm.raw",
        ref_node="v(n10b)",
        xyce_node="v(n10b)",
        timeout_s=260.0,
    ),
]


def ns(v: np.ndarray | float) -> np.ndarray | float:
    return v * 1e9


def fmt_num(v: float) -> str:
    text = f"{v:.12g}"
    return text.replace(".", "p")


def model_path(candidate: Candidate) -> Path:
    return XYCE_DIR / candidate.include_file


def deck_path(bench: Bench, candidate: Candidate) -> Path:
    return XYCE_DIR / f"tb_tailfix_{bench.name}_{candidate.name}.cir"


def csv_path(bench: Bench, candidate: Candidate) -> Path:
    return Path(str(deck_path(bench, candidate)) + ".csv")


def clean_key(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


def split_table(line: str) -> tuple[str, str, list[float], str]:
    prefix = line.split(TABLE_ARG, 1)[0] + TABLE_ARG
    rest = line.split(TABLE_ARG, 1)[1]
    suffix = ")}"
    if not rest.endswith(suffix):
        raise RuntimeError(f"Unexpected table line ending: {line[-80:]}")
    number_text = rest[: -len(suffix)]
    values = [float(x.strip()) for x in number_text.split(",") if x.strip()]
    if len(values) % 2:
        raise RuntimeError("Table has an odd number of numeric values")
    return prefix, number_text, values, suffix


def interpolate_pair_value(values: list[float], x: float) -> float:
    pairs = list(zip(values[0::2], values[1::2]))
    if x <= pairs[0][0]:
        return pairs[0][1]
    for (x0, y0), (x1, y1) in zip(pairs, pairs[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y1
            frac = (x - x0) / (x1 - x0)
            return y0 + frac * (y1 - y0)
    return pairs[-1][1]


def flatten_table_line(line: str, cap: float) -> str:
    prefix, _number_text, values, suffix = split_table(line)
    hold = interpolate_pair_value(values, cap)
    new_values: list[str] = []
    for x, y in zip(values[0::2], values[1::2]):
        new_values.append(repr(x))
        new_values.append(repr(hold if x >= cap else y))
    return prefix + ", ".join(new_values) + suffix


def soft_cap_expr(cap: float, k: float) -> str:
    gate_hi = f"(0.5+0.5*tanh({k:g}*({cap:g}-V(NX))))"
    gate_lo = f"(0.5-0.5*tanh({k:g}*({cap:g}-V(NX))))"
    blended = f"({gate_hi}*V(NX)+{gate_lo}*{cap:g})"
    return f"table(min(max({blended}, 0), {MAX_NX}),"


def apply_tail_fix(line: str, mode: str, cap: float, softness: float | None = None) -> str:
    if mode == "hard":
        return line.replace(TABLE_ARG, f"table(min(max(V(NX), 0), {cap:g}),", 1)
    if mode == "soft":
        if softness is None:
            raise ValueError("soft tail fix needs softness")
        return line.replace(TABLE_ARG, soft_cap_expr(cap, softness), 1)
    if mode == "flat":
        return flatten_table_line(line, cap)
    raise ValueError(mode)


def b_number(line: str) -> int | None:
    match = re.match(r"B(\d+)\s", line)
    return int(match.group(1)) if match else None


def make_model(candidate: Candidate) -> None:
    if candidate.mode == "base":
        return

    src = XYCE_DIR / BASE_MODEL
    text = src.read_text(encoding="ascii")
    lines = []
    tail_touched = 0
    control_touched = 0

    for line in text.splitlines():
        if line.startswith("B20 ") or line.startswith("B21 "):
            if candidate.mode in {"hard", "soft", "flat"}:
                assert candidate.cap is not None
                line = apply_tail_fix(line, candidate.mode, candidate.cap, candidate.softness)
                tail_touched += 1
            elif candidate.mode == "hybrid" and candidate.tail_mode:
                assert candidate.cap is not None
                line = apply_tail_fix(line, candidate.tail_mode, candidate.cap, candidate.softness)
                tail_touched += 1
            elif candidate.mode != "hybrid":
                raise ValueError(candidate.mode)

        if candidate.mode == "hybrid" and candidate.control_factor is not None:
            num = b_number(line)
            in_edge_scope = num is not None and 10 <= num <= 18 and candidate.control_scope in {"edge", "all"}
            in_selector_scope = num is not None and 24 <= num <= 29 and candidate.control_scope in {"selector", "all"}
            if in_edge_scope or in_selector_scope:
                updated = line.replace("tanh(92*", f"tanh({candidate.control_factor}*")
                if updated != line:
                    control_touched += 1
                line = updated
        if candidate.mode == "hybrid" and (candidate.edge_factor is not None or candidate.selector_factor is not None):
            num = b_number(line)
            factor = None
            if num is not None and 10 <= num <= 18:
                factor = candidate.edge_factor
            elif num is not None and 24 <= num <= 29:
                factor = candidate.selector_factor
            if factor is not None:
                updated = line.replace("tanh(92*", f"tanh({factor}*")
                if updated != line:
                    control_touched += 1
                line = updated
        if candidate.mode == "hybrid" and candidate.line_factor is not None:
            num = b_number(line)
            if num in candidate.control_lines:
                updated = line.replace("tanh(92*", f"tanh({candidate.line_factor}*")
                if updated != line:
                    control_touched += 1
                line = updated
        lines.append(line)

    if candidate.mode in {"hard", "soft", "flat"} and tail_touched != 2:
        raise RuntimeError(f"Expected to touch B20/B21, touched {tail_touched}")
    if candidate.mode == "hybrid":
        if candidate.tail_mode and tail_touched != 2:
            raise RuntimeError(f"Expected to touch B20/B21, touched {tail_touched}")
        if control_touched == 0:
            raise RuntimeError(f"Expected to touch control tanh terms for {candidate.name}")
    model_path(candidate).write_text("\n".join(lines) + "\n", encoding="ascii")


def write_deck(bench: Bench, candidate: Candidate) -> Path:
    make_model(candidate)
    if bench.kind == "spisim_tline":
        body = f"""Vin   in_dig   0  {bench.stimulus}
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include '{candidate.include_file}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

TVAL  pad  0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0  50

.ic V(pad)=0 V(ntst)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
{TIMEINT}
{OUTPUT}
.tran 10p {bench.stop} uic
.print tran format=csv time V(in_dig) V(pad) V(ntst) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
"""
    elif bench.kind in {"channel_pulse", "channel_bitpattern"}:
        body = f"""Vin   in_dig  0  {bench.stimulus}
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3

.include '{candidate.include_file}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

RCH_TX  pad tx_out 1u
.include 'channel_xyce.sp'
RTERM   n10b 0 50

.ic V(pad)=0 V(tx_out)=0 V(n10b)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
{TIMEINT}
{OUTPUT}
.tran 10p {bench.stop} uic
.print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
"""
    elif bench.kind == "channel_prbs":
        body = f""".include 'prbs7_vstim.inc'
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3

.include '{candidate.include_file}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

RCH_TX  pad tx_out 1u
.include 'channel_xyce.sp'
RTERM   n10b 0 50

.ic V(pad)=0 V(tx_out)=0 V(n10b)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
{TIMEINT}
{OUTPUT}
.tran 10p {bench.stop} uic
.print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
"""
    else:
        raise ValueError(bench.kind)

    path = deck_path(bench, candidate)
    path.write_text(
        f"""* Xyce pybis tail-fix probe: {bench.title}
* Candidate: {candidate.title}

{body}.end
""",
        encoding="ascii",
    )
    return path


def load_xyce_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = []
        for row in reader:
            try:
                rows.append([float(x) for x in row])
            except ValueError:
                continue
    if not rows:
        raise RuntimeError(f"No numeric rows in {path}")
    arr = np.asarray(rows, dtype=float)
    return {name.lower(): arr[:, i] for i, name in enumerate(header)}


def load_ngspice_raw(path: Path) -> dict[str, np.ndarray]:
    data = path.read_bytes()
    marker = b"Binary:\n"
    idx = data.find(marker)
    if idx < 0:
        raise RuntimeError(f"Binary marker not found in {path}")

    header = data[:idx].decode("latin1")
    lines = header.splitlines()
    nvars = None
    npts = None
    variables = []
    reading_vars = False

    for line in lines:
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":", 1)[1])
        elif line.strip() == "Variables:":
            reading_vars = True
        elif reading_vars and line.startswith("\t"):
            variables.append(line.split()[1].lower())

    if nvars is None or npts is None or len(variables) != nvars:
        raise RuntimeError(f"Could not parse ngspice raw header for {path}")

    payload = data[idx + len(marker) :]
    if npts == 0:
        npts = len(payload) // (8 * nvars)
    values = struct.unpack("<" + "d" * (nvars * npts), payload[: 8 * nvars * npts])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))
    return {name: arr[:, i] for i, name in enumerate(variables)}


def col(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    key = name.lower()
    if key not in data:
        raise KeyError(f"{name} missing; have {sorted(data)}")
    return data[key]


def run_xyce(bench: Bench, candidate: Candidate) -> tuple[int | None, bool, float]:
    deck = write_deck(bench, candidate)
    csv_file = csv_path(bench, candidate)
    csv_file.unlink(missing_ok=True)
    t0 = time.time()
    try:
        proc = subprocess.run(
            [str(XYCE), deck.name],
            cwd=XYCE_DIR,
            timeout=bench.timeout_s,
            capture_output=True,
            text=True,
        )
        return proc.returncode, False, round(time.time() - t0, 2)
    except subprocess.TimeoutExpired:
        return None, True, round(time.time() - t0, 2)


def compare_to_ref(bench: Bench, data: dict[str, np.ndarray]) -> dict[str, float]:
    ref = load_ngspice_raw(NGSPICE_DIR / bench.ng_ref)
    t_ref = col(ref, "time")
    y_ref = col(ref, bench.ref_node)
    t = col(data, "time")
    y = col(data, bench.xyce_node)

    stop = min(t[-1], t_ref[-1], bench.target_ns * 1e-9)
    mask = (t_ref >= 0) & (t_ref <= stop)
    t_common = t_ref[mask]
    y_common = y_ref[mask]
    y_interp = np.interp(t_common, t, y)
    diff = y_interp - y_common

    return {
        "compare_stop_ns": float(ns(stop)),
        "rmse_mv": float(np.sqrt(np.mean(diff**2)) * 1e3),
        "max_abs_mv": float(np.max(np.abs(diff)) * 1e3),
        "mean_err_mv": float(np.mean(diff) * 1e3),
    }


def run_one(bench: Bench, candidate: Candidate) -> dict[str, object]:
    rc, timed_out, wall_s = run_xyce(bench, candidate)
    out = csv_path(bench, candidate)
    row: dict[str, object] = {
        "bench": bench.name,
        "bench_title": bench.title,
        "candidate": candidate.name,
        "candidate_title": candidate.title,
        "mode": candidate.mode,
        "cap_ns": candidate.cap if candidate.cap is not None else "",
        "softness": candidate.softness if candidate.softness is not None else "",
        "model": candidate.include_file,
        "returncode": rc if rc is not None else "",
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(deck_path(bench, candidate).relative_to(ROOT)).replace("\\", "/"),
        "output": str(out.relative_to(ROOT)).replace("\\", "/"),
    }

    if out.exists():
        try:
            data = load_xyce_csv(out)
            t = col(data, "time")
            row.update(
                {
                    "rows": len(t),
                    "t_end_ns": float(ns(t[-1])),
                    "completed": float(ns(t[-1])) >= bench.target_ns - 0.05,
                    "vout_last": float(col(data, bench.xyce_node)[-1]),
                    "vout_min": float(np.min(col(data, bench.xyce_node))),
                    "vout_max": float(np.max(col(data, bench.xyce_node))),
                }
            )
            if "v(xdrv:nx)" in data:
                row["nx_last"] = float(col(data, "v(xdrv:nx)")[-1])
                row["nx_max"] = float(np.max(col(data, "v(xdrv:nx)")))
            row.update(compare_to_ref(bench, data))
        except Exception as exc:
            row["completed"] = False
            row["error"] = str(exc)
    else:
        row["completed"] = False
        row["error"] = "CSV not generated"
    return row


def write_metrics(rows: list[dict[str, object]], path: Path) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_tline(rows: list[dict[str, object]], out_path: Path) -> None:
    passed = [
        row
        for row in rows
        if row["bench"] == "spisim_rfr200p" and str(row.get("completed")) == "True"
    ]
    ref = load_ngspice_raw(NGSPICE_DIR / "tb_spisim_val_rfr200p_ngspice_pybis.raw")
    t_ref = ns(col(ref, "time"))
    y_ref = col(ref, "v(ntst)")

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(t_ref, y_ref, color="black", linewidth=1.4, label="ngspice direct pybis")
    axes[1].axhline(0, color="black", linewidth=0.7)

    for row in sorted(passed, key=lambda r: float(r.get("rmse_mv", 9999))):
        candidate = next(c for c in CANDIDATES if c.name == row["candidate"])
        data = load_xyce_csv(csv_path(SPISIM_BENCHES[1], candidate))
        t = ns(col(data, "time"))
        y = col(data, "v(ntst)")
        label = f"{candidate.name} ({float(row['rmse_mv']):.1f} mV rms)"
        axes[0].plot(t, y, linewidth=1.0, alpha=0.9, label=label)
        common = t_ref[(t_ref >= 0) & (t_ref <= min(t[-1], t_ref[-1]))]
        err = np.interp(common / 1e9, col(data, "time"), y) - np.interp(common / 1e9, col(ref, "time"), y_ref)
        axes[1].plot(common, err * 1e3, linewidth=0.9, alpha=0.9, label=candidate.name)

    axes[0].set_title("Tail-fix candidates on SPISim-style RFR200p T-line")
    axes[0].set_ylabel("V(ntst) [V]")
    axes[1].set_ylabel("Xyce - ngspice [mV]")
    axes[1].set_xlabel("Time [ns]")
    for ax in axes:
        ax.grid(True, alpha=0.25)
    axes[0].legend(fontsize=8, ncol=2)
    axes[1].legend(fontsize=8, ncol=4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def plot_channel(rows: list[dict[str, object]], out_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=False)
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for ax, bench in zip(axes, CHANNEL_BENCHES[:2]):
        ref = load_ngspice_raw(NGSPICE_DIR / bench.ng_ref)
        ax.plot(ns(col(ref, "time")), col(ref, bench.ref_node), color="black", linewidth=1.2, label="ngspice direct")
        bench_rows = [
            row
            for row in rows
            if row["bench"] == bench.name and str(row.get("completed")) == "True"
        ]
        for i, row in enumerate(sorted(bench_rows, key=lambda r: float(r.get("rmse_mv", 9999)))[:5]):
            candidate = next(c for c in CANDIDATES if c.name == row["candidate"])
            data = load_xyce_csv(csv_path(bench, candidate))
            ax.plot(
                ns(col(data, "time")),
                col(data, bench.xyce_node),
                linewidth=0.9,
                color=colors[i % len(colors)],
                label=f"{candidate.name} ({float(row['rmse_mv']):.1f} mV rms)",
            )
        ax.set_title(bench.title)
        ax.set_ylabel("V(n10b) [V]")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8, ncol=2)
    axes[-1].set_xlabel("Time [ns]")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def plot_score(rows: list[dict[str, object]], out_path: Path) -> None:
    complete = [r for r in rows if str(r.get("completed")) == "True"]
    if not complete:
        return
    labels = []
    values = []
    colors = []
    for row in complete:
        labels.append(f"{row['bench']}\n{row['candidate']}")
        values.append(float(row.get("rmse_mv", np.nan)))
        colors.append("tab:green" if row["mode"] in {"hard", "flat", "soft"} else "tab:gray")

    fig, ax = plt.subplots(figsize=(max(10, 0.32 * len(labels)), 5))
    ax.bar(np.arange(len(labels)), values, color=colors, alpha=0.85)
    ax.set_ylabel("RMSE vs ngspice [mV]")
    ax.set_title("Completed Xyce tail-fix runs")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def select_benches(stage: str) -> list[Bench]:
    if stage == "tline":
        return SPISIM_BENCHES
    if stage == "channel":
        return CHANNEL_BENCHES[:2]
    if stage == "prbs80":
        return CHANNEL_BENCHES[2:3]
    if stage == "prbs":
        return CHANNEL_BENCHES[3:4]
    if stage == "prbs300":
        return CHANNEL_BENCHES[4:5]
    if stage == "prbs1000":
        return CHANNEL_BENCHES[5:]
    if stage == "all":
        return SPISIM_BENCHES + CHANNEL_BENCHES
    raise ValueError(stage)


def select_candidates(names: str) -> list[Candidate]:
    if names == "all":
        return CANDIDATES
    wanted = {name.strip() for name in names.split(",") if name.strip()}
    selected = [candidate for candidate in CANDIDATES if candidate.name in wanted]
    missing = wanted - {candidate.name for candidate in selected}
    if missing:
        raise SystemExit(f"Unknown candidate(s): {', '.join(sorted(missing))}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["tline", "channel", "prbs80", "prbs", "prbs300", "prbs1000", "all"],
        default="tline",
    )
    parser.add_argument("--candidates", default="all")
    parser.add_argument("--metrics", default="xyce_pybis_tailfix_metrics.csv")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    benches = select_benches(args.stage)
    candidates = select_candidates(args.candidates)
    rows = []

    for candidate in candidates:
        make_model(candidate)

    for bench in benches:
        for candidate in candidates:
            row = run_one(bench, candidate)
            rows.append(row)
            status = "PASS" if row.get("completed") is True else "FAIL"
            rmse = row.get("rmse_mv", "")
            rmse_text = f", rmse={float(rmse):.1f} mV" if rmse != "" else ""
            print(
                f"{status:4s} {bench.name:24s} {candidate.name:12s} "
                f"t_end={row.get('t_end_ns', '')} ns wall={row['wall_s']} s{rmse_text}",
                flush=True,
            )

    metrics_path = OUT_DIR / args.metrics
    write_metrics(rows, metrics_path)
    if args.stage in {"tline", "all"}:
        plot_tline(rows, OUT_DIR / "xyce_pybis_tailfix_tline_rfr200p.png")
    if args.stage in {"channel", "all"}:
        plot_channel(rows, OUT_DIR / "xyce_pybis_tailfix_channel.png")
    plot_score(rows, OUT_DIR / f"xyce_pybis_tailfix_{clean_key(args.stage)}_score.png")
    print(f"Wrote {metrics_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
