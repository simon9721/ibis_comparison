#!/usr/bin/env python3
"""Does silicon Ku/Kd change when the fixtures themselves change?

The two-fixture extraction assumes Ku(t) is a property of the buffer's internal
state, not of what hangs off the pad. `test_kukd_load_transfer.py` tests that
indirectly -- solve on two fixtures, predict a third load. This tests it
directly: re-solve on *different* fixtures and compare the coefficients. If the
premise holds, adding C_fixture and L_fixture must leave Ku(t) and Kd(t) where
they were, because they describe the buffer and the buffer did not change.

The fixture current is probed rather than modelled. `generating_current_data`
computes it as `(v_fix - v_pad) / r_fix`, which stops being true the moment an
inductor is in series, so the deck carries a 0 V sense source and the solve uses
what HSPICE measured:

    Ku i_pu(V) + Kd i_pd(V) = i_gc(V) + i_pc(V) + i_fix - C_comp dV/dt

With L = 0 and C = 0 that reduces to the shipped formulation exactly, and the
first variant run is precisely that control: it has to reproduce
`solve_silicon_kukd` to numerical noise, or the sign convention on the sense
source is wrong.

Fixture topology, following the IBIS test-load shape:

    pad -- Vsense -- Lfixture --+-- Rfixture -- Vfixture
                                |
                            Cfixture
                                |
                               gnd

    py -3.14 scripts/test_kukd_fixture_variants.py
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
    CORNER, R_FIXTURE, SWEEP, UNIFORM_GRID_PS, read_csv, rmse,
    solve_silicon_kukd,
)

OUT = ROOT / "results" / "kukd_fixture_variants_2026-08-28"

# label, L_fixture (H), C_fixture (F). R and V stay at the IBIS values.
VARIANTS = [
    ("baseline   R only", 0.0, 0.0),
    ("C_fix 2 pF", 0.0, 2e-12),
    ("L_fix 0.5 nH", 0.5e-9, 0.0),
    ("L_fix 2 nH", 2e-9, 0.0),
    ("L 2 nH + C 2 pF", 2e-9, 2e-12),
]

# One case per device, chosen from the cases whose pad actually moves.
CASES = [("io_buf", "short_high", 70), ("inv_chain", "short_low", 90),
         ("ex2", "short_low", 90)]

DPI = 175
# One per entry in VARIANTS -- zip against the solutions truncates silently, so
# a short list drops variants from the figure without any warning.
COLOURS = ["#111111", "#C02626", "#1B6B4F", "#7B2CBF", "#C77F0A"]
assert len(COLOURS) >= len(VARIANTS), "a colour per variant"


def variant_deck(device, case, v_fixture: float, l_fix: float, c_fix: float) -> str:
    """Transistor deck loaded by an IBIS fixture with optional L and C.

    A 0 V source in series with the fixture acts as an ammeter. HSPICE reports
    I(Vsense) flowing from its first node to its second, so the current arriving
    at the pad from the fixture is the negative of that.
    """
    full = base.transistor_deck(device, case)
    lines: list[str] = []
    for line in full.splitlines():
        low = line.strip().lower()
        if low.startswith("rload") or low.startswith("cload"):
            continue
        if low.startswith(".probe"):
            lines.append("Vsense pad_sp fixa DC 0")
            node = "fixa"
            if l_fix > 0.0:
                lines.append(f"Lfix fixa fixb {l_fix * 1e9:.6f}n")
                node = "fixb"
            if c_fix > 0.0:
                lines.append(f"Cfix {node} 0 {c_fix * 1e12:.6f}p")
            lines.append(f"Rfix {node} fix {base.fmt(R_FIXTURE)}")
            lines.append(f"Vfix fix 0 DC {base.fmt(v_fixture)}")
            lines.append(".probe tran V(in_dig) V(pad_sp) I(Vsense)")
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def run_variant(device, case, v_fixture, l_fix, c_fix, out_dir: Path,
                hspice: Path, timeout_s: int):
    """(time_s, pad_v, i_into_pad) for one fixture, cached like the others."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base.copy_transistor_inputs(device, out_dir)
    (out_dir / "run.sp").write_text(
        variant_deck(device, case, v_fixture, l_fix, c_fix), encoding="utf-8")
    tr0, lis = out_dir / "run.tr0", out_dir / "run.lis"
    concluded = (
        tr0.exists() and lis.exists()
        and "job concluded" in lis.read_text(encoding="utf-8", errors="replace").lower()
    )
    if not concluded:
        rc = base.run_process([str(hspice), "-i", "run.sp", "-o", "run"], out_dir,
                              out_dir / "hspice_stdout.log", timeout_s)
        if rc != 0 or not tr0.exists():
            raise RuntimeError(f"fixture run failed: {out_dir}")
    raw = parse_hspice_tr0(tr0)
    keys = {k.lower(): k for k in raw}
    time_s = np.asarray(raw[keys["time"]], dtype=float)
    pad = np.asarray(raw[next(k for k in raw if "pad_sp" in k.lower())], dtype=float)
    sense = next((k for k in raw if "vsense" in k.lower()), None)
    if sense is None:
        raise RuntimeError(f"no I(Vsense) in {tr0}")
    into_pad = -np.asarray(raw[sense], dtype=float)
    return time_s, pad, into_pad


def solve_from_measured(ibis_data, runs, uniform_ps: float = UNIFORM_GRID_PS):
    """Ku/Kd from two fixtures, using the measured fixture current.

    ``runs`` is a pair of (time_s, pad_v, i_into_pad). Both are resampled onto a
    common uniform grid first, for the reason recorded in extract_silicon_kukd:
    C_comp dV/dt is a finite difference, and differentiating across the union of
    two adaptive grids amplifies the interpolation staircase.
    """
    start = max(r[0][0] for r in runs)
    stop = min(r[0][-1] for r in runs)
    time = np.arange(start, stop, uniform_ps * 1e-12)

    c_comp = float(ibis_data.c_comp[CORNER - 1])
    pu_ref = pb.get_reference(ibis_data.pullup_ref, ibis_data.v_range, CORNER)
    pd_ref = pb.get_reference(ibis_data.pulldown_ref, 0, CORNER)
    pc_ref = pb.get_reference(ibis_data.pwr_clamp_ref, ibis_data.v_range, CORNER)
    gc_ref = pb.get_reference(ibis_data.gnd_clamp_ref, 0, CORNER)

    matrix_rows, rhs_rows = [], []
    for time_s, pad, into_pad in runs:
        vt = np.interp(time, time_s, pad)
        i_fix = np.interp(time, time_s, into_pad)
        i_pu = pb.get_current_data_from_iv_data(vt, ibis_data.iv_pullup, pu_ref,
                                                CORNER, iv_data_adjust=ibis_data.iv_pwr_clamp)
        i_pd = pb.get_current_data_from_iv_data(vt, ibis_data.iv_pulldown, pd_ref,
                                                CORNER, iv_data_adjust=ibis_data.iv_gnd_clamp)
        i_pc = pb.get_current_data_from_iv_data(vt, ibis_data.iv_pwr_clamp, pc_ref,
                                                CORNER, iv_data_adjust=None)
        i_gc = pb.get_current_data_from_iv_data(vt, ibis_data.iv_gnd_clamp, gc_ref,
                                                CORNER, iv_data_adjust=None)
        matrix_rows.append((np.asarray(i_pu), np.asarray(i_pd)))
        rhs_rows.append(np.asarray(i_gc) + np.asarray(i_pc) + i_fix
                        - c_comp * pb.differentiate(vt, time))

    out = np.zeros((len(time), 4))
    out[:, 0] = time
    for n in range(len(time)):
        matrix = np.array([[matrix_rows[0][0][n], matrix_rows[0][1][n]],
                           [matrix_rows[1][0][n], matrix_rows[1][1][n]]])
        out[n, 3] = np.linalg.cond(matrix)
        if abs(np.linalg.det(matrix)) < 1e-18:
            out[n, 1] = out[n, 2] = np.nan
            continue
        out[n, 1], out[n, 2] = np.linalg.solve(
            matrix, np.array([rhs_rows[0][n], rhs_rows[1][n]]))
    return out


def compare(reference: np.ndarray, other: np.ndarray) -> tuple[float, float, float]:
    """Time-weighted RMSE and worst gap between two Ku/Kd solutions."""
    t_ref = reference[:, 0] * 1e9
    t_other = other[:, 0] * 1e9
    lo, hi = max(t_ref[0], t_other[0]), min(t_ref[-1], t_other[-1])
    grid = t_ref[(t_ref >= lo) & (t_ref <= hi)]
    out = []
    for col in (1, 2):
        a = np.interp(grid, t_ref, reference[:, col])
        b = np.interp(grid, t_other, other[:, col])
        ok = np.isfinite(a) & np.isfinite(b)
        out.append(rmse(a[ok], b[ok], grid[ok]))
    worst = 0.0
    for col in (1, 2):
        a = np.interp(grid, t_ref, reference[:, col])
        b = np.interp(grid, t_other, other[:, col])
        ok = np.isfinite(a) & np.isfinite(b)
        worst = max(worst, float(np.max(np.abs(a[ok] - b[ok]))) if ok.any() else 0.0)
    return out[0], out[1], worst


def variant_figure(path, label, solutions, window):
    """Overlay above, departure from the R-only baseline below.

    The overlay alone is close to unreadable: away from the reversal the traces
    sit on top of each other to four decimals, so the difference panel is what
    actually carries the answer.
    """
    fig, axes = plt.subplots(4, 1, figsize=(13.0, 12.4), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2, 3, 2]})
    base_t = solutions[0][1][:, 0] * 1e9
    for (top, bottom), col, name in ((( axes[0], axes[1]), 1, "Ku"),
                                     ((axes[2], axes[3]), 2, "Kd")):
        top.axhspan(0.0, 1.0, color="#EDF3FA", zorder=0)
        base = solutions[0][1][:, col]
        for (variant, solution), colour in zip(solutions, COLOURS):
            t = solution[:, 0] * 1e9
            top.plot(t, solution[:, col], color=colour,
                     lw=2.6 if variant.startswith("baseline") else 1.8,
                     ls="-" if variant.startswith("baseline") else (0, (5, 2.2)),
                     label=variant, zorder=3)
            if variant.startswith("baseline"):
                continue
            bottom.plot(t, solution[:, col] - np.interp(t, base_t, base),
                        color=colour, lw=1.7, zorder=3)
        top.set_ylabel(name, fontsize=15)
        top.set_ylim(-0.3, 1.3)
        bottom.set_ylabel(f"{name} − baseline", fontsize=11.5)
        bottom.axhline(0.0, color="#5A5A5A", lw=1.0)
        bottom.set_ylim(-0.6, 0.6)
        for axis in (top, bottom):
            axis.set_xlim(*window)
            axis.grid(alpha=0.28, color="#C9D3DE", lw=0.8)
            axis.tick_params(labelsize=11)
            for spine in axis.spines.values():
                spine.set_color("#3A4753")
    axes[0].set_title(f"{label}  |  Ku and Kd re-solved on {len(solutions)} fixtures, "
                      "against the R-only baseline",
                      fontsize=15.5, fontweight="bold", pad=11)
    axes[0].legend(fontsize=11, loc="upper left", framealpha=0.94)
    axes[3].set_xlabel("Time (ns)", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--hspice", type=Path, default=default_hspice())
    parser.add_argument("--hspice-timeout", type=int, default=300)
    parser.add_argument("--device", action="append",
                        choices=[d.device_id for d in base.DEVICES])
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    (out / "plots").mkdir(parents=True, exist_ok=True)

    wanted = set(args.device or [d.device_id for d in base.DEVICES])
    selection = {(r["device"], r["direction"], str(int(float(r["target_percent"])))): r
                 for r in read_csv(SWEEP / "selection.csv")}

    rows: list[dict[str, object]] = []
    for device_id, direction, target in CASES:
        if device_id not in wanted:
            continue
        device = next(d for d in base.DEVICES if d.device_id == device_id)
        chosen = selection.get((device_id, direction, str(target)))
        if chosen is None:
            continue
        ibis_data = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                                 model_name=device.model, component_name=device.component)
        width_ns = float(chosen["pulse_width_ps"]) / 1000.0
        case = base.PulseCase(f"{direction}_swing{target}", 0.050, direction,
                              width_ns, 22.0, f"{target}% native swing")
        label = f"{device_id} {direction} {target}%"
        edge_ns = 5.0 if direction == "short_high" else 10.0
        window = (edge_ns - 0.3, edge_ns + width_ns + 4.0)
        print(f"\n{label}   pulse {width_ns * 1000:.0f} ps")

        solutions, reference = [], None
        for variant, l_fix, c_fix in VARIANTS:
            tag = variant.split()[0].lower().replace("_", "")
            tag = f"l{l_fix * 1e9:g}n_c{c_fix * 1e12:g}p"
            try:
                runs = [run_variant(device, case, v, l_fix, c_fix,
                                    out / "hspice_fixtures" / device_id /
                                    f"{direction}_swing{target}" / tag / name,
                                    args.hspice, args.hspice_timeout)
                        for v, name in ((0.0, "vfix_0"), (device.supply_v, "vfix_vcc"))]
            except RuntimeError as error:
                print(f"  {variant:<20} skipped: {error}")
                continue
            solution = solve_from_measured(ibis_data, runs)
            solutions.append((variant, solution))
            if reference is None:
                reference = solution
                # The control: the same two fixtures through the shipped solve,
                # which models the fixture current instead of measuring it.
                shipped = solve_silicon_kukd(
                    ibis_data,
                    np.column_stack([runs[0][0]] + [runs[0][1]] * 3),
                    np.column_stack([runs[1][0]] + [runs[1][1]] * 3),
                    device.supply_v)
                ku_e, kd_e, worst = compare(shipped, solution)
                print(f"  {'CONTROL vs shipped solve':<26}"
                      f"Ku {ku_e:8.2e}  Kd {kd_e:8.2e}  worst {worst:8.2e}")
            ku_e, kd_e, worst = compare(reference, solution)

            # Where the disagreement sits, and how hard the fixture is driving
            # the pad. An inductor makes the pad ring, and the coefficients only
            # move where it is slewing -- see the module docstring.
            grid = solution[:, 0] * 1e9
            pad_a = np.interp(solution[:, 0], runs[0][0], runs[0][1])
            slew = np.abs(np.gradient(pad_a, grid))
            delta = solution[:, 1] - np.interp(grid, reference[:, 0] * 1e9,
                                               reference[:, 1])
            quiet = slew < 0.05
            quiet_ku = float(np.abs(delta[quiet]).mean()) if quiet.any() else 0.0
            print(f"  {variant:<26}Ku {ku_e:8.4f}  Kd {kd_e:8.4f}  worst {worst:8.4f}"
                  f"   slew {slew.max():6.2f} V/ns   quiet {quiet_ku:.4f}")
            rows.append({"device": device_id, "direction": direction,
                         "target_percent": target, "variant": variant,
                         "l_fixture_nh": l_fix * 1e9, "c_fixture_pf": c_fix * 1e12,
                         "max_pad_slew_v_per_ns": round(float(slew.max()), 3),
                         "ku_rmse_vs_baseline": round(ku_e, 6),
                         "kd_rmse_vs_baseline": round(kd_e, 6),
                         "quiet_mean_dku": round(quiet_ku, 6),
                         "worst_gap": round(worst, 6)})
        if solutions:
            variant_figure(out / "plots" / f"variants_{device_id}_{direction}_{target}.png",
                           label, solutions, window)

    if not rows:
        print("no cases ran")
        return 1
    summary = out / "fixture_variants.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    changed = [r for r in rows if not str(r["variant"]).startswith("baseline")]
    print(f"\n{len(changed)} altered-fixture solves")
    print(f"  Ku RMSE vs baseline   mean {np.mean([r['ku_rmse_vs_baseline'] for r in changed]):.4f}"
          f"   worst {np.max([r['ku_rmse_vs_baseline'] for r in changed]):.4f}")
    print(f"  Kd RMSE vs baseline   mean {np.mean([r['kd_rmse_vs_baseline'] for r in changed]):.4f}"
          f"   worst {np.max([r['kd_rmse_vs_baseline'] for r in changed]):.4f}")
    print(f"\nwrote {summary.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
