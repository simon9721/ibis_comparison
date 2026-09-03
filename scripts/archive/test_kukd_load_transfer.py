#!/usr/bin/env python3
"""Does silicon Ku/Kd extracted under two fixtures describe a third load?

Ku/Kd is extracted by driving the transistor through 50 ohm to 0 V and 50 ohm
to VCC and solving the IBIS output equation for two unknowns at every timestep.
The result is then compared against models running the *study* load, 50 ohm to
0 V in parallel with 2 pF. Nothing transforms the coefficients between those two
settings: the method simply assumes Ku(t) is a property of the buffer's internal
state and independent of what hangs off the pad. That assumption is what IBIS
asserts, and the 2x2 solve cannot report a violation of it -- two equations in
two unknowns is exactly determined, so it always returns an answer with no
residual left to inspect.

The study load is a genuine third condition (different capacitance, and fixture
B pulls the opposite way), so the assumption is testable. Take Ku(t) and Kd(t)
from the two fixtures and integrate the same equation forward under the study
load:

    (C_comp + C_load) dV/dt = i_gc(V) + i_pc(V) + (V_fix - V)/R_fix
                              - Ku(t) i_pu(V) - Kd(t) i_pd(V)

then compare the predicted pad against the transistor pad the study actually
recorded. The sign convention is taken from the solve itself, where
``i1 = gc1 + pc1 + rf1 - cc1 - cf1`` is the right-hand side of
``Ku*i_pu + Kd*i_pd = i1``.

Two controls run first. Re-integrating under each fixture's *own* load has to
reproduce that fixture's pad, because that is the equation the coefficients were
solved from. The controls therefore measure what the integrator and the finite
difference in the extraction cost on their own, and the test is only meaningful
against that floor.

The study-load run is generated here rather than taken from the archived sweep.
`three_buffer_native_anchored_stress_sweep_2026-08-19` was run on the RDSW=0
card (`hspice_ngspice.mod`), which is ~12% stronger in the output stage than the
stock card the fixtures and the IBIS characterisation use. Fixture A and the
study load are electrically identical at DC -- both 50 ohm to 0 V -- yet the
archived io_buf run settles 80 to 102 mV higher than the fixture. Comparing
against it would measure that card difference, not load transfer.

    py -3.14 scripts/test_kukd_load_transfer.py
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / ".codex_deps" / "presentation" / "python", ROOT,
             ROOT / "scripts", ROOT / "tools" / "pybis2spice"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from pybis2spice import pybis2spice as pb  # noqa: E402
from eye_diagram import parse_hspice_tr0  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from extract_silicon_kukd import (  # noqa: E402
    CORNER, R_FIXTURE, SWEEP, load_case_waveforms, read_csv, rmse,
    solve_silicon_kukd,
)

FIXTURES = ROOT / "results" / "silicon_kukd_recovery_uniform_2026-08-27" / "hspice_fixtures"
OUT = ROOT / "results" / "kukd_load_transfer_test_2026-08-28"

# The study load, from the deck: `Rload pad_sp 0 50` and `Cload pad_sp 0 2p`.
R_LOAD, C_LOAD, V_LOAD = 50.0, 2e-12, 0.0

NEWTON_ITERS = 12
NEWTON_TOL = 1e-11
V_GRID_POINTS = 8001
DPI = 175

SILICON_C = "#111111"
PRED_C = "#C02626"


def fixture_pad(path: Path) -> np.ndarray:
    """(time_s, pad_v) from a cached HSPICE fixture run."""
    raw = parse_hspice_tr0(path)
    time_s = np.asarray(raw["time"], dtype=float)
    pad = np.asarray(raw[next(k for k in raw if "pad_sp" in k)], dtype=float)
    return np.column_stack([time_s, pad, pad, pad])


def run_study_load(device, case, out_dir: Path, hspice: Path, timeout_s: int) -> np.ndarray:
    """The transistor under the study load, on the same card as the fixtures.

    ``base.transistor_deck`` already emits `Rload 50` and `Cload 2p`, so this is
    the campaign's own reference deck, unmodified. Cached the same way the
    fixtures are: an existing run with "job concluded" in its listing is reused.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    base.copy_transistor_inputs(device, out_dir)
    (out_dir / "run.sp").write_text(base.transistor_deck(device, case), encoding="utf-8")
    tr0, lis = out_dir / "run.tr0", out_dir / "run.lis"
    concluded = (
        tr0.exists() and lis.exists()
        and "job concluded" in lis.read_text(encoding="utf-8", errors="replace").lower()
    )
    if not concluded:
        rc = base.run_process([str(hspice), "-i", "run.sp", "-o", "run"], out_dir,
                              out_dir / "hspice_stdout.log", timeout_s)
        if rc != 0 or not tr0.exists():
            raise RuntimeError(f"study-load run failed: {out_dir}")
    return fixture_pad(tr0)


def device_currents(ibis_data, v_grid: np.ndarray):
    """The four IBIS branch currents evaluated on a dense voltage grid.

    Same calls ``generating_current_data`` makes, but against a voltage axis
    rather than a waveform, so the integrator can look them up at whatever pad
    voltage it arrives at.
    """
    pu_ref = pb.get_reference(ibis_data.pullup_ref, ibis_data.v_range, CORNER)
    pd_ref = pb.get_reference(ibis_data.pulldown_ref, 0, CORNER)
    pc_ref = pb.get_reference(ibis_data.pwr_clamp_ref, ibis_data.v_range, CORNER)
    gc_ref = pb.get_reference(ibis_data.gnd_clamp_ref, 0, CORNER)
    i_pu = pb.get_current_data_from_iv_data(v_grid, ibis_data.iv_pullup, pu_ref,
                                            CORNER, iv_data_adjust=ibis_data.iv_pwr_clamp)
    i_pd = pb.get_current_data_from_iv_data(v_grid, ibis_data.iv_pulldown, pd_ref,
                                            CORNER, iv_data_adjust=ibis_data.iv_gnd_clamp)
    i_pc = pb.get_current_data_from_iv_data(v_grid, ibis_data.iv_pwr_clamp, pc_ref,
                                            CORNER, iv_data_adjust=None)
    i_gc = pb.get_current_data_from_iv_data(v_grid, ibis_data.iv_gnd_clamp, gc_ref,
                                            CORNER, iv_data_adjust=None)
    return (np.asarray(i_pu, dtype=float), np.asarray(i_pd, dtype=float),
            np.asarray(i_pc, dtype=float), np.asarray(i_gc, dtype=float))


def integrate(time_s, ku, kd, v_grid, branches, cap, r_load, v_load, v0):
    """Trapezoidal integration of the IBIS output equation under one load.

    Trapezoidal rather than forward Euler because a fully-on device puts the
    pad time constant near 15 ps, which is only three steps of the 5 ps grid
    the coefficients live on. The implicit half is closed with Newton against a
    finite-difference slope; the branch currents are piecewise linear in V, so
    that slope is exact away from the table knots.
    """
    i_pu, i_pd, i_pc, i_gc = branches

    def slope(v, k_u, k_d):
        return (np.interp(v, v_grid, i_gc) + np.interp(v, v_grid, i_pc)
                + (v_load - v) / r_load
                - k_u * np.interp(v, v_grid, i_pu)
                - k_d * np.interp(v, v_grid, i_pd)) / cap

    out = np.empty(len(time_s), dtype=float)
    out[0] = v = float(v0)
    for n in range(1, len(time_s)):
        dt = time_s[n] - time_s[n - 1]
        here = slope(v, ku[n - 1], kd[n - 1])
        guess = v + dt * here
        for _ in range(NEWTON_ITERS):
            residual = guess - v - 0.5 * dt * (here + slope(guess, ku[n], kd[n]))
            h = 1e-7
            derivative = 1.0 - 0.5 * dt * (
                (slope(guess + h, ku[n], kd[n]) - slope(guess - h, ku[n], kd[n]))
                / (2.0 * h))
            step = residual / derivative
            guess -= step
            if abs(step) < NEWTON_TOL:
                break
        out[n] = v = guess
    return out


def fill_gaps(values: np.ndarray) -> tuple[np.ndarray, int]:
    """Linear fill over the timesteps where the 2x2 was singular."""
    bad = ~np.isfinite(values)
    if bad.any():
        index = np.arange(len(values))
        values = values.copy()
        values[bad] = np.interp(index[bad], index[~bad], values[~bad])
    return values, int(bad.sum())


def case_figure(path, label, time_ns, runs):
    """Predicted against recorded pad, one panel per load."""
    fig, axes = plt.subplots(len(runs), 1, figsize=(12.4, 3.1 * len(runs)), sharex=True)
    for axis, (name, measured, predicted) in zip(np.atleast_1d(axes), runs):
        axis.plot(time_ns, measured, color=SILICON_C, lw=3.0, label="HSPICE transistor")
        axis.plot(time_ns, predicted, color=PRED_C, lw=1.9, ls=(0, (5, 2.2)),
                  label="rebuilt from silicon Ku/Kd")
        axis.set_ylabel(f"{name}\npad (V)", fontsize=11.5)
        axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=11)
        for spine in axis.spines.values():
            spine.set_color("#3A4753")
    np.atleast_1d(axes)[0].set_title(
        f"{label}  |  Ku/Kd solved on fixtures A and B, integrated under three loads",
        fontsize=15, fontweight="bold", pad=11)
    np.atleast_1d(axes)[0].legend(fontsize=11, loc="upper right", framealpha=0.94)
    np.atleast_1d(axes)[-1].set_xlabel("Time (ns)", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--device", action="append",
                        choices=[d.device_id for d in base.DEVICES])
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--hspice-timeout", type=int, default=300)
    parser.add_argument("--figure-case", default="io_buf short_high 70")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    (out / "plots").mkdir(parents=True, exist_ok=True)

    devices = set(args.device or [d.device_id for d in base.DEVICES])
    selection = {(r["device"], r["direction"], str(int(float(r["target_percent"])))): r
                 for r in read_csv(SWEEP / "selection.csv")}

    rows: list[dict[str, object]] = []
    print(f"{'case':<26}{'swing':>8}{'ctrl A':>9}{'ctrl B':>9}{'STUDY':>9}"
          f"{'worst':>9}{'quiet':>9}{'edges':>9}{'archived':>11}")
    print(f"{'':<26}{'mV':>8}{'mV':>9}{'mV':>9}{'mV':>9}{'mV':>9}"
          f"{'mV':>9}{'mV':>9}{'mV':>11}")

    for device in base.DEVICES:
        if device.device_id not in devices:
            continue
        ibis_data = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                                 model_name=device.model, component_name=device.component)
        c_comp = float(ibis_data.c_comp[CORNER - 1])
        v_grid = np.linspace(-device.supply_v, 2.0 * device.supply_v, V_GRID_POINTS)
        branches = device_currents(ibis_data, v_grid)

        for direction in ("short_high", "short_low"):
            for target in (90, 70, 50):
                key = (device.device_id, direction, str(target))
                chosen = selection.get(key)
                case_dir = FIXTURES / device.device_id / direction / f"swing_{target}"
                tr_low = case_dir / "vfix_0" / "run.tr0"
                tr_high = case_dir / "vfix_vcc" / "run.tr0"
                if chosen is None or not (tr_low.exists() and tr_high.exists()):
                    continue

                label = f"{device.device_id} {direction} {target}%"
                width_ns = float(chosen["pulse_width_ps"]) / 1000.0
                case = base.PulseCase(f"{direction}_swing{target}", 0.050, direction,
                                      width_ns, 22.0, f"{target}% native swing")
                try:
                    study_pad = run_study_load(
                        device, case, out / "hspice_study_load" / device.device_id /
                        direction / f"swing_{target}", args.hspice, args.hspice_timeout)
                except RuntimeError as error:
                    print(f"{label:<26}  skipped: {error}", flush=True)
                    continue
                low, high = fixture_pad(tr_low), fixture_pad(tr_high)
                silicon = solve_silicon_kukd(ibis_data, low, high, device.supply_v)
                time_s = silicon[:, 0]
                time_ns = time_s * 1e9
                ku, nan_ku = fill_gaps(silicon[:, 1])
                kd, nan_kd = fill_gaps(silicon[:, 2])

                # The two fixtures resampled onto the solve grid, and the study
                # pad brought onto the same axis for comparison.
                pad_low = np.interp(time_s, low[:, 0], low[:, 1])
                pad_high = np.interp(time_s, high[:, 0], high[:, 1])
                pad_study = np.interp(time_s, study_pad[:, 0], study_pad[:, 1])

                # How far the archived sweep sits from the study load it is
                # nominally the same measurement as. Reported, not used: it is a
                # model-card difference, and the number documents the trap.
                archived = load_case_waveforms(device.device_id, direction, target)
                archived_mv = float("nan")
                if archived:
                    archived_mv = rmse(
                        pad_study, np.interp(time_ns, archived["time_ns"],
                                             archived["hspice_transistor_pad_v"]),
                        time_ns) * 1e3

                loads = [
                    ("control A\n50 to 0 V", c_comp, R_FIXTURE, 0.0, pad_low),
                    ("control B\n50 to VCC", c_comp, R_FIXTURE, device.supply_v, pad_high),
                    ("STUDY\n50 to 0 V + 2 pF", c_comp + C_LOAD, R_LOAD, V_LOAD, pad_study),
                ]
                runs, errors = [], []
                for name, cap, r_load, v_load, measured in loads:
                    predicted = integrate(time_s, ku, kd, v_grid, branches,
                                          cap, r_load, v_load, measured[0])
                    errors.append(rmse(predicted, measured, time_ns) * 1e3)
                    runs.append((name, measured, predicted))

                swing = float(np.max(pad_study) - np.min(pad_study)) * 1e3
                worst = float(np.max(np.abs(runs[2][2] - runs[2][1]))) * 1e3

                # Where the transfer error lives. It is not spread over the
                # record: it collects entirely on the slewing edges, and the
                # quiet stretches are near-exact. Refitting a constant extra
                # capacitance does not remove it -- best delta is -0.10 pF on
                # io_buf and +0.40 pF on ex2, opposite signs, for under 6% of
                # RMSE -- so it is not a mis-set lumped C_comp. What remains
                # are the two effects a constant cannot express: a genuinely
                # voltage-dependent parasitic, and Miller feedback making Ku(t)
                # slightly load-dependent, which is the premise under test.
                error_v = runs[2][2] - runs[2][1]
                slew = np.abs(np.gradient(pad_study, time_ns))
                quiet = slew < 0.05
                edges = slew > 1.0
                quiet_mv = float(np.abs(error_v[quiet]).mean()) * 1e3 if quiet.any() else 0.0
                edge_mv = float(np.abs(error_v[edges]).mean()) * 1e3 if edges.any() else 0.0
                print(f"{label:<26}{swing:8.0f}{errors[0]:9.2f}{errors[1]:9.2f}"
                      f"{errors[2]:9.2f}{worst:9.1f}{quiet_mv:9.2f}{edge_mv:9.1f}"
                      f"{archived_mv:11.1f}", flush=True)
                rows.append({
                    "device": device.device_id, "direction": direction,
                    "target_percent": target,
                    "pulse_width_ps": float(chosen["pulse_width_ps"]),
                    "study_swing_mv": round(swing, 2),
                    "control_a_rmse_mv": round(errors[0], 4),
                    "control_b_rmse_mv": round(errors[1], 4),
                    "study_rmse_mv": round(errors[2], 4),
                    "study_worst_mv": round(worst, 3),
                    "quiet_mean_mv": round(quiet_mv, 4),
                    "edge_mean_mv": round(edge_mv, 3),
                    "archived_card_rmse_mv": round(archived_mv, 3),
                    "singular_points": nan_ku + nan_kd,
                })
                if f"{device.device_id} {direction} {target}" == args.figure_case:
                    case_figure(out / "plots" / f"transfer_{device.device_id}_"
                                                f"{direction}_{target}.png",
                                label, time_ns, runs)

    if not rows:
        print("no cases found")
        return 1

    summary = out / "load_transfer.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # Cases whose pad never moves carry no information about load transfer and
    # would only dilute the averages. inv_chain short-high is the known one:
    # silicon produces 0.000 V there where native IBIS invents a 0.93 V pulse.
    live = [r for r in rows if r["study_swing_mv"] > 10.0]
    ctrl = np.array([[r["control_a_rmse_mv"], r["control_b_rmse_mv"]] for r in live])
    test = np.array([r["study_rmse_mv"] for r in live])
    quiet_all = np.array([r["quiet_mean_mv"] for r in live])
    edge_all = np.array([r["edge_mean_mv"] for r in live])
    print(f"\n{len(rows)} cases, {len(live)} with a moving pad")
    print(f"  quiet stretches  |dV/dt| < 0.05 V/ns   mean {quiet_all.mean():7.2f} mV")
    print(f"  slewing edges    |dV/dt| > 1.0  V/ns   mean {edge_all.mean():7.2f} mV")
    print(f"  control floor (own fixture)  mean {ctrl.mean():7.2f} mV   "
          f"worst {ctrl.max():7.2f} mV")
    print(f"  study load     (third load)  mean {test.mean():7.2f} mV   "
          f"worst {test.max():7.2f} mV")
    print(f"  test / control ratio         {test.mean() / ctrl.mean():.2f}x")
    print(f"\nwrote {summary.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
