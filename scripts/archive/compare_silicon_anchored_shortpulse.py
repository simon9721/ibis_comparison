#!/usr/bin/env python3
"""Compare pybis against silicon at pulse widths that actually stress silicon.

Every stress sweep so far chose pulse widths by watching either the transistor's
pad or native IBIS. Anchoring on native IBIS turned out to guarantee the wrong
regime on two of three buffers: native IBIS over-responds on `inv_chain` and
`ex2`, so asking for 50% of *its* swing picks a pulse far shorter than the real
transistor can react to. Four of six buffer/direction combinations were tested
at widths where silicon does nothing at all:

    inv_chain short-high   tested  50- 97 ps, silicon responds from  284 ps
    inv_chain short-low    tested  86-111 ps, silicon responds from  318 ps
    ex2       short-high   tested 576-740 ps, silicon responds from  904 ps
    ex2       short-low    tested 441-642 ps, silicon responds from  904 ps

Both models then invent a response silicon never produces, which says more about
the stimulus than about either model.

This anchors on silicon instead. Widths are taken from the measured depth sweep
so that the transistor's own coefficient reaches a chosen fraction of its travel
at the reverse edge, making all six combinations informative.

Set `PYBIS_GATE_MODE` to compare model variants at identical stimuli; with
`--width-ps` that gives a controlled A/B, which matters because an earlier
attempt changed the width selection and the model together and could attribute
the difference to neither.

The deliverable is waveform evidence, not a summary statistic. Every scalar
recovery metric attempted so far has been defeated by either the command still
in flight after the reverse edge or the brief ill-conditioning spike at the
input edge, so the shapes are what should be read.
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPS = ROOT / ".codex_deps" / "presentation" / "python"
for path in (LOCAL_DEPS, ROOT, ROOT / "scripts", ROOT / "tools" / "pybis2spice"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from pybis2spice import pybis2spice  # noqa: E402
from convert_ibis_to_pybis import convert as convert_ibis_to_pybis  # noqa: E402
from spice_tool_paths import default_hspice, default_ngspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
import run_three_buffer_pad_matched_replay as pad  # noqa: E402
from extract_silicon_kukd import run_fixture, solve_silicon_kukd  # noqa: E402

DEPTH_SWEEP = ROOT / "results" / "silicon_recovery_depth_sweep_2026-08-19" / "depth_vs_recovery.csv"
DEFAULT_OUT = ROOT / "results" / "silicon_anchored_shortpulse_2026-08-19"
GATE_STATE_MODE = os.environ.get("PYBIS_GATE_MODE", "InputDrivenTwoStateGateDirectionalDualResidualFull")
LOAD = (50.0, 2.0)
DEPTH_TARGETS = (0.25, 0.50, 0.75)
# Pad-matched replay indexes its coefficients off a recorded pad trajectory, so
# the reference has to be measured and baked into the subcircuit before the
# model can be built at all. Every other mode is a pure function of the IBIS
# file and needs none of this.
NEEDS_PAD_REFERENCE = "PadMatchedReplay" in GATE_STATE_MODE

SILICON = "#111111"
NATIVE = "#2b6ca3"
MODEL = "#c02626"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def widths_for_depths(device_id: str, direction: str) -> list[tuple[float, float]]:
    """Picks measured pulse widths whose silicon depth is closest to each target.

    Interpolation is not safe here. The depth-versus-width curve rises steeply
    and then saturates, and on `io_buf` short-low it is not even monotonic --
    depth hovers between 0.60 and 0.84 across widths from 491 to 2900 ps.
    Interpolating across that produced widths that went *down* as the requested
    depth went up. Selecting the nearest measured point instead cannot invent a
    width the device never showed, and the achieved depth is reported rather
    than the requested one.
    """
    points = [
        (float(r["pulse_width_ps"]), float(r["depth_at_reversal"]))
        for r in read_csv(DEPTH_SWEEP)
        if r["device"] == device_id and r["direction"] == direction
        and 0.0 <= float(r["depth_at_reversal"]) <= 1.05
    ]
    if not points:
        return []
    out: list[tuple[float, float]] = []
    for target in DEPTH_TARGETS:
        width, depth = min(points, key=lambda p: (abs(p[1] - target), p[0]))
        if abs(depth - target) > 0.20:
            continue
        if any(abs(width - chosen) < 1e-6 for _, chosen in out):
            continue
        out.append((depth, width))
    return out


def coefficient_for(direction: str) -> str:
    return "kd" if direction == "short_high" else "ku"


def plot_case(path: Path, title: str, t: np.ndarray, t_rev: float, edge_ns: float,
              series: dict[str, tuple[str, float, dict[str, np.ndarray]]]) -> None:
    window = (t >= edge_ns - 0.15) & (t <= t_rev + 3.5)
    if window.sum() < 8:
        window = np.ones_like(t, dtype=bool)
    fig, axes = plt.subplots(3, 1, figsize=(11.0, 9.2), sharex=True)
    panels = (("ku", "Ku"), ("kd", "Kd"), ("pad", "Pad voltage (V)"))
    for axis, (key, label) in zip(axes, panels):
        stacked = []
        for name, (colour, width, data) in series.items():
            if key not in data:
                continue
            axis.plot(t[window], data[key][window], color=colour, lw=width, label=name, zorder=3)
            stacked.append(data[key][window])
        axis.axvline(t_rev, color="0.45", ls="--", lw=1.1, zorder=1)
        if key != "pad":
            axis.axhspan(-0.05, 1.05, color="0.93", zorder=0)
        if stacked:
            # Set the view from the bulk: the two-fixture solve spikes briefly
            # at the input edge and would otherwise flatten every real feature.
            finite = np.concatenate(stacked)
            finite = finite[np.isfinite(finite)]
            if len(finite):
                low, high = np.percentile(finite, [0.5, 99.5])
                pad_y = max(0.10, 0.10 * (high - low))
                axis.set_ylim(low - pad_y, high + pad_y)
        axis.set_ylabel(label)
        axis.grid(alpha=0.25, zorder=0)
    axes[0].set_title(title, fontsize=11)
    axes[0].legend(fontsize=9, ncol=3, loc="best")
    axes[2].set_xlabel("Time (ns)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    parser.add_argument("--hspice-timeout", type=int, default=300)
    parser.add_argument("--ngspice-timeout", type=int, default=240)
    parser.add_argument("--device", action="append",
                        choices=[d.device_id for d in base.DEVICES])
    parser.add_argument("--direction", action="append",
                        choices=["short_high", "short_low"])
    parser.add_argument("--width-ps", action="append", type=float,
                        help="override width selection with explicit pulse widths, so a "
                             "model change can be A/B tested at identical stimuli")
    args = parser.parse_args()

    devices = set(args.device or [d.device_id for d in base.DEVICES])
    directions = args.direction or ["short_high", "short_low"]
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, object]] = []
    for device in base.DEVICES:
        if device.device_id not in devices:
            continue
        profile = base.Profile("fast_5ps", "fast-edge IBIS", device.fast_ibis)
        ibis_data = pybis2spice.DataModel(
            pybis2spice.get_ibis_model_ecdtools(str(device.fast_ibis)),
            model_name=device.model, component_name=device.component,
        )
        model_path = out / "generated_models" / device.device_id / f"{device.subckt}.sub"
        if not model_path.exists():
            reference = None
            if NEEDS_PAD_REFERENCE:
                # The reference is a clean full-edge pad trajectory from legacy
                # pybis at the nominal load, which is what the replay maps
                # against. It comes from the model, not from silicon: the method
                # is about reusing a known edge shape, not about importing truth.
                pad.OUT = out
                legacy = out / "generated_models" / device.device_id / "legacy" / f"{device.subckt}.sub"
                if not legacy.exists():
                    convert_ibis_to_pybis(device.fast_ibis, legacy, device.component,
                                          device.model, "Output", "InputDriven", "Typical")
                reference, _ = pad.build_pad_reference(device, profile, legacy, args.ngspice,
                                                       args.ngspice_timeout, resume=True)
            convert_ibis_to_pybis(device.fast_ibis, model_path, device.component,
                                  device.model, "Output", GATE_STATE_MODE, "Typical",
                                  pad_replay_reference=reference)

        for direction in directions:
            if args.width_ps:
                targets = [(float("nan"), w) for w in args.width_ps]
            else:
                targets = widths_for_depths(device.device_id, direction)
            if not targets:
                print(f"[{device.device_id} {direction}] no usable depth curve", flush=True)
                continue
            edge_ns = 5.0 if direction == "short_high" else 10.0
            for depth_target, width_ps in targets:
                width_ns = width_ps / 1000.0
                tag = (f"{direction}_w{int(round(width_ps))}ps" if not np.isfinite(depth_target)
                       else f"{direction}_depth{int(round(depth_target * 100))}")
                case = base.PulseCase(f"{tag}_{int(round(width_ps))}ps", 0.050, direction,
                                      width_ns, 22.0, f"silicon depth {depth_target:.2f}")
                label = f"{device.device_id} {direction.replace('_', '-')} silicon depth {depth_target:.2f}"
                print(f"[{label}] width {width_ps:.1f} ps", flush=True)

                case_dir = out / "hspice_fixtures" / device.device_id / tag
                try:
                    low = run_fixture(device, case, 0.0, case_dir / "vfix_0",
                                      args.hspice, args.hspice_timeout)
                    high = run_fixture(device, case, device.supply_v, case_dir / "vfix_vcc",
                                       args.hspice, args.hspice_timeout)
                except RuntimeError as error:
                    print(f"  fixture failed: {error}", flush=True)
                    continue
                silicon = solve_silicon_kukd(ibis_data, low, high, device.supply_v)

                native, _ = pad.run_native_reference(device, profile, case, LOAD,
                                                    args.hspice, args.hspice_timeout)
                transistor, _ = pad.run_transistor_reference(device, case, args.hspice,
                                                             args.hspice_timeout)
                raw, row = base.run_ngspice(device, profile, case, "gate_state",
                                            GATE_STATE_MODE, model_path,
                                            out / "ngspice_runs", args.ngspice,
                                            args.ngspice_timeout)
                if raw is None:
                    print(f"  gate-state did not converge; recorded and skipped", flush=True)
                    summary.append({"device": device.device_id, "direction": direction,
                                    "depth_target": depth_target,
                                    "pulse_width_ps": round(width_ps, 1),
                                    "status": "NGSPICE_FAIL"})
                    continue
                model_wave = base.ngspice_waveform(raw)

                grid = native["time_ns"]
                t_sil = silicon[:, 0] * 1e9
                series = {
                    "silicon (transistor)": (SILICON, 2.8, {
                        "ku": np.interp(grid, t_sil, silicon[:, 1]),
                        "kd": np.interp(grid, t_sil, silicon[:, 2]),
                        "pad": np.interp(grid, transistor["time_ns"], transistor["pad_v"]),
                    }),
                    "HSPICE native IBIS": (NATIVE, 1.7, {
                        "ku": native["ku"], "kd": native["kd"], "pad": native["pad_v"],
                    }),
                    "pybis gate-state": (MODEL, 1.7, {
                        "ku": np.interp(grid, model_wave["time_ns"], model_wave["ku"]),
                        "kd": np.interp(grid, model_wave["time_ns"], model_wave["kd"]),
                        "pad": np.interp(grid, model_wave["time_ns"], model_wave["pad_v"]),
                    }),
                }
                t_rev = edge_ns + width_ns
                plot_case(out / "plots" / f"{device.device_id}_{tag}.png",
                          f"{label} â€” pulse {width_ps:.0f} ps", grid, t_rev, edge_ns, series)

                wave_path = out / "waveforms" / f"{device.device_id}_{tag}.csv"
                wave_path.parent.mkdir(parents=True, exist_ok=True)
                names = ["time_ns"]
                columns = [grid]
                for name, (_, _, data) in series.items():
                    stem = name.split(" ")[0].lower().strip("(")
                    for key in ("ku", "kd", "pad"):
                        names.append(f"{stem}_{key}")
                        columns.append(data[key])
                with wave_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(names)
                    writer.writerows(np.column_stack(columns))

                summary.append({"device": device.device_id, "direction": direction,
                                "depth_target": depth_target,
                                "pulse_width_ps": round(width_ps, 1),
                                "status": "OK"})

    if summary:
        # Merge rather than overwrite. Widths are given per direction, so a full
        # sweep takes several invocations into one directory, and rewriting the
        # index each time left it describing only the last one while the
        # waveforms from the earlier ones sat there unreferenced.
        merged: dict[tuple[str, str, str], dict[str, object]] = {}
        for row in read_csv(out / "cases.csv"):
            merged[(row["device"], row["direction"], row["pulse_width_ps"])] = row
        for row in summary:
            key = (str(row["device"]), str(row["direction"]), str(row["pulse_width_ps"]))
            merged[key] = row
        rows = list(merged.values())
        with (out / "cases.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(f"cases: {len(summary)}")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


