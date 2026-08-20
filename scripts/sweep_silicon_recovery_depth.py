#!/usr/bin/env python3
"""Sweep pulse width and measure how silicon's recovery depends on interruption depth.

The standing hypothesis behind several earlier model generations was that a
device only partly turned off recovers faster than one fully off, so a fixed
delay plus a fixed time constant is the wrong law. Measured against silicon on
`io_buf`, recovery time was constant to 3% across a threefold range of depth,
which does not support it -- but `io_buf` was the only buffer able to test the
question. `inv_chain` and `ex2` pulses in the native-anchored sweep are so short
that their interrupted coefficient never moves at all, giving depth ~0.

This sweeps pulse width directly rather than searching for target depths. A
sweep produces a depth-versus-recovery curve instead of isolated points, needs
no search iterations to converge, and reports whatever depths the device
actually reaches rather than assuming they are attainable.

"Depth" is how far the interrupted coefficient had travelled from its ON state
when the reverse edge arrived: 0 means untouched, 1 means fully off. The
coefficient in question is Kd for a short-high pulse and Ku for a short-low one
-- in each case the device that was on, got partly turned off, and must return.

Two HSPICE fixture runs per width; nothing else is simulated.
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
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from extract_silicon_kukd import run_fixture, solve_silicon_kukd  # noqa: E402

DEFAULT_OUT = ROOT / "results" / "silicon_recovery_depth_sweep_2026-08-19"

# Width ranges bracket each buffer's own coefficient transition, taken from the
# long-control timing: inv_chain's coefficients move over roughly 270-330 ps
# after an edge, ex2's over 770-1260 ps, io_buf's over a much longer span.
WIDTH_RANGES_PS = {
    "inv_chain": (150.0, 520.0),
    "ex2": (450.0, 1450.0),
    "io_buf": (250.0, 2900.0),
}
POINTS = 8


def recovery_metrics(t: np.ndarray, y: np.ndarray, index: int, t_rev: float) -> dict[str, float]:
    """Separates continued turn-off from the actual return.

    The device keeps turning off after the reverse edge, because the command
    that switched it off is still in flight. Measuring from the reverse edge
    therefore mixes that continued departure with the return, and reports long
    "recovery" times for pulses whose depth at the edge was near zero. The
    return leg is measured from the extremum instead, which is where recovery
    genuinely starts.
    """
    segment = t >= t_rev
    times, values = t[segment], y[segment]
    if len(times) < 3:
        return {}
    floor_index = int(np.nanargmin(values))
    t_floor, v_floor = times[floor_index], values[floor_index]

    target = v_floor + (1.0 - v_floor) * 0.632
    tail_t, tail_v = times[floor_index:], values[floor_index:]
    crossings = np.where(np.diff(np.sign(tail_v - target)) != 0)[0]
    return_ps = float(tail_t[crossings[0]] - t_floor) * 1000.0 if len(crossings) else float("nan")

    return {
        "depth_at_reversal": 1.0 - float(y[index]),
        "max_depth": 1.0 - float(v_floor),
        "turn_off_continues_ps": float(t_floor - t_rev) * 1000.0,
        "return_from_floor_63_ps": return_ps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--hspice-timeout", type=int, default=300)
    parser.add_argument("--device", action="append", choices=list(WIDTH_RANGES_PS))
    parser.add_argument("--direction", action="append", choices=["short_high", "short_low"])
    parser.add_argument("--points", type=int, default=POINTS)
    args = parser.parse_args()

    devices = args.device or ["inv_chain", "ex2"]
    directions = args.direction or ["short_high", "short_low"]
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for device in base.DEVICES:
        if device.device_id not in devices:
            continue
        ibis_data = pybis2spice.DataModel(
            pybis2spice.get_ibis_model_ecdtools(str(device.fast_ibis)),
            model_name=device.model, component_name=device.component,
        )
        low_ps, high_ps = WIDTH_RANGES_PS[device.device_id]
        widths = np.linspace(low_ps, high_ps, args.points)
        for direction in directions:
            coefficient = "kd" if direction == "short_high" else "ku"
            edge_ns = 5.0 if direction == "short_high" else 10.0
            for width_ps in widths:
                width_ns = float(width_ps) / 1000.0
                tag = f"{direction}_{int(round(width_ps))}ps"
                case = base.PulseCase(tag, 0.050, direction, width_ns, 22.0,
                                      f"{width_ps:.0f} ps pulse")
                case_dir = out / "hspice_fixtures" / device.device_id / tag
                try:
                    low = run_fixture(device, case, 0.0, case_dir / "vfix_0",
                                      args.hspice, args.hspice_timeout)
                    high = run_fixture(device, case, device.supply_v, case_dir / "vfix_vcc",
                                       args.hspice, args.hspice_timeout)
                except RuntimeError as error:
                    print(f"  {device.device_id} {tag}: skipped ({error})", flush=True)
                    continue

                silicon = solve_silicon_kukd(ibis_data, low, high, device.supply_v)
                t_ns = silicon[:, 0] * 1e9
                values = silicon[:, 1 if coefficient == "ku" else 2]
                condition = silicon[:, 3]

                t_rev = edge_ns + width_ns
                index = int(np.searchsorted(t_ns, t_rev))
                index = min(max(index, 0), len(t_ns) - 1)
                metrics = recovery_metrics(t_ns, values, index, t_rev)
                if not metrics:
                    continue
                recovery = metrics["return_from_floor_63_ps"]
                post = t_ns >= t_rev
                trusted = float(np.count_nonzero(condition[post] < 100.0)) / max(np.count_nonzero(post), 1)

                rows.append({
                    "device": device.device_id,
                    "direction": direction,
                    "coefficient": coefficient.upper(),
                    "pulse_width_ps": round(width_ps, 1),
                    "depth_at_reversal": round(metrics["depth_at_reversal"], 4),
                    "max_depth": round(metrics["max_depth"], 4),
                    "turn_off_continues_ps": round(metrics["turn_off_continues_ps"], 1),
                    "silicon_recovery_63_ps": round(recovery, 1) if np.isfinite(recovery) else "",
                    "well_conditioned_fraction": round(trusted, 3),
                })
                shown = f"{recovery:8.1f} ps" if np.isfinite(recovery) else "     n/a"
                print(f"  {device.device_id:10s} {direction:11s} {width_ps:7.1f} ps -> "
                      f"depth@rev {metrics['depth_at_reversal']:6.3f}  max {metrics['max_depth']:6.3f}  "
                      f"return {shown}", flush=True)

                with (out / "depth_vs_recovery.csv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)

    # Below this depth the device never meaningfully turned off, so there is
    # nothing to recover from and the measured time is threshold noise rather
    # than a recovery. Those points would otherwise sit at the origin and drag
    # any trend line toward a dependence that is not there.
    min_depth = 0.05
    usable = [
        r for r in rows
        if r["silicon_recovery_63_ps"] != "" and float(r["max_depth"]) >= min_depth
    ]
    degenerate = len(rows) - len(usable)
    if usable:
        fig, ax = plt.subplots(figsize=(9.0, 5.6))
        styles = {
            ("inv_chain", "short_high"): ("#b3541e", "o"), ("inv_chain", "short_low"): ("#b3541e", "s"),
            ("ex2", "short_high"): ("#3c8d3c", "o"), ("ex2", "short_low"): ("#3c8d3c", "s"),
            ("io_buf", "short_high"): ("#2b6ca3", "o"), ("io_buf", "short_low"): ("#2b6ca3", "s"),
        }
        for key, (colour, marker) in styles.items():
            subset = [r for r in usable if (r["device"], r["direction"]) == key]
            if not subset:
                continue
            ax.scatter([r["max_depth"] for r in subset],
                       [float(r["silicon_recovery_63_ps"]) for r in subset],
                       color=colour, marker=marker, s=46,
                       label=f"{key[0]} {key[1].replace('short_', '')}")
        ax.set_xlabel("interruption depth at the reverse edge (0 = untouched, 1 = fully off)")
        ax.set_ylabel("silicon 63% recovery time (ps)")
        ax.set_title("Does silicon's recovery time depend on how far the device turned off?")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8.5)
        fig.tight_layout()
        (out / "plots").mkdir(parents=True, exist_ok=True)
        fig.savefig(out / "plots" / "depth_vs_recovery.png", dpi=160)
        plt.close(fig)

    print()
    print("recovery time versus depth, per buffer and direction:")
    for device in ("io_buf", "inv_chain", "ex2"):
        for direction in ("short_high", "short_low"):
            subset = [r for r in usable if r["device"] == device and r["direction"] == direction]
            if len(subset) < 2:
                continue
            depths = np.array([float(r["max_depth"]) for r in subset])
            times = np.array([float(r["silicon_recovery_63_ps"]) for r in subset])
            order = np.argsort(depths)
            slope = np.polyfit(depths[order], times[order], 1)[0] if len(subset) >= 2 else float("nan")
            print(f"  {device:10s} {direction:11s} n={len(subset):2d}  "
                  f"depth {depths.min():.2f}-{depths.max():.2f}  "
                  f"recovery {times.min():7.1f}-{times.max():7.1f} ps  "
                  f"spread {times.max() - times.min():6.1f} ps  "
                  f"slope {slope:8.1f} ps per unit depth")
    print()
    print(f"points: {len(rows)}  usable: {len(usable)}  "
          f"excluded as depth < {min_depth}: {degenerate}")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


