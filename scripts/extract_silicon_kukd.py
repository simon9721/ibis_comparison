#!/usr/bin/env python3
"""Extract Ku/Kd directly from the transistor during an interrupted pulse.

The transistor is ground truth, but it exposes only a pad voltage, so a
recovery law cannot be graded against it directly. Ku/Kd are not measured
quantities though -- they are *derived*. pybis obtains them by driving the
buffer through two different fixture loads and solving two equations for two
unknowns at every time point. Nothing about that procedure requires the buffer
to be an IBIS model, so the same solve applied to the transistor yields the
Ku/Kd trajectory silicon actually follows.

That gives a recovery target that is not native IBIS's opinion. It matters
because the two disagree sharply: on `inv_chain` short-high native IBIS invents
a 0.93 V pulse where silicon produces 0.000 V, so fitting a recovery law to
native IBIS would teach the model to reproduce an artifact.

The I-V tables are still taken from the IBIS file. They describe the DC device
characteristic, which is not what is in question here -- only the switching
coefficients over time are. Both come from the same transistor netlist via
s2ibispy, so they are mutually consistent.

Cached HSPICE is reused; only the two fixture runs per case are new.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
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
from eye_diagram import parse_hspice_tr0  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402

SWEEP = ROOT / "results" / "three_buffer_native_anchored_stress_sweep_2026-08-19"
DEFAULT_OUT = ROOT / "results" / "silicon_kukd_recovery_2026-08-19"
R_FIXTURE = 50.0
CORNER = 1


@dataclass
class FixtureWaveform:
    """Minimal stand-in for a pybis waveform object.

    ``generating_current_data`` only reads ``data``, ``v_fix`` and ``r_fix``, so
    a transistor run can be presented to the existing solve unchanged.
    """

    data: np.ndarray
    v_fix: list[float]
    r_fix: float
    c_fix: None = None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fixture_deck(device: base.Device, case: base.PulseCase, v_fixture: float) -> str:
    """Transistor deck loaded by an IBIS-style fixture instead of the study load."""
    full = base.transistor_deck(device, case)
    lines: list[str] = []
    for line in full.splitlines():
        low = line.strip().lower()
        if low.startswith("rload") or low.startswith("cload"):
            continue
        if low.startswith(".probe"):
            lines.append(f"Vfix fix 0 DC {base.fmt(v_fixture)}")
            lines.append(f"Rfix pad_sp fix {base.fmt(R_FIXTURE)}")
            lines.append(".probe tran V(in_dig) V(pad_sp)")
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def run_fixture(device: base.Device, case: base.PulseCase, v_fixture: float,
                out_dir: Path, hspice: Path, timeout_s: int) -> np.ndarray:
    out_dir.mkdir(parents=True, exist_ok=True)
    base.copy_transistor_inputs(device, out_dir)
    deck = fixture_deck(device, case, v_fixture)
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    tr0 = out_dir / "run.tr0"
    lis = out_dir / "run.lis"
    concluded = (
        tr0.exists() and lis.exists()
        and "job concluded" in lis.read_text(encoding="utf-8", errors="replace").lower()
    )
    if not concluded:
        rc = base.run_process(
            [str(hspice), "-i", "run.sp", "-o", "run"], out_dir,
            out_dir / "hspice_stdout.log", timeout_s,
        )
        if rc != 0 or not tr0.exists():
            raise RuntimeError(f"fixture run failed ({v_fixture} V): {out_dir}")
    raw = parse_hspice_tr0(tr0)
    time_s = np.asarray(raw["time"], dtype=float)
    pad = np.asarray(raw[next(k for k in raw if "pad_sp" in k)], dtype=float)
    return np.column_stack([time_s, pad, pad, pad])


# Uniform resample applied before the solve. The two fixtures arrive on their
# own HSPICE adaptive grids, and taking the union of those grids puts timesteps
# as short as 8 fs beside stretches where one fixture is only linearly
# interpolated. `C_comp * dV/dt` is a finite difference over that grid, so it
# amplifies the interpolation staircase enormously -- across the io_buf falling
# edge the device currents move under 1% while the C_comp term swings 9x,
# driving Ku to +1.5 and -1.2 on a coefficient that belongs in [0, 1].
#
# The conditioning is not the problem; `np.linalg.cond` never exceeds 5.5 on
# any case here. Resampling both fixtures onto one uniform grid removes 77-80%
# of the excursion on io_buf and leaves inv_chain and ex2 essentially
# untouched, which is what identifies it as numerical: a physical coefficient
# does not depend on the sampling interval.
#
# 5 ps is still 200 samples per io_buf's slowest fitted time constant (1.13 ns),
# so the edge shape survives intact.
UNIFORM_GRID_PS = 5.0


def solve_silicon_kukd(ibis_data, low: np.ndarray, high: np.ndarray,
                       v_high: float, uniform_ps: float | None = UNIFORM_GRID_PS
                       ) -> np.ndarray:
    """Solves Ku/Kd from two transistor fixture responses.

    This mirrors ``pybis2spice.solve_k_params_output`` exactly; only the source
    of the two voltage waveforms differs, and the grid the solve runs on.
    Pass ``uniform_ps=None`` to reproduce the original union-grid behaviour.
    """
    if uniform_ps is None:
        time = np.unique(np.sort(np.concatenate([low[:, 0], high[:, 0]])))
    else:
        start = max(low[0, 0], high[0, 0])
        stop = min(low[-1, 0], high[-1, 0])
        time = np.arange(start, stop, uniform_ps * 1e-12)
        low = np.column_stack([time] + [np.interp(time, low[:, 0], low[:, 1])] * 3)
        high = np.column_stack([time] + [np.interp(time, high[:, 0], high[:, 1])] * 3)
    wave_low = FixtureWaveform(low, [0.0, 0.0, 0.0], R_FIXTURE)
    wave_high = FixtureWaveform(high, [v_high] * 3, R_FIXTURE)

    pu1, pd1, pc1, gc1, rf1, cc1, cf1 = pybis2spice.generating_current_data(
        ibis_data, time, CORNER, wave_low)
    pu2, pd2, pc2, gc2, rf2, cc2, cf2 = pybis2spice.generating_current_data(
        ibis_data, time, CORNER, wave_high)

    i1 = gc1 + pc1 + rf1 - cc1 - cf1
    i2 = gc2 + pc2 + rf2 - cc2 - cf2

    out = np.zeros((len(time), 4))
    out[:, 0] = time
    for n in range(len(time)):
        matrix = np.array([[pu1[n], pd1[n]], [pu2[n], pd2[n]]])
        # Conditioning is the honest confidence measure here. The two fixtures
        # stop giving independent information whenever both devices are nearly
        # off, and the solve is then reconstructing coefficients from almost no
        # signal. Recording it keeps a numerically meaningless Ku/Kd from being
        # read as a statement about the buffer.
        out[n, 3] = np.linalg.cond(matrix)
        if abs(np.linalg.det(matrix)) < 1e-18:
            out[n, 1] = out[n, 2] = np.nan
            continue
        ku, kd = np.linalg.solve(matrix, np.array([i1[n], i2[n]]))
        out[n, 1], out[n, 2] = ku, kd
    return out


def load_case_waveforms(device_id: str, direction: str, target: int) -> dict[str, np.ndarray]:
    path = SWEEP / "figures" / device_id / direction / f"swing_{target}" / "waveforms.csv"
    rows = read_csv(path)
    if not rows:
        return {}
    return {
        key: np.array([float(r[key]) if r[key] not in ("", "nan") else np.nan for r in rows])
        for key in rows[0]
    }


def rmse(a: np.ndarray, b: np.ndarray, t: np.ndarray,
         mask: np.ndarray | None = None) -> float:
    """Time-weighted RMSE.

    These waveforms sit on HSPICE's adaptive time grid, which concentrates
    samples wherever the circuit is moving: on one 50 ps `inv_chain` case, 127
    of 283 samples fall inside a 95 ps window. Averaging over samples therefore
    weights by sample density rather than by time, and a brief excursion during
    the transition dominates a figure that reads as a whole-record average.
    Integrating over time removes that bias.
    """
    if mask is not None:
        a, b, t = a[mask], b[mask], t[mask]
    ok = np.isfinite(a) & np.isfinite(b) & np.isfinite(t)
    a, b, t = a[ok], b[ok], t[ok]
    if len(t) < 2:
        return float("nan")
    span = t[-1] - t[0]
    if span <= 0:
        return float("nan")
    return float(np.sqrt(np.trapezoid((a - b) ** 2, t) / span))


def plot_case(path: Path, label: str, t: np.ndarray, series: dict[str, tuple],
              t_rev: float, edge_ns: float) -> None:
    # Crop to the event. These records run to 22 ns and are flat almost
    # everywhere, so an uncropped plot hides the only interesting nanosecond.
    window = (t >= edge_ns - 0.3) & (t <= t_rev + 4.0)
    if window.sum() < 8:
        window = np.ones_like(t, dtype=bool)
    fig, axes = plt.subplots(2, 1, figsize=(11.0, 7.0), sharex=True)
    for axis, coeff in zip(axes, ("ku", "kd")):
        for name, (colour, width, data) in series.items():
            axis.plot(t[window], data[coeff][window], color=colour, lw=width, label=name)
        axis.axvline(t_rev, color="0.4", ls="--", lw=1)
        axis.set_ylabel(coeff.replace("k", "K"))
        axis.grid(alpha=0.3)
    axes[0].set_title(f"{label} — Ku/Kd from silicon, from native IBIS, and from the model")
    axes[0].legend(fontsize=8.5, ncol=3)
    axes[1].set_xlabel("Time (ns)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--hspice-timeout", type=int, default=300)
    parser.add_argument("--device", action="append", choices=[d.device_id for d in base.DEVICES])
    parser.add_argument("--direction", action="append", choices=["short_high", "short_low"])
    parser.add_argument("--target-percent", action="append", type=int)
    args = parser.parse_args()

    devices = set(args.device or [d.device_id for d in base.DEVICES])
    directions = args.direction or ["short_high", "short_low"]
    targets = args.target_percent or [90, 70, 50]

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    selection = {
        (r["device"], r["direction"], str(int(float(r["target_percent"])))): r
        for r in read_csv(SWEEP / "selection.csv")
    }

    summary: list[dict[str, object]] = []
    for device in base.DEVICES:
        if device.device_id not in devices:
            continue
        ibis_data = pybis2spice.DataModel(
            pybis2spice.get_ibis_model_ecdtools(str(device.fast_ibis)),
            model_name=device.model, component_name=device.component,
        )
        for direction in directions:
            for target in targets:
                chosen = selection.get((device.device_id, direction, str(target)))
                data = load_case_waveforms(device.device_id, direction, target)
                if chosen is None or not data:
                    continue
                width_ns = float(chosen["pulse_width_ps"]) / 1000.0
                case = base.PulseCase(
                    f"{direction}_swing{target}", 0.050,
                    direction, width_ns, 22.0, f"{target}% native swing",
                )
                label = f"{device.device_id} {direction} {target}%"
                print(f"[{label}] pulse {width_ns * 1000:.1f} ps", flush=True)
                case_dir = out / "hspice_fixtures" / device.device_id / direction / f"swing_{target}"
                try:
                    low = run_fixture(device, case, 0.0, case_dir / "vfix_0", args.hspice, args.hspice_timeout)
                    high = run_fixture(device, case, device.supply_v, case_dir / "vfix_vcc",
                                       args.hspice, args.hspice_timeout)
                except RuntimeError as error:
                    print(f"  skipped: {error}", flush=True)
                    continue

                silicon = solve_silicon_kukd(ibis_data, low, high, device.supply_v)
                t_ns = silicon[:, 0] * 1e9
                t_rev = (5.0 if direction == "short_high" else 10.0) + width_ns

                grid = data["time_ns"]
                sil_ku = np.interp(grid, t_ns, silicon[:, 1])
                sil_kd = np.interp(grid, t_ns, silicon[:, 2])
                sil_cond = np.interp(grid, t_ns, silicon[:, 3])
                post = grid >= t_rev
                # Is the IBIS formulation itself able to express what silicon
                # does here? If the coefficients silicon requires stay bounded
                # and the solve stays conditioned, the formulation is adequate
                # and any error is the model's. If not, the limit is structural.
                trusted = post & (sil_cond < 100.0)
                frac_trusted = float(np.count_nonzero(trusted)) / max(np.count_nonzero(post), 1)
                ku_span = (float(np.nanmin(sil_ku[trusted])), float(np.nanmax(sil_ku[trusted]))) if trusted.any() else (np.nan, np.nan)
                kd_span = (float(np.nanmin(sil_kd[trusted])), float(np.nanmax(sil_kd[trusted]))) if trusted.any() else (np.nan, np.nan)

                series = {
                    "silicon (transistor)": ("#111111", 2.6, {"ku": sil_ku, "kd": sil_kd}),
                    "HSPICE native IBIS": ("#2b6ca3", 1.6,
                                           {"ku": data["hspice_native_ku"], "kd": data["hspice_native_kd"]}),
                    "gate-state model": ("#c02626", 1.6,
                                         {"ku": data["gate_state_ku"], "kd": data["gate_state_kd"]}),
                }
                plot_case(out / "plots" / f"{device.device_id}_{direction}_{target}.png",
                          label, grid, series, t_rev, 5.0 if direction == "short_high" else 10.0)

                rows = np.column_stack([grid, sil_ku, sil_kd,
                                        data["hspice_native_ku"], data["hspice_native_kd"],
                                        data["gate_state_ku"], data["gate_state_kd"]])
                csv_path = out / "waveforms" / f"{device.device_id}_{direction}_{target}.csv"
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                with csv_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["time_ns", "silicon_ku", "silicon_kd", "native_ku",
                                     "native_kd", "model_ku", "model_kd"])
                    writer.writerows(rows)

                summary.append({
                    "device": device.device_id,
                    "direction": direction,
                    "target_percent": target,
                    "pulse_width_ps": round(width_ns * 1000, 1),
                    "native_vs_silicon_ku_post": round(rmse(data["hspice_native_ku"], sil_ku, grid, post), 4),
                    "model_vs_silicon_ku_post": round(rmse(data["gate_state_ku"], sil_ku, grid, post), 4),
                    "native_vs_silicon_kd_post": round(rmse(data["hspice_native_kd"], sil_kd, grid, post), 4),
                    "model_vs_silicon_kd_post": round(rmse(data["gate_state_kd"], sil_kd, grid, post), 4),
                    "native_vs_model_ku_post": round(rmse(data["hspice_native_ku"], data["gate_state_ku"], grid, post), 4),
                    "well_conditioned_fraction": round(frac_trusted, 3),
                    "silicon_ku_min": round(ku_span[0], 3),
                    "silicon_ku_max": round(ku_span[1], 3),
                    "silicon_kd_min": round(kd_span[0], 3),
                    "silicon_kd_max": round(kd_span[1], 3),
                })

    if summary:
        with (out / "recovery_vs_silicon.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
            writer.writeheader()
            writer.writerows(summary)
    print(f"cases: {len(summary)}")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
