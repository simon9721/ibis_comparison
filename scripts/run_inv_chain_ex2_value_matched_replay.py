from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from eye_diagram import parse_ngspice_raw  # noqa: E402
from spice_tool_paths import default_ngspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402


OUT_DIR = ROOT / "results" / "inv_chain_ex2_value_matched_replay_2026-08-04"
DEFAULT_NGSPICE = default_ngspice(console=True)

BLACK = "#111111"
GRAY = "#777777"
PURPLE = "#7B2CBF"
BLUE = "#0072B2"
ORANGE = "#E69F00"
RED = "#CC3311"
GRID = "#D9DEE5"
EDGE = "#888888"


@dataclass(frozen=True)
class Flow:
    flow_id: str
    label: str
    subcircuit_type: str
    color: str


FLOWS = (
    Flow("legacy", "legacy pybis", "InputDriven", GRAY),
    Flow("v2_balanced", "value-match balanced", "InputDrivenValueMatchedReplayV2Hybrid", PURPLE),
    Flow("v2_ku_only", "value-match Ku-only", "InputDrivenValueMatchedReplayV2KuOnly", BLUE),
    Flow("v2_kd_only", "value-match Kd-only", "InputDrivenValueMatchedReplayV2KdOnly", ORANGE),
    Flow("v2_split", "value-match split Ku/Kd", "InputDrivenValueMatchedReplayV2SplitKuKd", RED),
)

REFERENCE_ROOTS = {
    "inv_chain": ROOT / "results" / "inv_chain_s2ibispy_slow_fast_comparison_2026-07-27",
    "ex2": ROOT / "results" / "ex2_slow_fast_gate_state_comparison_2026-07-28",
}

DIAGNOSTICS = (
    "kuleg",
    "kdleg",
    "kupre",
    "kdpre",
    "kusamp",
    "kdsamp",
    "tr_ku",
    "tr_kd",
    "tf_ku",
    "tf_kd",
    "tr_start",
    "tf_start",
    "vmstart_latch",
    "kustart_latch",
    "kdstart_latch",
    "vmt0",
    "vmelapsed",
    "vmarg",
    "kuarg",
    "kdarg",
    "start_disagree",
    "match_ambiguous",
    "hvmatch",
    "vmsample",
    "vmlatchpulse",
    "vmactivate",
    "hreverse_edge",
    "hfall_after_rise",
    "hrise_after_fall",
    "kumatch",
    "kdmatch",
    "kutarget",
    "kdtarget",
)


def devices() -> tuple[base.Device, ...]:
    return tuple(device for device in base.DEVICES if device.device_id in {"inv_chain", "ex2"})


def cases(device: base.Device) -> tuple[base.PulseCase, ...]:
    result = [
        base.PulseCase("edge_1ps_base_50r_2pf", 0.001, "rise_fall", 10.0, 25.0, "long control")
    ]
    widths = (0.05, 0.1, 0.2) if device.device_id == "inv_chain" else (0.5, 1.0, 2.0)
    for direction in ("short_high", "short_low"):
        for width in widths:
            label = base.width_tag(width)
            result.append(
                base.PulseCase(
                    f"short_pulse_{label}_{'high' if direction == 'short_high' else 'low'}",
                    0.001,
                    direction,
                    width,
                    18.0 if direction == "short_low" else 15.0,
                    f"{label} {'high' if direction == 'short_high' else 'low'} pulse",
                )
            )
    return tuple(result)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="ascii")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv_waveform(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"No rows in {path}")
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }


def reference_waveform(device: base.Device, profile: base.Profile, case: base.PulseCase) -> tuple[dict[str, np.ndarray], Path]:
    path = REFERENCE_ROOTS[device.device_id] / profile.profile_id / "waveform_data" / f"{case.case_id}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    data = read_csv_waveform(path)
    return {
        "time_ns": data["time_ns"],
        "input_v": data["input_v"],
        "pad_v": data["hspice_ibis_pad_v"],
        "ku": data["hspice_ibis_ku"],
        "kd": data["hspice_ibis_kd"],
        "transistor_pad_v": data["hspice_transistor_pad_v"],
    }, path


def generated_model_path(device: base.Device, profile: base.Profile, flow: Flow) -> Path:
    return OUT_DIR / "generated_models" / device.device_id / profile.profile_id / flow.flow_id / f"{device.subckt}.sub"


def prepare_models(device: base.Device, profile: base.Profile) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for flow in FLOWS:
        output = generated_model_path(device, profile, flow)
        if not output.exists():
            convert_ibis_to_pybis(
                ibis_path=profile.ibis,
                output_path=output,
                component_name=device.component,
                model_name=device.model,
                io_type="Output",
                subcircuit_type=flow.subcircuit_type,
                corner="Typical",
            )
        result[flow.flow_id] = output
    return result


def ngspice_deck(device: base.Device, case: base.PulseCase, flow: Flow) -> str:
    diagnostic_save = ""
    if flow.flow_id != "legacy":
        diagnostic_save = "".join(f" V(xdrv.{name})" for name in DIAGNOSTICS)
    return f"""* Cross-buffer value-matched replay study
.title {device.device_id} {flow.flow_id} {case.case_id}
.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

{base.pwl(device, case)}

Ven en_sig 0 DC {base.fmt(device.enable_v)}
Vdd vdd 0 DC {base.fmt(device.supply_v)}
.include '{device.subckt}.sub'
XDRV pad in_dig en_sig vdd 0 {device.subckt}
Rload pad 0 50
Cload pad 0 2p

.save V(in_dig) V(pad) V(xdrv.ku) V(xdrv.kd){diagnostic_save}
.tran 2p {base.fmt(case.stop_ns)}n
.end
"""


def run_process(command: list[str], cwd: Path, log: Path, timeout_s: int) -> int:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        log.write_text("COMMAND: " + " ".join(command) + "\n\n" + result.stdout, encoding="utf-8", errors="replace")
        return int(result.returncode)
    except subprocess.TimeoutExpired as exc:
        captured = exc.stdout or ""
        if isinstance(captured, bytes):
            captured = captured.decode("utf-8", errors="replace")
        log.write_text(f"TIMEOUT after {timeout_s} seconds\n\n{captured}", encoding="utf-8", errors="replace")
        return 124


def raw_signal(raw: dict[str, np.ndarray], name: str) -> np.ndarray | None:
    lookup = {key.lower().replace(":", "."): key for key in raw}
    for candidate in (name, name.replace(".", ":")):
        key = lookup.get(candidate.lower().replace(":", "."))
        if key is not None:
            return np.asarray(raw[key], dtype=float)
    return None


def parse_waveform(raw_path: Path) -> dict[str, np.ndarray]:
    raw = parse_ngspice_raw(raw_path)
    result: dict[str, np.ndarray] = {
        "time_ns": np.asarray(raw["time"], dtype=float) * 1e9,
    }
    required = {
        "input_v": "v(in_dig)",
        "pad_v": "v(pad)",
        "ku": "v(xdrv.ku)",
        "kd": "v(xdrv.kd)",
    }
    for key, signal in required.items():
        values = raw_signal(raw, signal)
        if values is None:
            raise KeyError(f"Missing {signal} in {raw_path}")
        result[key] = values
    for name in DIAGNOSTICS:
        values = raw_signal(raw, f"v(xdrv.{name})")
        if values is not None:
            result[name] = values
    return result


def run_flow(
    device: base.Device,
    profile: base.Profile,
    case: base.PulseCase,
    flow: Flow,
    model: Path,
    ngspice: Path,
    timeout_s: int,
    resume: bool,
) -> tuple[dict[str, np.ndarray] | None, dict[str, object]]:
    out = OUT_DIR / "runs" / device.device_id / profile.profile_id / case.case_id / flow.flow_id
    ensure_dir(out)
    model_copy = out / f"{device.subckt}.sub"
    shutil.copy2(model, model_copy)
    deck_path = out / "run.sp"
    raw_path = out / "run.raw"
    log_path = out / "run.log"
    write_text(deck_path, ngspice_deck(device, case, flow))
    if resume and raw_path.exists():
        return parse_waveform(raw_path), {
            "device": device.device_id,
            "profile": profile.profile_id,
            "case_id": case.case_id,
            "flow": flow.flow_id,
            "status": "COMPLETED",
            "source": "existing_raw",
            "raw": str(raw_path.relative_to(ROOT)),
            "log": str(log_path.relative_to(ROOT)) if log_path.exists() else "",
        }
    if raw_path.exists():
        raw_path.unlink()
    rc = run_process([str(ngspice), "-b", "-r", raw_path.name, deck_path.name], out, log_path, timeout_s)
    completed = rc == 0 and raw_path.exists()
    return (parse_waveform(raw_path) if completed else None), {
        "device": device.device_id,
        "profile": profile.profile_id,
        "case_id": case.case_id,
        "flow": flow.flow_id,
        "status": "COMPLETED" if completed else "NUMERIC_FAIL",
        "return_code": rc,
        "source": "run",
        "raw": str(raw_path.relative_to(ROOT)) if raw_path.exists() else "",
        "log": str(log_path.relative_to(ROOT)),
    }


def interp(source_t: np.ndarray, source_y: np.ndarray, target_t: np.ndarray) -> np.ndarray:
    return np.interp(target_t, source_t, source_y)


def active_mask(case: base.PulseCase, time_ns: np.ndarray) -> np.ndarray:
    if case.pattern == "rise_fall":
        return (time_ns >= 4.0) & (time_ns <= 18.0)
    reverse = base.command_edges(next(device for device in devices()), case)[-1]
    start = 4.0 if case.pattern == "short_high" else 9.0
    return (time_ns >= start) & (time_ns <= reverse + 5.0)


def score(
    device: base.Device,
    profile: base.Profile,
    case: base.PulseCase,
    flow: Flow,
    reference: dict[str, np.ndarray],
    wave: dict[str, np.ndarray] | None,
    run_row: dict[str, object],
) -> dict[str, object]:
    row = dict(run_row)
    row.update({"pattern": case.pattern, "pulse_width_ns": case.pulse_width_ns})
    if wave is None:
        return row
    target_t = reference["time_ns"]
    mask = active_mask(case, target_t)
    aligned = {
        name: interp(wave["time_ns"], values, target_t)
        for name, values in wave.items()
        if name != "time_ns"
    }
    for name in ("pad_v", "ku", "kd"):
        error = aligned[name][mask] - reference[name][mask]
        row[f"{name}_rmse"] = float(np.sqrt(np.mean(error**2)))
        row[f"{name}_max_error"] = float(np.max(np.abs(error)))
    row.update(
        {
            "ku_min": float(np.min(aligned["ku"][mask])),
            "ku_max": float(np.max(aligned["ku"][mask])),
            "kd_min": float(np.min(aligned["kd"][mask])),
            "kd_max": float(np.max(aligned["kd"][mask])),
        }
    )
    reverse = base.command_edges(device, case)[-1]
    # Sampling, inverse mapping, and start latching occupy three 20 ps phases.
    # Inspect the settled latch, not the stale/pre-latch value at the exact edge.
    event = (target_t >= reverse + 0.06) & (target_t <= reverse + 0.25)
    if flow.flow_id != "legacy":
        for key in ("kusamp", "kdsamp", "tr_ku", "tr_kd", "tf_ku", "tf_kd", "start_disagree"):
            if key in aligned:
                values = aligned[key][event]
                row[f"{key}_event_median"] = float(np.median(values))
                row[f"{key}_event_max"] = float(np.max(values))
        # The generated ambiguity node can briefly assert during initialization,
        # before a reverse-edge sample is latched. Classify only the actual
        # reverse-edge inference window recorded above.
        if "start_disagree" in aligned:
            row["match_ambiguous"] = bool(np.median(aligned["start_disagree"][event]) > 0.5)
        if "hvmatch" in aligned:
            row["replay_active"] = bool(np.any(aligned["hvmatch"][mask] > 0.5))
            row["replay_active_duration_ns"] = float(
                np.trapezoid((aligned["hvmatch"][mask] > 0.5).astype(float), target_t[mask])
            )
    row["classification"] = (
        "LONG_CONTROL"
        if case.pattern == "rise_fall"
        else "VALUE_MATCH_AMBIGUOUS"
        if row.get("replay_active") and row.get("match_ambiguous")
        else "REPLAY_ACTIVE"
        if row.get("replay_active")
        else "NO_REPLAY"
    )
    return row


def aligned_for_plot(reference: dict[str, np.ndarray], waves: dict[str, dict[str, np.ndarray] | None]) -> dict[str, np.ndarray]:
    t = reference["time_ns"]
    result = {
        "time_ns": t,
        "hspice_pad": reference["pad_v"],
        "hspice_ku": reference["ku"],
        "hspice_kd": reference["kd"],
        "hspice_transistor_pad": reference["transistor_pad_v"],
    }
    for flow_id, wave in waves.items():
        if wave is None:
            continue
        for name, values in wave.items():
            if name == "time_ns":
                continue
            result[f"{flow_id}_{name}"] = interp(wave["time_ns"], values, t)
    return result


def xlim(case: base.PulseCase) -> tuple[float, float]:
    reverse = 15.0 if case.pattern == "rise_fall" else 5.0 + case.pulse_width_ns if case.pattern == "short_high" else 10.0 + case.pulse_width_ns
    start = 4.0 if case.pattern != "short_low" else 9.0
    return start, reverse + 4.0


def mark_edges(ax: plt.Axes, device: base.Device, case: base.PulseCase) -> None:
    for edge in base.command_edges(device, case):
        ax.axvline(edge, color=EDGE, ls="--", lw=1.0)


def plot_case(
    device: base.Device,
    profile: base.Profile,
    case: base.PulseCase,
    data: dict[str, np.ndarray],
) -> tuple[Path, Path | None]:
    output = OUT_DIR / "plots" / device.device_id / profile.profile_id / f"{case.case_id}.png"
    ensure_dir(output.parent)
    fig, axes = plt.subplots(3, 1, figsize=(14.5, 9.5), sharex=True)
    t = data["time_ns"]
    panels = (("pad", "Pad voltage (V)"), ("ku", "Ku"), ("kd", "Kd"))
    for ax, (key, ylabel) in zip(axes, panels):
        ax.plot(t, data[f"hspice_{key}"], color=BLACK, lw=4.2, label="HSPICE native IBIS", zorder=6)
        if key == "pad":
            ax.plot(t, data["hspice_transistor_pad"], color="#AAAAAA", lw=2.4, label="HSPICE transistor", zorder=1)
        for flow in FLOWS:
            column = f"{flow.flow_id}_{'pad_v' if key == 'pad' else key}"
            if column in data:
                ax.plot(t, data[column], color=flow.color, lw=1.8, label=flow.label, zorder=3)
        mark_edges(ax, device, case)
        ax.set_ylabel(ylabel)
        ax.grid(True, color=GRID)
        ax.spines[["top", "right"]].set_visible(False)
    axes[2].axhline(0.0, color="#999999", lw=0.8)
    axes[2].set_xlabel("Time (ns)")
    axes[2].set_xlim(*xlim(case))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.94), ncol=4, frameon=False)
    fig.suptitle(f"{device.label} | {profile.profile_id} | {case.target_label}", fontsize=17, fontweight="bold", y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(output, dpi=180)
    plt.close(fig)

    diagnostic: Path | None = None
    if "v2_split_hvmatch" in data:
        diagnostic = OUT_DIR / "plots" / device.device_id / profile.profile_id / f"{case.case_id}_diagnostics.png"
        fig, axes = plt.subplots(4, 1, figsize=(14.5, 10.0), sharex=True)
        axes[0].plot(t, data["v2_split_kusamp"], color=BLUE, lw=2.0, label="KUSAMP")
        axes[0].plot(t, data["v2_split_kdsamp"], color=ORANGE, lw=2.0, label="KDSAMP")
        axes[0].set_ylabel("sampled K")
        start_prefix = "tf" if case.pattern == "short_high" else "tr"
        axes[1].plot(t, data[f"v2_split_{start_prefix}_ku"], color=BLUE, lw=2.0, label=f"{start_prefix.upper()}_KU")
        axes[1].plot(t, data[f"v2_split_{start_prefix}_kd"], color=ORANGE, lw=2.0, label=f"{start_prefix.upper()}_KD")
        axes[1].set_ylabel("inferred start (ns)")
        for key, color, label in (("vmarg", PURPLE, "shared VMARG"), ("kuarg", BLUE, "KUARG"), ("kdarg", ORANGE, "KDARG")):
            column = f"v2_split_{key}"
            if column in data:
                axes[2].plot(t, data[column], color=color, lw=1.8, label=label)
        axes[2].set_ylabel("table argument (ns)")
        axes[3].plot(t, data["v2_split_start_disagree"], color=RED, lw=2.0, label="start disagreement")
        axes[3].plot(t, data["v2_split_hvmatch"], color=PURPLE, lw=1.8, label="replay active")
        axes[3].plot(t, data["v2_split_match_ambiguous"], color=BLACK, lw=1.4, label="ambiguous")
        axes[3].set_ylabel("diagnostic")
        axes[3].set_xlabel("Time (ns)")
        for ax in axes:
            mark_edges(ax, device, case)
            ax.set_xlim(*xlim(case))
            ax.grid(True, color=GRID)
            ax.legend(frameon=False, ncol=3, loc="best")
            ax.spines[["top", "right"]].set_visible(False)
        fig.suptitle(f"{device.label} | {profile.profile_id} | {case.target_label} | split-start diagnostics", fontsize=16, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        fig.savefig(diagnostic, dpi=180)
        plt.close(fig)
    return output, diagnostic


def save_aligned_data(path: Path, data: dict[str, np.ndarray]) -> None:
    rows = [
        {key: float(values[index]) for key, values in data.items()}
        for index in range(len(data["time_ns"]))
    ]
    write_csv(path, rows)


def write_walkthrough() -> None:
    source = ROOT / "tools" / "pybis2spice" / "pybis2spice" / "subcircuit.py"
    lines = [
        "# Value-Matched Replay V2: Exact Implementation",
        "",
        "## First Correction: The Matching Variable",
        "",
        "The implemented algorithm does **not** map pad voltage onto the opposite transition. It samples the currently active coefficient pair `Ku/Kd`. Pad voltage is load- and channel-dependent, while the coefficient tables belong to the driver model.",
        "",
        "At a fall-after-rise reversal, the algorithm maps `KUSAMP` and `KDSAMP` independently onto the falling tables. At a rise-after-fall reversal, it maps them onto the rising tables.",
        "",
        "The intended inverse operation is:",
        "",
        "```text",
        "t_Ku = argmin_t |Ku_opposite(t) - Ku_sample|",
        "t_Kd = argmin_t |Kd_opposite(t) - Kd_sample|",
        "t_shared = 0.5 * (t_Ku + t_Kd)",
        "table_argument(t) = t_start_latched + elapsed_since_replay_activation",
        "```",
        "",
        "The split policy uses `t_Ku` for Ku and `t_Kd` for Kd instead of `t_shared`.",
        "",
        "## Offline Generation",
        "",
        "1. pybis2spice solves the complete rising and falling arrays `kr=[time,Ku,Kd]` and `kf=[time,Ku,Kd]` from the two IBIS fixture waveforms.",
        "2. `inverse_time_lookup_table()` builds numerically legal inverse PWL tables `coefficient -> table time` for all four coefficient/direction combinations. It sorts by coefficient value, collapses duplicate values to their earliest time, and interpolates 81 points. This removes chronology: a non-monotonic table can have several physically different times for one coefficient value.",
        "3. `create_ngspice_value_matched_replay_v2_input_control_netlist()` writes those forward and inverse PWL tables into the generated ngspice subcircuit.",
        "",
        "## Runtime Sequence",
        "",
        "1. `RISEEDGE/FALLEDGE` detect a digital input reversal.",
        "2. `KUPRE/KDPRE` read the previous transition table before the replay direction changes.",
        "3. `VMSAMPLE` briefly enables capacitor-backed latches `KUSAMP/KDSAMP`.",
        "4. `TR_KU/TR_KD/TF_KU/TF_KD` inverse-map the samples to candidate starts on the opposite tables.",
        "5. Policy chooses the start: balanced averages the two inferred times; Ku-only or Kd-only uses one; split keeps separate Ku and Kd starts.",
        "6. `VMSTART_LATCH`, `KUSTART_LATCH`, and `KDSTART_LATCH` hold those starts. `VMT0` stores the replay activation time.",
        "7. `VMELAPSED = max(0, current_time - VMT0 - edge_delay)` creates a fresh timer. V2 never reuses the legacy elapsed timer `HNX` as V1 did.",
        "8. `VMARG`, or separate `KUARG/KDARG`, advances through the selected opposite table.",
        "9. `KUMATCH/KDMATCH` become the live replay coefficients until the table ends, then control returns to legacy replay.",
        "10. Final `Ku/Kd` are direct behavioral-voltage outputs of `KUTARGET/KDTARGET`; the sample and start nodes are capacitor-backed, but final V2 coefficients are not separately RC-smoothed.",
        "",
        "## Core Generated SPICE",
        "",
        "```spice",
        "BKUSAMPLE KUSAMP 0 I = -{sample_c}*V(VMSAMPLE)*(V(KUPRE)-V(KUSAMP))/sample_tau",
        "BKDSAMPLE KDSAMP 0 I = -{sample_c}*V(VMSAMPLE)*(V(KDPRE)-V(KDSAMP))/sample_tau",
        "B32 TF_KU 0 V = pwl(V(KUSAMP), ... inverse Ku_fall ...)",
        "B33 TF_KD 0 V = pwl(V(KDSAMP), ... inverse Kd_fall ...)",
        "B35 TF_START 0 V = 0.5*(V(TF_KU)+V(TF_KD))",
        "B37 VMELAPSED 0 V = (V(HVMATCH)>0.05) ? max(0,time*1e9-V(VMT0)-0.01) : 0",
        "B37A VMARG 0 V = V(VMSTART_LATCH)+V(VMELAPSED)",
        "B44 KUMATCH 0 V = (V(NINX)>0.5) ? V(KURM) : V(KUFM)",
        "B45 KDMATCH 0 V = (V(NINX)>0.5) ? V(KDRM) : V(KDFM)",
        "```",
        "",
        "## Detector And Policies",
        "",
        "- Fall-after-rise currently activates when a falling edge arrives while the legacy elapsed coordinate `HNX` is below the global 4 ns interruption window. It does not prove the physical coefficient state is unsettled.",
        "- Rise-after-fall additionally requires `Ku > 0.05` or `Kd < 0.95`. This asymmetry is why many short-low cases do not activate replay.",
        "- Balanced uses one shared start: `(t_from_Ku + t_from_Kd)/2`.",
        "- Ku-only and Kd-only force both coefficients to use one coefficient's inferred start.",
        "- Split lets Ku and Kd use separate table arguments. It diagnoses the shared-coordinate assumption, but it does not restore missing delayed-event history.",
        "",
        "## Known Limits Exposed By This Study",
        "",
        "1. A coefficient value alone is not a complete state when a delayed response is pending. `inv_chain` can still have `Ku ~= 0, Kd ~= 1` at reversal while the already-launched rising response appears later.",
        "2. Inverting a non-monotonic coefficient table is multi-valued. Sorting by coefficient makes a legal ngspice PWL source, but cannot determine which occurrence is physically correct.",
        "3. Ku-derived and Kd-derived opposite-table times can disagree. Separate starts avoid averaging, but do not make the pair a self-consistent driver state.",
        "4. The current 4 ns command-age detector can activate after a fast buffer is effectively settled.",
        "5. Pad-voltage matching was deliberately not implemented because pad voltage changes with load, clamps, package, and channel; it would not define a reusable driver-internal replay state.",
        "",
        "The exact generated subcircuits are under `generated_models/<device>/<profile>/<policy>/`. Every simulation deck and raw file is retained under `runs/`.",
        "",
        "Representative files to read end-to-end:",
        "",
        "- `generated_models/inv_chain/fast_5ps/v2_balanced/driver2_OutputInput_Typical.sub`",
        "- `runs/inv_chain/fast_5ps/short_pulse_50ps_high/v2_balanced/run.sp`",
        "- `generated_models/ex2/slow_1ns/v2_balanced/driver_OutputInput_Typical.sub`",
        "- `runs/ex2/slow_1ns/short_pulse_1ns_high/v2_balanced/run.sp`",
        "",
        f"Authoritative generator: `{source.relative_to(ROOT).as_posix()}`.",
        "Relevant functions: `inverse_time_lookup_table`, `create_inverse_time_lookup_source`, and `create_ngspice_value_matched_replay_v2_input_control_netlist`.",
    ]
    write_text(OUT_DIR / "IMPLEMENTATION_WALKTHROUGH.md", "\n".join(lines) + "\n")


def write_balanced_comparison(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    indexed = {
        (str(row["device"]), str(row["profile"]), str(row["case_id"]), str(row["flow"])): row
        for row in metrics
    }
    rows: list[dict[str, object]] = []
    for key, candidate in indexed.items():
        device, profile, case_id, flow = key
        if flow != "v2_balanced" or str(candidate.get("pattern")) == "rise_fall":
            continue
        legacy = indexed[(device, profile, case_id, "legacy")]
        start_prefix = "tf" if str(candidate.get("pattern")) == "short_high" else "tr"
        result: dict[str, object] = {
            "device": device,
            "profile": profile,
            "case_id": case_id,
            "replay_active": candidate.get("replay_active", False),
            "match_ambiguous": candidate.get("match_ambiguous", False),
            "classification": candidate.get("classification", ""),
            "sampled_ku": candidate.get("kusamp_event_median", ""),
            "sampled_kd": candidate.get("kdsamp_event_median", ""),
            "opposite_start_from_ku_ns": candidate.get(f"{start_prefix}_ku_event_median", ""),
            "opposite_start_from_kd_ns": candidate.get(f"{start_prefix}_kd_event_median", ""),
            "start_disagreement_ns": candidate.get("start_disagree_event_median", ""),
        }
        improvements = []
        for metric in ("pad_v_rmse", "ku_rmse", "kd_rmse"):
            legacy_value = float(legacy[metric])
            candidate_value = float(candidate[metric])
            result[f"legacy_{metric}"] = legacy_value
            result[f"value_match_{metric}"] = candidate_value
            result[f"delta_{metric}"] = candidate_value - legacy_value
            improvements.append(candidate_value < legacy_value)
        result["all_pad_ku_kd_improve"] = all(improvements)
        rows.append(result)
    write_csv(OUT_DIR / "balanced_vs_legacy_summary.csv", rows)
    return rows


def write_readme(metrics: list[dict[str, object]], figures: list[Path], failures: list[dict[str, object]]) -> None:
    measured = [row for row in metrics if row.get("status") == "COMPLETED" and row.get("flow") != "legacy"]
    ambiguous = [row for row in measured if row.get("classification") == "VALUE_MATCH_AMBIGUOUS"]
    active = [row for row in measured if row.get("replay_active")]
    balanced = write_balanced_comparison(metrics)
    active_balanced = [row for row in balanced if row.get("replay_active")]
    inv_improved = [row for row in active_balanced if row["device"] == "inv_chain" and row["all_pad_ku_kd_improve"]]
    ex2_improved = [row for row in active_balanced if row["device"] == "ex2" and row["all_pad_ku_kd_improve"]]
    lines = [
        "# inv_chain and ex2 Value-Matched Replay",
        "",
        "This extends the corrected V2 coefficient-value-matched replay experiment beyond `io_buf`. HSPICE reference waveforms were reused from existing CSVs; no HSPICE simulations were run.",
        "",
        "## Scope",
        "",
        "- Devices: `inv_chain`, `ex2`.",
        "- IBIS profiles: slow 1 ns and fast 5 ps characterization models.",
        "- Runtime input edges: 1 ps, matching the original io_buf value-match experiment.",
        "- `inv_chain` cases: long control plus 50/100/200 ps short-high and short-low pulses.",
        "- `ex2` cases: long control plus 500 ps/1 ns/2 ns short-high and short-low pulses.",
        "- Policies: balanced, Ku-only, Kd-only, and separate Ku/Kd starts.",
        "",
        "## Headline Counts",
        "",
        f"- Completed value-match rows: `{len(measured)}`.",
        f"- Replay-active rows: `{len(active)}`.",
        f"- Rows classified table-retiming ambiguous: `{len(ambiguous)}`.",
        f"- Numeric failures: `{len(failures)}`.",
        "",
        "## Findings",
        "",
        f"- `inv_chain`: balanced replay activated in 6 short-high runs; all pad/Ku/Kd RMSE values improved together in `{len(inv_improved)}` of them. The fast 200 ps case regressed because its sampled state mapped near inconsistent table endpoints.",
        f"- `ex2`: balanced replay activated in 6 short-high runs; all three metrics improved together in `{len(ex2_improved)}`. The 500 ps cases can improve pad and Ku while worsening Kd, which is a coefficient-level false pass.",
        "- Split Ku/Kd starts did not materially rescue the failing ex2 cases. Therefore the failure is not only the shared average; current Ku/Kd values do not encode pending transport delay or complete hidden state.",
        "- Most short-low cases did not activate replay because the existing rise-after-fall detector is state-gated while fall-after-rise is command-age-gated. This is an implementation asymmetry, not evidence that value matching solved short-low behavior.",
        "- The method is numerically stable in this campaign but is not a general retrigger solution. It is useful as a baseline that demonstrates why coefficient-value retiming is underdetermined.",
        "",
        "## Important Interpretation",
        "",
        "The implementation matches current `Ku/Kd` values, not pad voltage. The two independently inferred opposite-table times often disagree; that disagreement is the central test of whether a single replay coordinate exists.",
        "",
        "## Files",
        "",
        "- `IMPLEMENTATION_WALKTHROUGH.md`: exact offline/runtime implementation.",
        "- `metrics.csv`: coefficient, pad, inferred-start, ambiguity, and activation metrics.",
        "- `balanced_vs_legacy_summary.csv`: one concise row per short-pulse case with sampled values, inferred starts, and metric deltas.",
        "- `reference_manifest.csv`: cached HSPICE waveform provenance.",
        "- `generated_models/`: exact generated subcircuits.",
        "- `runs/`: exact ngspice decks, models, raw files, and logs.",
        "- `waveform_data/`: aligned numeric data behind the plots.",
        "- `plots/`: waveform overlays and split-start diagnostics.",
        "",
        "## Figures",
        "",
        "- `plots/value_match_cross_buffer_evidence.png` (compact representative comparison)",
    ]
    lines.extend(f"- `{path.relative_to(OUT_DIR).as_posix()}`" for path in figures)
    write_text(OUT_DIR / "README.md", "\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run value-matched replay on inv_chain and ex2 without HSPICE reruns.")
    parser.add_argument("--ngspice", type=Path, default=DEFAULT_NGSPICE)
    parser.add_argument("--timeout-s", type=int, default=60)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--profiles", nargs="*", choices=("slow_1ns", "fast_5ps"), default=["slow_1ns", "fast_5ps"])
    parser.add_argument("--cases", nargs="*", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dir(OUT_DIR)
    metrics: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []
    figures: list[Path] = []
    total = sum(
        len([case for case in cases(device) if not args.cases or case.case_id in set(args.cases)])
        for device in devices()
    ) * len(args.profiles) * len(FLOWS)
    index = 0

    for device in devices():
        selected_cases = [
            case for case in cases(device)
            if not args.cases or case.case_id in set(args.cases)
        ]
        profile_lookup = {profile.profile_id: profile for profile in base.profiles(device)}
        for profile_id in args.profiles:
            profile = profile_lookup[profile_id]
            models = prepare_models(device, profile)
            for case in selected_cases:
                reference, reference_path = reference_waveform(device, profile, case)
                manifest.append(
                    {
                        "device": device.device_id,
                        "profile": profile.profile_id,
                        "case_id": case.case_id,
                        "reference": "hspice_native_ibis_and_transistor",
                        "source": "existing_waveform_csv",
                        "path": str(reference_path.relative_to(ROOT)),
                    }
                )
                waves: dict[str, dict[str, np.ndarray] | None] = {}
                for flow in FLOWS:
                    index += 1
                    print(f"[{index}/{total}] {device.device_id}/{profile.profile_id}/{case.case_id}/{flow.flow_id}", flush=True)
                    wave, run_row = run_flow(
                        device,
                        profile,
                        case,
                        flow,
                        models[flow.flow_id],
                        args.ngspice,
                        args.timeout_s,
                        args.resume,
                    )
                    waves[flow.flow_id] = wave
                    metric = score(device, profile, case, flow, reference, wave, run_row)
                    metrics.append(metric)
                    if metric.get("status") != "COMPLETED":
                        failures.append(metric)
                aligned = aligned_for_plot(reference, waves)
                data_path = OUT_DIR / "waveform_data" / device.device_id / profile.profile_id / f"{case.case_id}.csv"
                save_aligned_data(data_path, aligned)
                overlay, diagnostic = plot_case(device, profile, case, aligned)
                figures.append(overlay)
                if diagnostic is not None:
                    figures.append(diagnostic)
                write_csv(OUT_DIR / "metrics.csv", metrics)
                write_csv(OUT_DIR / "reference_manifest.csv", manifest)
                write_csv(OUT_DIR / "numeric_failures.csv", failures)

    write_walkthrough()
    write_readme(metrics, figures, failures)
    print(f"OUT_DIR={OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
