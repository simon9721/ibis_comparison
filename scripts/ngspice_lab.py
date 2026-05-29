from __future__ import annotations

import argparse
import csv
import json
import math
import re
import struct
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.figure import Figure


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NGSPICE = ROOT.parent / "spice" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"
DEFAULT_PYBIS_REPOS = [
    ROOT.parent / "spice" / "pybis2spice",
    ROOT / "tools" / "pybis2spice",
]


def import_pybis() -> tuple[Any, Any]:
    for repo in DEFAULT_PYBIS_REPOS:
        if repo.exists() and str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
    try:
        from pybis2spice import pybis2spice, subcircuit
    except Exception as exc:  # pragma: no cover - runtime environment check
        raise RuntimeError(
            "Could not import pybis2spice. Run this with the pybis2spice venv python, "
            "for example: C:\\Users\\simom\\Desktop\\Projects\\spice\\pybis2spice\\.venv\\Scripts\\python.exe"
        ) from exc
    return pybis2spice, subcircuit


def clean_label(label: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", label.strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "dut"


def parse_float(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def parse_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


@dataclass
class StimulusConfig:
    kind: str = "pulse_train"  # pulse_train, bit_pattern, prbs7
    v_low: float = 0.0
    v_high: float = 1.2
    start_ns: float = 10.0
    edge_ps: float = 5.0
    high_ns: float = 20.0
    low_ns: float = 20.0
    pulses: int = 5
    bit_rate_mbps: float = 50.0
    bit_pattern: str = "10101010"
    prbs_bits: int = 64
    stop_ns: float | None = None


@dataclass
class TerminationConfig:
    r_ohm: float = 50.0
    v_term: float = 0.0
    channel: str = "none"  # none, ideal_tline
    tline_z0_ohm: float = 50.0
    tline_delay_ns: float = 1.0


@dataclass
class SpiceDutConfig:
    label: str
    include: str
    subckt: str
    pin_order: str = "OUT IN EN VCC VSS"


@dataclass
class IbisDutConfig:
    label: str
    ibis: str
    component: str
    model: str
    corner: str = "Typical"
    io_type: str = "Output"
    subckt_type: str = "InputDriven"


@dataclass
class DutConfig:
    type: str = "ibis"  # ibis, spice
    ibis: IbisDutConfig | None = None
    spice: SpiceDutConfig | None = None

    @property
    def label(self) -> str:
        if self.type == "ibis" and self.ibis:
            return self.ibis.label
        if self.type == "spice" and self.spice:
            return self.spice.label
        return "dut"


@dataclass
class RunConfig:
    ngspice: str = str(DEFAULT_NGSPICE)
    output_dir: str = str(ROOT / "results" / "ngspice_lab_run")
    vdd: float = 1.2
    temperature_c: float = 25.0
    max_step_ps: float = 10.0
    reltol: float = 1e-4
    abstol: float = 1e-12
    vntol: float = 1e-7
    gmin: float = 1e-12
    view: str = "overlay"  # overlay, side_by_side
    stimulus: StimulusConfig = field(default_factory=StimulusConfig)
    termination: TerminationConfig = field(default_factory=TerminationConfig)
    duts: list[DutConfig] = field(default_factory=list)


@dataclass
class DutRuntime:
    config: DutConfig
    label: str
    inst_name: str
    out_node: str
    pad_node: str
    subckt: str
    include_path: Path
    is_ibis: bool


@dataclass
class SimulationResult:
    config: RunConfig
    output_dir: Path
    bench_path: Path
    raw_path: Path
    log_path: Path
    diagram_path: Path
    plot_paths: list[Path]
    traces: dict[str, np.ndarray]
    dut_runtimes: list[DutRuntime]


def config_from_dict(data: dict[str, Any]) -> RunConfig:
    stim_data = data.get("stimulus", {})
    term_data = data.get("termination", {})
    duts = []
    for dut_data in data.get("duts", []):
        dut_type = dut_data.get("type", "ibis")
        if dut_type == "ibis":
            ibis_data = dut_data.get("ibis", dut_data)
            duts.append(
                DutConfig(
                    type="ibis",
                    ibis=IbisDutConfig(
                        label=ibis_data.get("label", ibis_data.get("model", "ibis_dut")),
                        ibis=ibis_data["ibis"],
                        component=ibis_data["component"],
                        model=ibis_data["model"],
                        corner=ibis_data.get("corner", "Typical"),
                        io_type=ibis_data.get("io_type", "Output"),
                        subckt_type=ibis_data.get("subckt_type", "InputDriven"),
                    ),
                )
            )
        elif dut_type == "spice":
            spice_data = dut_data.get("spice", dut_data)
            duts.append(
                DutConfig(
                    type="spice",
                    spice=SpiceDutConfig(
                        label=spice_data.get("label", spice_data.get("subckt", "spice_dut")),
                        include=spice_data["include"],
                        subckt=spice_data["subckt"],
                        pin_order=spice_data.get("pin_order", "OUT IN EN VCC VSS"),
                    ),
                )
            )
        else:
            raise ValueError(f"Unsupported DUT type: {dut_type}")

    return RunConfig(
        ngspice=data.get("ngspice", str(DEFAULT_NGSPICE)),
        output_dir=data.get("output_dir", str(ROOT / "results" / "ngspice_lab_run")),
        vdd=parse_float(data.get("vdd"), 1.2),
        temperature_c=parse_float(data.get("temperature_c"), 25.0),
        max_step_ps=parse_float(data.get("max_step_ps"), 10.0),
        reltol=parse_float(data.get("reltol"), 1e-4),
        abstol=parse_float(data.get("abstol"), 1e-12),
        vntol=parse_float(data.get("vntol"), 1e-7),
        gmin=parse_float(data.get("gmin"), 1e-12),
        view=data.get("view", "overlay"),
        stimulus=StimulusConfig(
            kind=stim_data.get("kind", "pulse_train"),
            v_low=parse_float(stim_data.get("v_low"), 0.0),
            v_high=parse_float(stim_data.get("v_high"), data.get("vdd", 1.2)),
            start_ns=parse_float(stim_data.get("start_ns"), 10.0),
            edge_ps=parse_float(stim_data.get("edge_ps"), 5.0),
            high_ns=parse_float(stim_data.get("high_ns"), 20.0),
            low_ns=parse_float(stim_data.get("low_ns"), 20.0),
            pulses=parse_int(stim_data.get("pulses"), 5),
            bit_rate_mbps=parse_float(stim_data.get("bit_rate_mbps"), 50.0),
            bit_pattern=stim_data.get("bit_pattern", "10101010"),
            prbs_bits=parse_int(stim_data.get("prbs_bits"), 64),
            stop_ns=stim_data.get("stop_ns"),
        ),
        termination=TerminationConfig(
            r_ohm=parse_float(term_data.get("r_ohm"), 50.0),
            v_term=parse_float(term_data.get("v_term"), 0.0),
            channel=term_data.get("channel", "none"),
            tline_z0_ohm=parse_float(term_data.get("tline_z0_ohm"), 50.0),
            tline_delay_ns=parse_float(term_data.get("tline_delay_ns"), 1.0),
        ),
        duts=duts,
    )


def config_to_dict(config: RunConfig) -> dict[str, Any]:
    data = asdict(config)
    duts = []
    for dut in config.duts:
        if dut.type == "ibis" and dut.ibis:
            duts.append({"type": "ibis", "ibis": asdict(dut.ibis)})
        elif dut.type == "spice" and dut.spice:
            duts.append({"type": "spice", "spice": asdict(dut.spice)})
    data["duts"] = duts
    return data


def make_prbs7(nbits: int) -> str:
    reg = 0x7F
    bits = []
    for _ in range(nbits):
        out = reg & 1
        bits.append(str(out))
        new_bit = ((reg >> 6) ^ (reg >> 5)) & 1
        reg = ((reg << 1) & 0x7E) | new_bit
    return "".join(bits)


def stimulus_points(config: StimulusConfig) -> tuple[list[tuple[float, float]], float]:
    edge_ns = config.edge_ps * 1e-3
    points: list[tuple[float, float]] = [(0.0, config.v_low), (config.start_ns, config.v_low)]

    def add_point(t_ns: float, value: float) -> None:
        if points and math.isclose(points[-1][0], t_ns, rel_tol=0.0, abs_tol=1e-15):
            points[-1] = (t_ns, value)
        else:
            points.append((t_ns, value))

    if config.kind == "pulse_train":
        t = config.start_ns
        level = config.v_high
        for _ in range(config.pulses * 2):
            add_point(t, points[-1][1])
            add_point(t + edge_ns, level)
            t += config.high_ns if level == config.v_high else config.low_ns
            level = config.v_low if level == config.v_high else config.v_high
        stop_ns = config.stop_ns if config.stop_ns is not None else t + max(config.high_ns, config.low_ns)
        add_point(float(stop_ns), points[-1][1])
        return points, float(stop_ns)

    if config.kind in {"bit_pattern", "prbs7"}:
        bits = make_prbs7(config.prbs_bits) if config.kind == "prbs7" else re.sub(r"[^01]", "", config.bit_pattern)
        if not bits:
            raise ValueError("Bit-pattern stimulus needs at least one 0/1 bit")
        ui_ns = 1000.0 / config.bit_rate_mbps
        t = config.start_ns
        current = config.v_low
        for bit in bits:
            target = config.v_high if bit == "1" else config.v_low
            if target != current:
                add_point(t, current)
                add_point(t + edge_ns, target)
                current = target
            t += ui_ns
            add_point(t, current)
        stop_ns = config.stop_ns if config.stop_ns is not None else t + 2.0 * ui_ns
        add_point(float(stop_ns), current)
        return points, float(stop_ns)

    raise ValueError(f"Unsupported stimulus kind: {config.kind}")


def pwl_source(points: list[tuple[float, float]]) -> str:
    tokens = []
    for t_ns, value in points:
        tokens.append(f"{t_ns:.9g}n")
        tokens.append(f"{value:.9g}")
    return "PWL(" + " ".join(tokens) + ")"


def parse_ngspice_raw(path: Path) -> dict[str, np.ndarray]:
    data = path.read_bytes()
    marker = b"Binary:\n"
    idx = data.find(marker)
    if idx < 0:
        raise RuntimeError(f"Binary marker not found in {path}")

    header = data[:idx].decode("latin1")
    nvars = None
    npts = None
    variables = []
    reading_vars = False
    for line in header.splitlines():
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            npts = int(line.split(":", 1)[1])
        elif line.strip() == "Variables:":
            reading_vars = True
        elif reading_vars and line.startswith("\t"):
            variables.append(line.split()[1])

    if nvars is None or npts is None or len(variables) != nvars:
        raise RuntimeError(f"Could not parse ngspice raw header for {path}")

    payload = data[idx + len(marker):]
    if npts == 0:
        npts = len(payload) // (8 * nvars)
    values = struct.unpack("<" + "d" * (nvars * npts), payload[: 8 * nvars * npts])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))
    return {name: arr[:, i] for i, name in enumerate(variables)}


def read_subckt_name(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.upper().startswith(".SUBCKT "):
            return line.split()[1]
    raise RuntimeError(f"Could not find .SUBCKT in {path}")


def prepare_ibis_dut(dut: IbisDutConfig, converted_dir: Path) -> tuple[Path, str]:
    pybis2spice, subcircuit = import_pybis()
    converted_dir.mkdir(parents=True, exist_ok=True)
    ibis_path = Path(dut.ibis)
    if not ibis_path.is_absolute():
        ibis_path = ROOT / ibis_path
    ibis = pybis2spice.get_ibis_model_ecdtools(str(ibis_path))
    data_model = pybis2spice.DataModel(ibis, dut.model, dut.component)
    out_path = converted_dir / f"{clean_label(dut.label)}_{clean_label(dut.model)}_{dut.corner}.sub"
    subcircuit.generate_spice_model(
        io_type=dut.io_type,
        subcircuit_type=dut.subckt_type,
        ibis_data=data_model,
        corner=dut.corner,
        output_filepath=str(out_path),
    )
    return out_path, read_subckt_name(out_path)


def map_spice_pins(pin_order: str, out_node: str, config: RunConfig) -> list[str]:
    mapping = {
        "OUT": out_node,
        "OUTPUT": out_node,
        "PAD": out_node,
        "DIE": out_node,
        "IN": "in_dig",
        "INPUT": "in_dig",
        "EN": "en_sig",
        "ENABLE": "en_sig",
        "OE": "en_sig",
        "VCC": "vdd",
        "VDD": "vdd",
        "POWER": "vdd",
        "VSS": "0",
        "GND": "0",
        "GROUND": "0",
    }
    pins = []
    for token in pin_order.split():
        pins.append(mapping.get(token.upper(), token))
    return pins


def prepare_duts(config: RunConfig, out_dir: Path) -> list[DutRuntime]:
    runtimes: list[DutRuntime] = []
    labels_seen: set[str] = set()
    converted_dir = out_dir / "converted"
    for index, dut in enumerate(config.duts, start=1):
        base_label = clean_label(dut.label)
        label = base_label
        suffix = 2
        while label.lower() in labels_seen:
            label = f"{base_label}_{suffix}"
            suffix += 1
        labels_seen.add(label.lower())

        inst_name = f"X{label}"
        out_node = f"src_{label}"
        pad_node = f"pad_{label}"
        if dut.type == "ibis" and dut.ibis:
            include_path, subckt = prepare_ibis_dut(dut.ibis, converted_dir)
            runtimes.append(DutRuntime(dut, label, inst_name, out_node, pad_node, subckt, include_path, True))
        elif dut.type == "spice" and dut.spice:
            include_path = Path(dut.spice.include)
            if not include_path.is_absolute():
                include_path = ROOT / include_path
            runtimes.append(DutRuntime(dut, label, inst_name, out_node, pad_node, dut.spice.subckt, include_path, False))
        else:
            raise ValueError(f"Invalid DUT config: {dut}")
    if not runtimes:
        raise ValueError("At least one DUT is required")
    return runtimes


def write_testbench(config: RunConfig, runtimes: list[DutRuntime], out_dir: Path) -> tuple[Path, Path, float]:
    bench_dir = out_dir / "benches"
    raw_dir = out_dir / "raw"
    bench_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    points, stop_ns = stimulus_points(config.stimulus)
    bench_path = bench_dir / "ngspice_lab_testbench.sp"
    raw_path = raw_dir / "ngspice_lab_testbench.raw"

    include_lines = []
    seen_includes = set()
    seen_subckts = set()
    for runtime in runtimes:
        include_text = runtime.include_path.as_posix()
        subckt_key = runtime.subckt.lower()
        if subckt_key not in seen_subckts and include_text not in seen_includes:
            include_lines.append(f".include '{include_text}'")
            seen_includes.add(include_text)
            seen_subckts.add(subckt_key)

    term_node = "0" if abs(config.termination.v_term) < 1e-18 else "vterm"
    lines = [
        "* Generated by scripts/ngspice_lab.py",
        f".temp {config.temperature_c:g}",
        (
            f".options method=gear maxord=2 reltol={config.reltol:g} abstol={config.abstol:g} "
            f"vntol={config.vntol:g} gmin={config.gmin:g}"
        ),
        f"Vin in_dig 0 {pwl_source(points)}",
        f"Ven en_sig 0 DC {config.vdd:g}",
        f"Vdd vdd 0 DC {config.vdd:g}",
    ]
    if term_node != "0":
        lines.append(f"Vterm {term_node} 0 DC {config.termination.v_term:g}")
    lines.extend(include_lines)

    save_vars = ["V(in_dig)"]
    for runtime in runtimes:
        if runtime.is_ibis:
            lines.append(f"{runtime.inst_name} {runtime.out_node} in_dig en_sig vdd 0 {runtime.subckt}")
        else:
            assert runtime.config.spice is not None
            pins = map_spice_pins(runtime.config.spice.pin_order, runtime.out_node, config)
            lines.append(f"{runtime.inst_name} {' '.join(pins)} {runtime.subckt}")

        if config.termination.channel == "ideal_tline":
            lines.append(
                f"TCH_{runtime.label} {runtime.out_node} 0 {runtime.pad_node} 0 "
                f"Z0={config.termination.tline_z0_ohm:g} TD={config.termination.tline_delay_ns:g}n"
            )
        else:
            runtime.pad_node = runtime.out_node

        lines.append(f"RLOAD_{runtime.label} {runtime.pad_node} {term_node} {config.termination.r_ohm:g}")
        save_vars.append(f"V({runtime.pad_node})")
        if runtime.pad_node != runtime.out_node:
            save_vars.append(f"V({runtime.out_node})")
        if runtime.is_ibis:
            save_vars.append(f"V({runtime.inst_name.lower()}.ku)")
            save_vars.append(f"V({runtime.inst_name.lower()}.kd)")

    lines.append(".save " + " ".join(save_vars))
    lines.append(f".tran {config.max_step_ps:g}p {stop_ns:g}n")
    lines.append(".end")
    lines.append("")
    bench_path.write_text("\n".join(lines), encoding="utf-8")
    return bench_path, raw_path, stop_ns


def run_ngspice(config: RunConfig, bench_path: Path, raw_path: Path) -> Path:
    ngspice = Path(config.ngspice)
    if not ngspice.exists():
        raise FileNotFoundError(f"ngspice executable not found: {ngspice}")
    proc = subprocess.run(
        [str(ngspice), "-b", "-r", str(raw_path), str(bench_path)],
        cwd=bench_path.parent,
        capture_output=True,
        text=True,
    )
    log_path = raw_path.with_suffix(".log")
    log_path.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"ngspice failed. See {log_path}")
    return log_path


def draw_testbench_schematic(config: RunConfig, runtimes: list[DutRuntime], out_path: Path | None = None) -> Figure:
    row_h = 2.65
    height = max(5.2, 1.85 + row_h * len(runtimes))
    width = 13.4
    fig = Figure(figsize=(12.8, height), dpi=130)
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)

    def line(x1: float, y1: float, x2: float, y2: float, color: str = "#2f2f2f", lw: float = 1.25) -> None:
        ax.plot([x1, x2], [y1, y2], color=color, lw=lw, solid_capstyle="round")

    def dot(x: float, y: float) -> None:
        from matplotlib.patches import Circle

        ax.add_patch(Circle((x, y), 0.045, color="#2f2f2f"))

    def ground(x: float, y: float) -> None:
        line(x, y, x, y + 0.12)
        line(x - 0.22, y, x + 0.22, y)
        line(x - 0.15, y - 0.08, x + 0.15, y - 0.08)
        line(x - 0.08, y - 0.16, x + 0.08, y - 0.16)

    def source(x: float, y: float, label: str) -> None:
        from matplotlib.patches import Circle

        ax.add_patch(Circle((x, y), 0.32, fill=False, lw=1.25, edgecolor="#2f2f2f"))
        ax.text(x - 0.07, y + 0.11, "+", fontsize=9, ha="center", va="center")
        ax.text(x - 0.07, y - 0.13, "-", fontsize=9, ha="center", va="center")
        ax.text(x, y + 0.55, label, ha="center", va="bottom", fontsize=8)

    def dut_box(x: float, y: float, runtime: DutRuntime) -> None:
        rect = plt_rectangle((x, y - 0.62), 2.15, 1.24, fc="#eef7ef")
        ax.add_patch(rect)
        detail = runtime.config.type.upper()
        if runtime.config.type == "ibis" and runtime.config.ibis:
            detail += f"\n{runtime.config.ibis.model}"
        elif runtime.config.type == "spice" and runtime.config.spice:
            detail += f"\n{runtime.config.spice.subckt}"
        ax.text(x + 1.08, y + 0.18, runtime.label, ha="center", va="center", fontsize=9, weight="bold")
        ax.text(x + 1.08, y - 0.24, detail, ha="center", va="center", fontsize=7.5)
        ax.text(x - 0.06, y + 0.28, "IN", ha="right", va="center", fontsize=7)
        ax.text(x - 0.06, y - 0.28, "EN", ha="right", va="center", fontsize=7)
        ax.text(x + 2.21, y, "OUT", ha="left", va="center", fontsize=7)
        ax.text(x + 1.08, y + 0.74, "VDD", ha="center", va="bottom", fontsize=7)
        ax.text(x + 1.08, y - 0.74, "VSS", ha="center", va="top", fontsize=7)

    def resistor_vertical(x: float, y_top: float, y_bottom: float, label: str) -> None:
        lead = 0.16
        line(x, y_top, x, y_top - lead)
        line(x, y_bottom + lead, x, y_bottom)
        zig_top = y_top - lead
        zig_bottom = y_bottom + lead
        steps = 7
        ys = np.linspace(zig_top, zig_bottom, steps + 1)
        xs = []
        for i in range(steps + 1):
            if i == 0 or i == steps:
                xs.append(x)
            elif i % 2:
                xs.append(x - 0.18)
            else:
                xs.append(x + 0.18)
        ax.plot(xs, ys, color="#2f2f2f", lw=1.25)
        ax.text(x + 0.34, (y_top + y_bottom) / 2, label, ha="left", va="center", fontsize=8)

    def tline(x1: float, x2: float, y: float) -> None:
        line(x1, y + 0.12, x2, y + 0.12, "#5a3c8a")
        line(x1, y - 0.12, x2, y - 0.12, "#5a3c8a")
        line(x1, y, x1 + 0.12, y + 0.12, "#5a3c8a")
        line(x1, y, x1 + 0.12, y - 0.12, "#5a3c8a")
        line(x2 - 0.12, y + 0.12, x2, y, "#5a3c8a")
        line(x2 - 0.12, y - 0.12, x2, y, "#5a3c8a")
        ax.text(
            (x1 + x2) / 2,
            y + 0.42,
            f"T-line\nZ0={config.termination.tline_z0_ohm:g} ohm, TD={config.termination.tline_delay_ns:g} ns",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color="#5a3c8a",
        )

    ax.text(width / 2, height - 0.2, "ngspice testbench schematic", ha="center", va="top", fontsize=13, weight="bold")
    stim = config.stimulus
    stim_lines = [f"Vin: {stim.kind}", f"{stim.v_low:g} to {stim.v_high:g} V", f"edge {stim.edge_ps:g} ps"]
    if stim.kind == "pulse_train":
        stim_lines.append(f"{stim.pulses} pulses, {stim.high_ns:g} ns high / {stim.low_ns:g} ns low")
    elif stim.kind == "bit_pattern":
        stim_lines.append(f"{stim.bit_rate_mbps:g} Mbps, pattern {stim.bit_pattern[:24]}")
    else:
        stim_lines.append(f"{stim.bit_rate_mbps:g} Mbps, PRBS7 {stim.prbs_bits} bits")
    ax.text(0.35, height - 0.72, "\n".join(stim_lines), ha="left", va="top", fontsize=8, color="#333333")

    for i, runtime in enumerate(runtimes):
        y = height - 2.3 - i * row_h
        src_x = 0.95
        dut_x = 3.65
        out_x = dut_x + 2.15
        pad_x = 9.45 if config.termination.channel == "ideal_tline" else 8.15
        res_x = 10.05 if config.termination.channel == "ideal_tline" else 9.05

        source(src_x, y + 0.28, "Vin")
        line(src_x + 0.32, y + 0.28, dut_x, y + 0.28)
        dot(dut_x, y + 0.28)
        ax.text((src_x + dut_x) / 2, y + 0.45, "in_dig", ha="center", va="bottom", fontsize=7.5)

        line(src_x + 0.18, y - 0.28, dut_x, y - 0.28)
        dot(dut_x, y - 0.28)
        ax.text(src_x + 0.12, y - 0.1, f"EN={config.vdd:g} V", ha="left", va="bottom", fontsize=8)

        dut_box(dut_x, y, runtime)
        line(dut_x + 1.08, y + 0.62, dut_x + 1.08, y + 0.98)
        ax.text(dut_x + 1.08, y + 1.08, f"VDD {config.vdd:g} V", ha="center", va="bottom", fontsize=7.5)
        line(dut_x + 1.08, y - 0.62, dut_x + 1.08, y - 1.0)
        ground(dut_x + 1.08, y - 1.12)

        line(out_x, y, out_x + 0.45, y)
        if config.termination.channel == "ideal_tline":
            tline(out_x + 0.45, pad_x - 0.45, y)
            line(pad_x - 0.45, y, pad_x, y)
        else:
            line(out_x + 0.45, y, pad_x, y)

        dot(pad_x, y)
        ax.text(pad_x, y + 0.18, runtime.pad_node, ha="center", va="bottom", fontsize=7.5)
        line(pad_x, y, res_x, y)
        resistor_vertical(res_x, y, y - 1.02, f"Rterm\n{config.termination.r_ohm:g} ohm")

        if abs(config.termination.v_term) < 1e-18:
            ground(res_x, y - 1.18)
            ax.text(res_x + 0.34, y - 1.18, "0 V", ha="left", va="center", fontsize=7.5)
        else:
            source(res_x, y - 1.62, f"Vterm={config.termination.v_term:g} V")
            line(res_x, y - 1.02, res_x, y - 1.3)
            line(res_x, y - 1.94, res_x, y - 2.12)
            ground(res_x, y - 2.24)

        if i < len(runtimes) - 1:
            line(0.25, y - 1.35, width - 0.25, y - 1.35, "#dddddd", 0.8)

    fig.tight_layout()
    return fig


def plt_rectangle(xy: tuple[float, float], w: float, h: float, fc: str) -> Any:
    from matplotlib.patches import FancyBboxPatch

    return FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        linewidth=1.1,
        edgecolor="#555555",
        facecolor=fc,
    )


def trace_name(name: str) -> str:
    return name.lower()


def get_trace(traces: dict[str, np.ndarray], name: str) -> np.ndarray | None:
    lower = name.lower()
    for key, value in traces.items():
        if key.lower() == lower:
            return value
    return None


def make_transient_figure(result: SimulationResult, view: str | None = None) -> Figure:
    traces = result.traces
    time_vec = get_trace(traces, "time")
    if time_vec is None:
        raise RuntimeError("Raw file does not contain time trace")
    t_ns = time_vec * 1e9
    vin = get_trace(traces, "v(in_dig)")
    view = view or result.config.view

    if view == "side_by_side":
        rows = len(result.dut_runtimes)
        fig = Figure(figsize=(11.5, max(3.5, 2.3 * rows)), dpi=130)
        axes = fig.subplots(rows, 1, sharex=True)
        if rows == 1:
            axes = [axes]
        for ax, runtime in zip(axes, result.dut_runtimes):
            pad = get_trace(traces, f"v({runtime.pad_node})")
            if pad is not None:
                ax.plot(t_ns, pad, lw=2.0, label=f"{runtime.label} pad")
            if vin is not None:
                ax2 = ax.twinx()
                ax2.plot(t_ns, vin, color="#777777", alpha=0.35, lw=1.0, label="input")
                ax2.set_ylabel("Input (V)", color="#777777")
                ax2.tick_params(axis="y", labelcolor="#777777")
            ax.set_title(runtime.label)
            ax.set_ylabel("Pad (V)")
            ax.grid(True, alpha=0.3)
            ax.legend(loc="best")
        axes[-1].set_xlabel("Time (ns)")
        fig.suptitle("ngspice transient results", fontsize=13)
        fig.tight_layout()
        return fig

    fig = Figure(figsize=(11.5, 5.8), dpi=130)
    ax = fig.add_subplot(111)
    if vin is not None:
        ax.plot(t_ns, vin, color="#555555", lw=1.7, label="input stimulus")
    for runtime in result.dut_runtimes:
        pad = get_trace(traces, f"v({runtime.pad_node})")
        if pad is not None:
            ax.plot(t_ns, pad, lw=2.0, label=f"{runtime.label} pad")
    ax.set_title("ngspice transient overlay")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def write_summary(result: SimulationResult, stop_ns: float) -> None:
    out_dir = result.output_dir
    csv_path = out_dir / "run_summary.csv"
    time_vec = get_trace(result.traces, "time")
    rows = []
    if time_vec is not None:
        t_ns = time_vec * 1e9
        for runtime in result.dut_runtimes:
            pad = get_trace(result.traces, f"v({runtime.pad_node})")
            if pad is None:
                continue
            last_mask = t_ns >= max(0.0, stop_ns - 0.1 * stop_ns)
            rows.append(
                {
                    "label": runtime.label,
                    "type": runtime.config.type,
                    "pad_min_v": float(np.min(pad)),
                    "pad_max_v": float(np.max(pad)),
                    "pad_final_v": float(pad[-1]),
                    "pad_last_window_avg_v": float(np.mean(pad[last_mask])) if np.any(last_mask) else float(pad[-1]),
                    "pad_node": runtime.pad_node,
                    "source_node": runtime.out_node,
                }
            )
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    readme = [
        "# ngspice lab run",
        "",
        f"- Bench: `{result.bench_path.relative_to(out_dir)}`",
        f"- Raw: `{result.raw_path.relative_to(out_dir)}`",
        f"- Log: `{result.log_path.relative_to(out_dir)}`",
        f"- Schematic: `{result.diagram_path.relative_to(out_dir)}`",
        f"- Termination: `{result.config.termination.r_ohm:g} ohm` to `{result.config.termination.v_term:g} V`",
        f"- Channel: `{result.config.termination.channel}`",
        f"- Stimulus: `{result.config.stimulus.kind}`",
        f"- Stop time: `{stop_ns:g} ns`",
        "",
        "DUTs:",
    ]
    for runtime in result.dut_runtimes:
        readme.append(f"- `{runtime.label}`: `{runtime.config.type}` using `{runtime.subckt}`")
    readme.extend(["", "Plots:"])
    for plot_path in result.plot_paths:
        readme.append(f"- `{plot_path.relative_to(out_dir)}`")
    if rows:
        readme.extend(["", "Summary CSV:", "", "- `run_summary.csv`"])
    (out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")


def execute_run(config: RunConfig) -> SimulationResult:
    out_dir = Path(config.output_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "plots").mkdir(exist_ok=True)
    config.output_dir = str(out_dir)

    runtimes = prepare_duts(config, out_dir)
    bench_path, raw_path, stop_ns = write_testbench(config, runtimes, out_dir)
    diagram_path = out_dir / "plots" / "testbench_schematic.png"
    schematic = draw_testbench_schematic(config, runtimes, diagram_path)
    schematic.savefig(diagram_path, dpi=180, bbox_inches="tight")

    log_path = run_ngspice(config, bench_path, raw_path)
    traces = parse_ngspice_raw(raw_path)
    result = SimulationResult(config, out_dir, bench_path, raw_path, log_path, diagram_path, [], traces, runtimes)
    overlay = make_transient_figure(result, "overlay")
    overlay_path = out_dir / "plots" / "transient_overlay.png"
    overlay.savefig(overlay_path, dpi=180, bbox_inches="tight")
    side = make_transient_figure(result, "side_by_side")
    side_path = out_dir / "plots" / "transient_side_by_side.png"
    side.savefig(side_path, dpi=180, bbox_inches="tight")
    result.plot_paths = [overlay_path, side_path]
    (out_dir / "config_used.json").write_text(json.dumps(config_to_dict(config), indent=2), encoding="utf-8")
    write_summary(result, stop_ns)
    return result


def load_ibis_names(ibis_path: str) -> tuple[list[str], list[str]]:
    pybis2spice, _ = import_pybis()
    ibis = pybis2spice.get_ibis_model_ecdtools(str(Path(ibis_path)))
    return list(pybis2spice.list_components(ibis)), list(pybis2spice.list_models(ibis))


def example_config() -> RunConfig:
    ibis = ROOT / "pcbauto" / "Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs"
    return RunConfig(
        output_dir=str(ROOT / "results" / "ngspice_lab_hibiki_1160_5pulse"),
        vdd=1.2,
        view="overlay",
        stimulus=StimulusConfig(kind="pulse_train", v_low=0.0, v_high=1.2, start_ns=10.0, edge_ps=5.0, high_ns=20.0, low_ns=20.0, pulses=5),
        termination=TerminationConfig(r_ohm=1160.0, v_term=0.0, channel="none"),
        duts=[
            DutConfig(
                type="ibis",
                ibis=IbisDutConfig(
                    label="hibiki_i3c_0p125ma",
                    ibis=str(ibis),
                    component="A11486_IBIS-00001760",
                    model="I3C_TX_0p125mA_tx",
                ),
            )
        ],
    )


def parse_direct_ibis_args(args: argparse.Namespace) -> RunConfig:
    if not args.ibis or not args.model or not args.component:
        raise SystemExit("Direct run needs --ibis, --component, and --model, or use --config.")
    out_dir = args.output_dir or str(ROOT / "results" / f"ngspice_lab_{clean_label(args.model)}_{int(time.time())}")
    return RunConfig(
        ngspice=args.ngspice or str(DEFAULT_NGSPICE),
        output_dir=out_dir,
        vdd=args.vdd,
        view=args.view,
        stimulus=StimulusConfig(
            kind=args.stimulus,
            v_low=0.0,
            v_high=args.vdd,
            start_ns=args.start_ns,
            edge_ps=args.edge_ps,
            high_ns=args.high_ns,
            low_ns=args.low_ns,
            pulses=args.pulses,
            bit_rate_mbps=args.bit_rate_mbps,
            bit_pattern=args.bit_pattern,
            prbs_bits=args.prbs_bits,
            stop_ns=args.stop_ns,
        ),
        termination=TerminationConfig(
            r_ohm=args.r_ohm,
            v_term=args.v_term,
            channel=args.channel,
            tline_z0_ohm=args.tline_z0_ohm,
            tline_delay_ns=args.tline_delay_ns,
        ),
        duts=[
            DutConfig(
                type="ibis",
                ibis=IbisDutConfig(
                    label=args.label or args.model,
                    ibis=args.ibis,
                    component=args.component,
                    model=args.model,
                    corner=args.corner,
                ),
            )
        ],
    )


def gui_main() -> None:
    import threading
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

    class App:
        def __init__(self, root: tk.Tk) -> None:
            self.root = root
            self.root.title("ngspice Lab")
            self.root.geometry("1320x860")
            self.root.minsize(980, 640)
            self.duts: list[DutConfig] = []
            self.result: SimulationResult | None = None
            self.canvas: FigureCanvasTkAgg | None = None
            self.toolbar: NavigationToolbar2Tk | None = None
            self.schematic_canvas: FigureCanvasTkAgg | None = None
            self.schematic_toolbar: NavigationToolbar2Tk | None = None

            self.vars: dict[str, tk.Variable] = {}
            self.build()
            self.load_defaults()

        def var(self, name: str, value: Any = "") -> tk.StringVar:
            v = tk.StringVar(value=str(value))
            self.vars[name] = v
            return v

        def build(self) -> None:
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(1, weight=1)

            toolbar = ttk.Frame(self.root, padding=(10, 8))
            toolbar.grid(row=0, column=0, sticky="ew")
            toolbar.columnconfigure(6, weight=1)
            ttk.Button(toolbar, text="Generate Schematic", command=self.generate_diagram).grid(row=0, column=0, padx=(0, 6))
            ttk.Button(toolbar, text="Run Sim", command=self.run_sim).grid(row=0, column=1, padx=(0, 6))
            ttk.Button(toolbar, text="Save Config", command=self.save_config).grid(row=0, column=2, padx=(0, 16))
            ttk.Label(toolbar, text="Output view").grid(row=0, column=3, padx=(0, 4))
            self.output_view = ttk.Combobox(
                toolbar,
                textvariable=self.var("output_view", "transient_overlay"),
                values=["transient_overlay", "transient_side_by_side"],
                state="readonly",
                width=22,
            )
            self.output_view.grid(row=0, column=4, padx=(0, 10))
            self.output_view.bind("<<ComboboxSelected>>", lambda _event: self.refresh_output_view())

            self.status = tk.StringVar(value="Ready")
            ttk.Label(toolbar, textvariable=self.status).grid(row=0, column=6, sticky="e")

            self.notebook = ttk.Notebook(self.root)
            self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

            setup_tab = ttk.Frame(self.notebook)
            output_tab = ttk.Frame(self.notebook)
            self.notebook.add(setup_tab, text="Setup")
            self.notebook.add(output_tab, text="Output")

            setup_body = self.scrollable_frame(setup_tab)
            setup_body.columnconfigure(0, weight=1)
            setup_body.columnconfigure(1, weight=1)
            setup_body.columnconfigure(2, weight=1)

            run_box = self.section(setup_body, "Run", 0, 0)
            self.entry(run_box, 0, "Output dir", "output_dir", str(ROOT / "results" / "ngspice_lab_gui_run"), browse_dir=True)
            self.entry(run_box, 1, "ngspice", "ngspice", str(DEFAULT_NGSPICE), browse_file=True)
            self.entry(run_box, 2, "VDD", "vdd", "1.2")

            stim_box = self.section(setup_body, "Stimulus", 0, 1)
            self.combo(stim_box, 0, "Kind", "stim_kind", ["pulse_train", "bit_pattern", "prbs7"], "pulse_train")
            self.entry(stim_box, 1, "Start ns", "start_ns", "10")
            self.entry(stim_box, 2, "Edge ps", "edge_ps", "5")
            self.entry(stim_box, 3, "High ns", "high_ns", "20")
            self.entry(stim_box, 4, "Low ns", "low_ns", "20")
            self.entry(stim_box, 5, "Pulses", "pulses", "5")
            self.entry(stim_box, 6, "Bit rate Mbps", "bit_rate_mbps", "50")
            self.entry(stim_box, 7, "Bit pattern", "bit_pattern", "10101010")
            self.entry(stim_box, 8, "PRBS bits", "prbs_bits", "64")
            self.entry(stim_box, 9, "Stop ns optional", "stop_ns", "")

            term_box = self.section(setup_body, "Termination / Channel", 0, 2)
            self.combo(term_box, 0, "Preset", "preset", ["1160 ohm to ground", "50 ohm to ground", "custom"], "1160 ohm to ground", callback=self.apply_preset)
            self.entry(term_box, 1, "R ohm", "r_ohm", "1160")
            self.entry(term_box, 2, "V term", "v_term", "0")
            self.combo(term_box, 3, "Channel", "channel", ["none", "ideal_tline"], "none")
            self.entry(term_box, 4, "Tline Z0", "tline_z0_ohm", "50")
            self.entry(term_box, 5, "Tline delay ns", "tline_delay_ns", "1")

            dut_box = self.section(setup_body, "Add DUT", 1, 0, columnspan=2)
            dut_box.columnconfigure(1, weight=1)
            dut_box.columnconfigure(4, weight=1)
            self.combo(dut_box, 0, "DUT type", "dut_type", ["ibis", "spice"], "ibis", column=0)
            self.entry(dut_box, 1, "Label", "dut_label", "hibiki_i3c", column=0)
            self.entry(dut_box, 2, "IBIS file", "ibis", str(ROOT / "pcbauto" / "Hibiki_IOCL_I3C_I2C_ibis_20260211.ibs"), browse_file=True, column=0)
            self.entry(dut_box, 3, "Component", "component", "A11486_IBIS-00001760", column=0)
            self.entry(dut_box, 4, "Model", "model", "I3C_TX_0p125mA_tx", column=0)
            self.entry(dut_box, 5, "Corner", "corner", "Typical", column=0)
            self.entry(dut_box, 0, "SPICE include", "spice_include", "", browse_file=True, column=3)
            self.entry(dut_box, 1, "SPICE subckt", "spice_subckt", "", column=3)
            self.entry(dut_box, 2, "SPICE pin order", "pin_order", "OUT IN EN VCC VSS", column=3)

            dut_actions = ttk.Frame(dut_box)
            dut_actions.grid(row=6, column=0, columnspan=6, sticky="ew", pady=(8, 0))
            ttk.Button(dut_actions, text="List IBIS Names", command=self.list_ibis_names).pack(side=tk.LEFT, padx=(0, 6))
            ttk.Button(dut_actions, text="Add DUT", command=self.add_dut).pack(side=tk.LEFT, padx=(0, 6))
            ttk.Button(dut_actions, text="Clear DUTs", command=self.clear_duts).pack(side=tk.LEFT)

            list_box = self.section(setup_body, "DUTs In This Run", 1, 2)
            self.dut_tree = ttk.Treeview(list_box, columns=("type", "detail"), height=9, show="headings")
            self.dut_tree.heading("type", text="Type")
            self.dut_tree.heading("detail", text="Detail")
            self.dut_tree.column("type", width=70, stretch=False)
            self.dut_tree.column("detail", width=360, stretch=True)
            self.dut_tree.grid(row=0, column=0, sticky="nsew")
            list_box.rowconfigure(0, weight=1)
            list_box.columnconfigure(0, weight=1)

            schematic_box = self.section(setup_body, "Schematic Preview", 2, 0, columnspan=3)
            schematic_box.rowconfigure(0, weight=1)
            schematic_box.columnconfigure(0, weight=1)
            self.schematic_area = ttk.Frame(schematic_box)
            self.schematic_area.grid(row=0, column=0, sticky="nsew")
            ttk.Label(
                self.schematic_area,
                text="Use Generate Schematic to preview the equivalent testbench before running ngspice.",
            ).pack(anchor="w", padx=8, pady=8)

            output_tab.columnconfigure(0, weight=1)
            output_tab.rowconfigure(1, weight=1)
            output_controls = ttk.Frame(output_tab, padding=(8, 6))
            output_controls.grid(row=0, column=0, sticky="ew")
            ttk.Label(output_controls, text="View").pack(side=tk.LEFT)
            self.output_tab_view = ttk.Combobox(
                output_controls,
                textvariable=self.vars["output_view"],
                values=["transient_overlay", "transient_side_by_side"],
                state="readonly",
                width=22,
            )
            self.output_tab_view.pack(side=tk.LEFT, padx=(6, 12))
            self.output_tab_view.bind("<<ComboboxSelected>>", lambda _event: self.refresh_output_view())
            ttk.Button(output_controls, text="Redraw", command=self.refresh_output_view).pack(side=tk.LEFT, padx=(0, 6))
            ttk.Button(output_controls, text="Show Output Folder", command=self.show_output_folder).pack(side=tk.LEFT)

            output_pane = ttk.PanedWindow(output_tab, orient=tk.VERTICAL)
            output_pane.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
            self.plot_area = ttk.Frame(output_pane)
            self.output_text_frame = ttk.Frame(output_pane)
            output_pane.add(self.plot_area, weight=5)
            output_pane.add(self.output_text_frame, weight=1)
            self.output_text = tk.Text(self.output_text_frame, height=7, wrap="word")
            self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            text_scroll = ttk.Scrollbar(self.output_text_frame, orient=tk.VERTICAL, command=self.output_text.yview)
            text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.output_text.configure(yscrollcommand=text_scroll.set)
            self.write_output_message("Run a simulation to populate this tab. The setup schematic preview lives in the Setup tab.")

        def scrollable_frame(self, parent: Any) -> ttk.Frame:
            container = ttk.Frame(parent)
            container.pack(fill=tk.BOTH, expand=True)
            canvas = tk.Canvas(container, highlightthickness=0)
            scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
            body = ttk.Frame(canvas)

            body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
            window_id = canvas.create_window((0, 0), window=body, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            def resize_body(event: Any) -> None:
                canvas.itemconfigure(window_id, width=event.width)

            def wheel(event: Any) -> None:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            canvas.bind("<Configure>", resize_body)
            canvas.bind_all("<MouseWheel>", wheel)
            return body

        def section(self, parent: Any, title: str, row: int, column: int, columnspan: int = 1) -> ttk.LabelFrame:
            frame = ttk.LabelFrame(parent, text=title, padding=10)
            frame.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=6, pady=6)
            frame.columnconfigure(1, weight=1)
            return frame

        def entry(self, parent: Any, row: int, label: str, name: str, value: str, browse_file: bool = False, browse_dir: bool = False, column: int = 0) -> None:
            ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=2, padx=(0, 6))
            ent = ttk.Entry(parent, textvariable=self.var(name, value), width=38)
            ent.grid(row=row, column=column + 1, sticky="ew", pady=2)
            if browse_file:
                ttk.Button(parent, text="...", width=3, command=lambda n=name: self.browse_file(n)).grid(row=row, column=column + 2, padx=(3, 8))
            elif browse_dir:
                ttk.Button(parent, text="...", width=3, command=lambda n=name: self.browse_dir(n)).grid(row=row, column=column + 2, padx=(3, 8))

        def combo(self, parent: Any, row: int, label: str, name: str, values: list[str], value: str, callback: Any | None = None, column: int = 0) -> None:
            ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=2, padx=(0, 6))
            cb = ttk.Combobox(parent, textvariable=self.var(name, value), values=values, state="readonly", width=35)
            cb.grid(row=row, column=column + 1, sticky="ew", pady=2)
            if callback:
                cb.bind("<<ComboboxSelected>>", lambda _event: callback())

        def browse_file(self, var_name: str) -> None:
            path = filedialog.askopenfilename()
            if path:
                self.vars[var_name].set(path)

        def browse_dir(self, var_name: str) -> None:
            path = filedialog.askdirectory()
            if path:
                self.vars[var_name].set(path)

        def apply_preset(self) -> None:
            preset = self.vars["preset"].get()
            if preset == "50 ohm to ground":
                self.vars["r_ohm"].set("50")
                self.vars["v_term"].set("0")
            elif preset == "1160 ohm to ground":
                self.vars["r_ohm"].set("1160")
                self.vars["v_term"].set("0")

        def load_defaults(self) -> None:
            if not self.duts:
                self.add_dut()

        def list_ibis_names(self) -> None:
            try:
                comps, models = load_ibis_names(self.vars["ibis"].get())
                messagebox.showinfo(
                    "IBIS names",
                    "Components:\n"
                    + "\n".join(comps[:20])
                    + "\n\nModels:\n"
                    + "\n".join(models[:40])
                    + ("\n..." if len(models) > 40 else ""),
                )
            except Exception as exc:
                messagebox.showerror("IBIS load failed", str(exc))

        def add_dut(self) -> None:
            dut_type = self.vars["dut_type"].get()
            label = self.vars["dut_label"].get().strip() or self.vars["model"].get().strip() or "dut"
            if dut_type == "ibis":
                dut = DutConfig(
                    type="ibis",
                    ibis=IbisDutConfig(
                        label=label,
                        ibis=self.vars["ibis"].get(),
                        component=self.vars["component"].get(),
                        model=self.vars["model"].get(),
                        corner=self.vars["corner"].get() or "Typical",
                    ),
                )
                detail = f"{dut.ibis.model} from {Path(dut.ibis.ibis).name}"
            else:
                dut = DutConfig(
                    type="spice",
                    spice=SpiceDutConfig(
                        label=label,
                        include=self.vars["spice_include"].get(),
                        subckt=self.vars["spice_subckt"].get(),
                        pin_order=self.vars["pin_order"].get(),
                    ),
                )
                detail = f"{dut.spice.subckt} from {Path(dut.spice.include).name}"
            self.duts.append(dut)
            self.dut_tree.insert("", "end", values=(dut.type, f"{label}: {detail}"))

        def clear_duts(self) -> None:
            self.duts.clear()
            for item in self.dut_tree.get_children():
                self.dut_tree.delete(item)

        def build_config(self) -> RunConfig:
            stop_value = self.vars["stop_ns"].get().strip()
            selected_view = self.vars["output_view"].get()
            run_view = "side_by_side" if selected_view == "transient_side_by_side" else "overlay"
            return RunConfig(
                ngspice=self.vars["ngspice"].get(),
                output_dir=self.vars["output_dir"].get(),
                vdd=float(self.vars["vdd"].get()),
                view=run_view,
                stimulus=StimulusConfig(
                    kind=self.vars["stim_kind"].get(),
                    v_low=0.0,
                    v_high=float(self.vars["vdd"].get()),
                    start_ns=float(self.vars["start_ns"].get()),
                    edge_ps=float(self.vars["edge_ps"].get()),
                    high_ns=float(self.vars["high_ns"].get()),
                    low_ns=float(self.vars["low_ns"].get()),
                    pulses=int(self.vars["pulses"].get()),
                    bit_rate_mbps=float(self.vars["bit_rate_mbps"].get()),
                    bit_pattern=self.vars["bit_pattern"].get(),
                    prbs_bits=int(self.vars["prbs_bits"].get()),
                    stop_ns=float(stop_value) if stop_value else None,
                ),
                termination=TerminationConfig(
                    r_ohm=float(self.vars["r_ohm"].get()),
                    v_term=float(self.vars["v_term"].get()),
                    channel=self.vars["channel"].get(),
                    tline_z0_ohm=float(self.vars["tline_z0_ohm"].get()),
                    tline_delay_ns=float(self.vars["tline_delay_ns"].get()),
                ),
                duts=list(self.duts),
            )

        def show_figure(self, fig: Figure) -> None:
            for child in self.plot_area.winfo_children():
                child.destroy()
            self.canvas = FigureCanvasTkAgg(fig, master=self.plot_area)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_area)
            self.toolbar.update()

        def show_schematic(self, fig: Figure) -> None:
            for child in self.schematic_area.winfo_children():
                child.destroy()
            self.schematic_canvas = FigureCanvasTkAgg(fig, master=self.schematic_area)
            self.schematic_canvas.draw()
            self.schematic_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.schematic_toolbar = NavigationToolbar2Tk(self.schematic_canvas, self.schematic_area)
            self.schematic_toolbar.update()

        def write_output_message(self, text: str) -> None:
            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, text)
            self.output_text.configure(state="disabled")

        def set_busy(self, busy: bool) -> None:
            self.root.configure(cursor="watch" if busy else "")

        def generate_diagram(self) -> None:
            try:
                config = self.build_config()
                out_dir = Path(config.output_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "plots").mkdir(exist_ok=True)
                runtimes = prepare_duts(config, out_dir)
                diagram_path = out_dir / "plots" / "testbench_schematic.png"
                fig = draw_testbench_schematic(config, runtimes, diagram_path)
                fig.savefig(diagram_path, dpi=180, bbox_inches="tight")
                self.show_schematic(fig)
                self.notebook.select(0)
                self.status.set(f"Generated schematic preview: {diagram_path}")
            except Exception as exc:
                messagebox.showerror("Schematic failed", str(exc))
                self.status.set("Schematic failed.")

        def run_sim(self) -> None:
            config = self.build_config()

            def work() -> None:
                try:
                    result = execute_run(config)
                except Exception as exc:
                    traceback.print_exc()
                    self.root.after(0, lambda: self.run_failed(exc))
                    return
                self.root.after(0, lambda: self.run_complete(result))

            try:
                self.status.set("Running ngspice...")
                self.set_busy(True)
                self.root.update_idletasks()
                threading.Thread(target=work, daemon=True).start()
            except Exception as exc:
                traceback.print_exc()
                messagebox.showerror("Run failed", str(exc))
                self.set_busy(False)
                self.status.set("Run failed.")

        def run_complete(self, result: SimulationResult) -> None:
            self.result = result
            self.set_busy(False)
            self.show_schematic(draw_testbench_schematic(result.config, result.dut_runtimes, result.diagram_path))
            self.vars["output_view"].set("transient_overlay")
            self.refresh_output_view()
            self.notebook.select(1)
            self.status.set(f"Run complete: {result.output_dir}")
            self.write_output_message(
                "Run complete.\n\n"
                f"Output folder:\n{result.output_dir}\n\n"
                f"Bench:\n{result.bench_path}\n\n"
                f"Raw:\n{result.raw_path}\n\n"
                f"Schematic:\n{result.diagram_path}"
            )

        def run_failed(self, exc: Exception) -> None:
            self.set_busy(False)
            messagebox.showerror("Run failed", str(exc))
            self.status.set("Run failed.")
            self.write_output_message(f"Run failed:\n{exc}")

        def refresh_output_view(self) -> None:
            view = self.vars["output_view"].get()
            if self.result is None:
                self.write_output_message("No completed simulation yet. Generate the setup schematic or run ngspice first.")
                return
            if view == "transient_side_by_side":
                fig = make_transient_figure(self.result, "side_by_side")
            else:
                fig = make_transient_figure(self.result, "overlay")
            self.show_figure(fig)

        def show_output_folder(self) -> None:
            path = Path(self.vars["output_dir"].get())
            if self.result is not None:
                path = self.result.output_dir
            if not path.exists():
                messagebox.showinfo("Output folder", f"Folder does not exist yet:\n{path}")
                return
            try:
                subprocess.Popen(["explorer", str(path)])
            except Exception as exc:
                messagebox.showerror("Open folder failed", str(exc))

        def save_config(self) -> None:
            try:
                path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
                if not path:
                    return
                config = self.build_config()
                Path(path).write_text(json.dumps(config_to_dict(config), indent=2), encoding="utf-8")
                self.status.set(f"Saved config: {path}")
            except Exception as exc:
                messagebox.showerror("Save failed", str(exc))

    tk_root = tk.Tk()
    App(tk_root)
    tk_root.mainloop()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ngspice CLI+GUI testbench tool for SPICE and pybis-converted IBIS buffers.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a simulation from JSON config or direct single-IBIS arguments")
    run.add_argument("--config", help="JSON config file")
    run.add_argument("--ngspice", default=str(DEFAULT_NGSPICE))
    run.add_argument("--output-dir")
    run.add_argument("--view", choices=["overlay", "side_by_side"], default="overlay")
    run.add_argument("--ibis")
    run.add_argument("--component")
    run.add_argument("--model")
    run.add_argument("--label")
    run.add_argument("--corner", default="Typical")
    run.add_argument("--vdd", type=float, default=1.2)
    run.add_argument("--r-ohm", type=float, default=50.0)
    run.add_argument("--v-term", type=float, default=0.0)
    run.add_argument("--channel", choices=["none", "ideal_tline"], default="none")
    run.add_argument("--tline-z0-ohm", type=float, default=50.0)
    run.add_argument("--tline-delay-ns", type=float, default=1.0)
    run.add_argument("--stimulus", choices=["pulse_train", "bit_pattern", "prbs7"], default="pulse_train")
    run.add_argument("--start-ns", type=float, default=10.0)
    run.add_argument("--edge-ps", type=float, default=5.0)
    run.add_argument("--high-ns", type=float, default=20.0)
    run.add_argument("--low-ns", type=float, default=20.0)
    run.add_argument("--pulses", type=int, default=5)
    run.add_argument("--bit-rate-mbps", type=float, default=50.0)
    run.add_argument("--bit-pattern", default="10101010")
    run.add_argument("--prbs-bits", type=int, default=64)
    run.add_argument("--stop-ns", type=float)

    gui = sub.add_parser("gui", help="Open the Tkinter GUI")
    gui.set_defaults(gui=True)

    ex = sub.add_parser("example-config", help="Write an example JSON config")
    ex.add_argument("path", nargs="?", default=str(ROOT / "results" / "ngspice_lab_example_config.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.command == "gui":
        gui_main()
        return 0
    if args.command == "example-config":
        path = Path(args.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config_to_dict(example_config()), indent=2), encoding="utf-8")
        print(f"Wrote example config: {path}")
        return 0
    if args.command == "run":
        if args.config:
            config = config_from_dict(json.loads(Path(args.config).read_text(encoding="utf-8")))
        else:
            config = parse_direct_ibis_args(args)
        result = execute_run(config)
        print(f"Run complete: {result.output_dir}")
        print(f"Bench: {result.bench_path}")
        print(f"Raw: {result.raw_path}")
        print(f"Schematic: {result.diagram_path}")
        for plot in result.plot_paths:
            print(f"Plot: {plot}")
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
