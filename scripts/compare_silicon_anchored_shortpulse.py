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

This anchors on silicon instead. Widths are interpolated from the measured
depth sweep so that the transistor's own coefficient reaches a chosen fraction
of its travel at the reverse edge, making all six combinations informative.

The deliverable is waveform evidence, not a summary statistic. Every scalar
recovery metric attempted so far has been defeated by either the command still
in flight after the reverse edge or the brief ill-conditioning spike at the
input edge, so the shapes are what should be read.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
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
GATE_STATE_MODE = "InputDrivenTwoStateGateDirectionalDualResidualFull"
LOAD = (50.0, 2.0)
DEPTH_TARGETS = (0.25, 0.50, 0.75)

SILICON = "#111111"
NATIVE = "#2b6ca3"
MODEL = "#c02626"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def widths_for_depths(device_id: str, direction: str) -> list[tuple[float, float]]:
    """Interpolates pulse widths that put silicon at each target depth.

    The measured depth-versus-width curve is monotonic in the region of
    interest but saturates once the device is fully off, so only the rising
    portion is used for interpolation.
    """
    points = sorted(
        (float(r["pulse_width_ps"]), float(r["depth_at_reversal"]))
        for r in read_csv(DEPTH_SWEEP)
        if r["device"] == device_id and r["direction"] == direction
    )
    if len(points) < 3:
        return []
    widths = np.array([p[0] for p in points])
    depths = np.array([p[1] for p in points])
    keep = depths < 0.98
    widths, depths = widths[keep], depths[keep]
    order = np.argsort(depths)
    widths, depths = widths[order], depths[order]
    out: list[tuple[float, float]] = []
    for target in DEPTH_TARGETS:
        if target < depths.min() or target > depths.max():
            continue
        out.append((target, float(np.interp(target, depths, widths))))
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
            convert_ibis_to_pybis(device.fast_ibis, model_path, device.component,
                                  device.model, "Output", GATE_STATE_MODE, "Typical")

        for direction in directions:
            targets = widths_for_depths(device.device_id, direction)
            if not targets:
                print(f"[{device.device_id} {direction}] no usable depth curve", flush=True)
                continue
            edge_ns = 5.0 if direction == "short_high" else 10.0
            for depth_target, width_ps in targets:
                width_ns = width_ps / 1000.0
                tag = f"{direction}_depth{int(round(depth_target * 100))}"
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
                          f"{label} — pulse {width_ps:.0f} ps", grid, t_rev, edge_ns, series)

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
        with (out / "cases.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
            writer.writeheader()
            writer.writerows(summary)
    print(f"cases: {len(summary)}")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
