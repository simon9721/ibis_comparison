"""Sweep short bit patterns to characterize the pybis receiver spike.

The current corrected PRBS run showed a large pybis-only receiver spike near
56.7 ns.  This script keeps the same stressed channel setup and varies the
local bit history around a target rising edge:

    0000 + 1*pre_high + 0*low_gap + 1*post_high + 0000

It runs Xyce refspice and Xyce pybis edge50 for the sweep, then validates a few
representative cases with the corrected ngspice pybis dialect.
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from eye_diagram import load_waveform, resolve_signal_key, sanitize_waveform  # noqa: E402
from run_edge_family_stress_crossflow import format_channel, StressCase  # noqa: E402


XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")
NGSPICE = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")
OUT_DIR = ROOT / "results" / "pybis_spike_trend_sweep_2026-05-12"

UI = 2e-9
TR = 200e-12
VLO = 0.0
VHI = 3.3
STEP = 10e-12
SKIP_LEAD = 4
TAIL_ZEROS = 4


@dataclass(frozen=True)
class PatternCase:
    key: str
    pre_high: int
    low_gap: int
    post_high: int
    channel: StressCase

    @property
    def states(self) -> list[int]:
        return (
            [0] * SKIP_LEAD
            + [1] * self.pre_high
            + [0] * self.low_gap
            + [1] * self.post_high
            + [0] * TAIL_ZEROS
        )

    @property
    def stop_s(self) -> float:
        return len(self.states) * UI

    @property
    def target_rise_s(self) -> float:
        return (SKIP_LEAD + self.pre_high + self.low_gap) * UI + 0.5 * TR

    @property
    def target_fall_s(self) -> float:
        return (
            SKIP_LEAD + self.pre_high + self.low_gap + self.post_high
        ) * UI + 0.5 * TR


def rel(path: Path, cwd: Path) -> str:
    return Path(os.path.relpath(path.resolve(), cwd.resolve())).as_posix()


def pwl_source(states: list[int], node: str) -> str:
    rows: list[tuple[float, float]] = []
    v_prev = VHI if states[0] else VLO
    rows.append((0.0, v_prev))
    for i, state in enumerate(states):
        v_next = VHI if state else VLO
        t_start = i * UI
        if v_next != v_prev:
            if rows[-1][0] < t_start - 1e-15:
                rows.append((t_start, v_prev))
            rows.append((t_start + TR, v_next))
        elif rows[-1][0] < t_start - 1e-15:
            rows.append((t_start, v_prev))
        v_prev = v_next
    t_final = len(states) * UI
    if rows[-1][0] < t_final - 1e-15:
        rows.append((t_final, v_prev))

    lines = [f"Vstim {node} 0 PWL({rows[0][0]:.9e} {rows[0][1]:.4f}"]
    for i, (t_val, v_val) in enumerate(rows[1:], 1):
        suffix = ")" if i == len(rows) - 1 else ""
        lines.append(f"+ {t_val:.9e} {v_val:.4f}{suffix}")
    return "\n".join(lines)


def ensure_ngspice_edge50_model() -> Path:
    model_dir = OUT_DIR / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    out_model = model_dir / "driver_OutputInput_Typical_relaxed92_edge50_tailflat4p2_ngspice_syntax.sub"
    src = ROOT / "xyce_pybis" / "driver_OutputInput_Typical_xyce_relaxed92_edge50_tailflat4p2.sub"
    lines = []
    for line in src.read_text(encoding="ascii").splitlines():
        if line.startswith("B") and " V={" in line and line.rstrip().endswith("}"):
            line = line.replace(" V={", " V = ", 1)
            line = line.rstrip()[:-1]
        line = line.replace("table(", "pwl(")
        lines.append(line)
    out_model.write_text("\n".join(lines) + "\n", encoding="ascii")
    return out_model


def make_xyce_ref_deck(case: PatternCase, cwd: Path) -> str:
    stop = f"{case.stop_s:.9e}"
    step = f"{STEP:.9e}"
    return f"""* {case.key} / Xyce refspice
{pwl_source(case.states, "in_src")}
Rin    in_src  in_dig  1

Vdd_ref  vdd_ref_src  0  DC 3.3
Voe_ref  oe_ref_src   0  DC 3.3
Rvdd_ref vdd_ref_src  vdd_ref  1
Roe_ref  oe_ref_src   oe_ref   1
Cdec_ref vdd_ref      0        10p

.subckt SPICE_BUF in oe out in_sense vdd vss
.include '{rel(ROOT / "models" / "hspice_ngspice.mod", cwd)}'
.include '{rel(ROOT / "models" / "io_buf.sp", cwd)}'
.ends SPICE_BUF

XREF in_dig oe_ref pad_ref in_sense_ref vdd_ref 0 SPICE_BUF
RCH_TX  pad_ref tx_out 1u
{format_channel(case.channel, "xyce")}
RTERM   n10b 0 50

.ic V(pad_ref)=0 V(tx_out)=0 V(n10b)=0
.options output initial_interval=10p
.tran {step} {stop} uic
.print tran format=csv time V(in_dig) V(pad_ref) V(tx_out) V(n10b)
.end
"""


def make_xyce_pybis_deck(case: PatternCase, cwd: Path) -> str:
    stop = f"{case.stop_s:.9e}"
    step = f"{STEP:.9e}"
    return f"""* {case.key} / Xyce pybis edge50
{pwl_source(case.states, "in_dig")}
Ven   en_sig  0  DC 3.3
Vdd   vdd     0  DC 3.3

.include '{rel(ROOT / "xyce_pybis" / "driver_OutputInput_Typical_xyce_relaxed92_edge50_tailflat4p2.sub", cwd)}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
RCH_TX  pad tx_out 1u
{format_channel(case.channel, "xyce")}
RTERM   n10b 0 50

.ic V(pad)=0 V(tx_out)=0 V(n10b)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
.options timeint method=gear maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1
.options output initial_interval=10p
.tran {step} {stop} uic
.print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)
.end
"""


def make_ngspice_pybis_deck(case: PatternCase, cwd: Path, model: Path) -> str:
    stop = f"{case.stop_s:.9e}"
    step = f"{STEP:.9e}"
    return f"""* {case.key} / corrected ngspice pybis edge50
.temp 27
.options method=gear maxord=1 reltol=1e-3 abstol=1e-3 vntol=1e-4 gmin=1e-12 itl4=50 itl5=0 trtol=7
{pwl_source(case.states, "in_dig")}
Ven    en_sig  0  DC 3.3
Vdd    vdd     0  DC 3.3

.include '{rel(model, cwd)}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical
RCH_TX  pad tx_out 1u
{format_channel(case.channel, "ngspice")}
RTERM   n10b 0 50

.save V(in_dig) V(pad) V(tx_out) V(n10b)
.tran {step} {stop}
.end
"""


def run_xyce(deck: Path, timeout_s: float = 90.0) -> tuple[int | str, bool, float]:
    start = time.time()
    try:
        proc = subprocess.run(
            [str(XYCE), deck.name],
            cwd=deck.parent,
            timeout=timeout_s,
            capture_output=True,
            text=True,
        )
        rc: int | str = proc.returncode
        timed_out = False
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc = "timeout"
        timed_out = True
        stdout, stderr = exc.stdout or "", exc.stderr or ""
    wall = time.time() - start
    deck.with_suffix(deck.suffix + ".log").write_text(
        f"COMMAND: {XYCE} {deck.name}\nRETURN_CODE: {rc}\nTIMED_OUT: {timed_out}\n"
        f"WALL_SECONDS: {wall:.3f}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
        encoding="utf-8",
    )
    return rc, timed_out, wall


def run_ngspice(deck: Path, raw: Path, timeout_s: float = 90.0) -> tuple[int | str, bool, float]:
    start = time.time()
    try:
        proc = subprocess.run(
            [str(NGSPICE), "-b", "-r", raw.name, deck.name],
            cwd=deck.parent,
            timeout=timeout_s,
            capture_output=True,
            text=True,
        )
        rc: int | str = proc.returncode
        timed_out = False
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc = "timeout"
        timed_out = True
        stdout, stderr = exc.stdout or "", exc.stderr or ""
    wall = time.time() - start
    deck.with_suffix(deck.suffix + ".log").write_text(
        f"COMMAND: {NGSPICE} -b -r {raw.name} {deck.name}\nRETURN_CODE: {rc}\nTIMED_OUT: {timed_out}\n"
        f"WALL_SECONDS: {wall:.3f}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
        encoding="utf-8",
    )
    return rc, timed_out, wall


def load_signal(path: Path, fmt: str, signal: str) -> tuple[np.ndarray, np.ndarray]:
    data = load_waveform(path, fmt)
    key = resolve_signal_key(data, signal)
    return sanitize_waveform(data["time"], data[key])


def window_stats(
    time: np.ndarray,
    voltage: np.ndarray,
    x0: float,
    x1: float,
) -> dict[str, float]:
    mask = (time >= x0) & (time <= x1)
    if not np.any(mask):
        return {"max_v": np.nan, "max_t": np.nan, "min_v": np.nan, "min_t": np.nan}
    t = time[mask]
    v = voltage[mask]
    imax = int(np.argmax(v))
    imin = int(np.argmin(v))
    return {
        "max_v": float(v[imax]),
        "max_t": float(t[imax]),
        "min_v": float(v[imin]),
        "min_t": float(t[imin]),
    }


def analyze_case(case: PatternCase, run_dir: Path) -> dict[str, object]:
    ref_path = run_dir / "xyce_ref" / f"{case.key}_xyce_ref.cir.csv"
    py_path = run_dir / "xyce_pybis" / f"{case.key}_xyce_pybis.cir.csv"
    t_ref, v_ref = load_signal(ref_path, "xyce", "v(n10b)")
    t_py, v_py = load_signal(py_path, "xyce", "v(n10b)")
    t_py_tx, v_py_tx = load_signal(py_path, "xyce", "v(tx_out)")
    t_ref_tx, v_ref_tx = load_signal(ref_path, "xyce", "v(tx_out)")

    rise_x0 = case.target_rise_s
    rise_x1 = rise_x0 + 1.4e-9
    fall_x0 = case.target_fall_s
    fall_x1 = fall_x0 + 1.4e-9
    grid = np.arange(rise_x0, rise_x1, 2e-12)
    ref_i = np.interp(grid, t_ref, v_ref)
    py_i = np.interp(grid, t_py, v_py)
    diff = py_i - ref_i
    j = int(np.argmax(np.abs(diff)))
    py_rise = window_stats(t_py, v_py, rise_x0, rise_x1)
    ref_rise = window_stats(t_ref, v_ref, rise_x0, rise_x1)
    py_tx_rise = window_stats(t_py_tx, v_py_tx, rise_x0, rise_x1)
    ref_tx_rise = window_stats(t_ref_tx, v_ref_tx, rise_x0, rise_x1)

    grid_f = np.arange(fall_x0, fall_x1, 2e-12)
    ref_f = np.interp(grid_f, t_ref, v_ref)
    py_f = np.interp(grid_f, t_py, v_py)
    fdiff = py_f - ref_f
    jf = int(np.argmax(np.abs(fdiff)))
    py_fall = window_stats(t_py, v_py, fall_x0, fall_x1)
    ref_fall = window_stats(t_ref, v_ref, fall_x0, fall_x1)

    return {
        "case": case.key,
        "pre_high": case.pre_high,
        "low_gap": case.low_gap,
        "post_high": case.post_high,
        "length_cm": case.channel.length_scale * 10,
        "loss_scale": case.channel.loss_scale,
        "n_sections": case.channel.n_sections,
        "target_rise_ns": case.target_rise_s * 1e9,
        "target_fall_ns": case.target_fall_s * 1e9,
        "py_rise_max_v": py_rise["max_v"],
        "py_rise_max_ns": py_rise["max_t"] * 1e9,
        "ref_rise_max_v": ref_rise["max_v"],
        "ref_rise_max_ns": ref_rise["max_t"] * 1e9,
        "rise_maxabs_py_minus_ref_v": float(diff[j]),
        "rise_maxabs_py_minus_ref_abs_v": float(abs(diff[j])),
        "rise_maxabs_ns": float(grid[j] * 1e9),
        "py_tx_rise_max_v": py_tx_rise["max_v"],
        "ref_tx_rise_max_v": ref_tx_rise["max_v"],
        "py_fall_min_v": py_fall["min_v"],
        "ref_fall_min_v": ref_fall["min_v"],
        "fall_maxabs_py_minus_ref_v": float(fdiff[jf]),
        "fall_maxabs_py_minus_ref_abs_v": float(abs(fdiff[jf])),
        "fall_maxabs_ns": float(grid_f[jf] * 1e9),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_case(case: PatternCase) -> dict[str, object]:
    run_dir = OUT_DIR / "runs" / case.key
    ref_dir = run_dir / "xyce_ref"
    py_dir = run_dir / "xyce_pybis"
    ref_dir.mkdir(parents=True, exist_ok=True)
    py_dir.mkdir(parents=True, exist_ok=True)
    ref_deck = ref_dir / f"{case.key}_xyce_ref.cir"
    py_deck = py_dir / f"{case.key}_xyce_pybis.cir"
    ref_deck.write_text(make_xyce_ref_deck(case, ref_dir), encoding="ascii")
    py_deck.write_text(make_xyce_pybis_deck(case, py_dir), encoding="ascii")
    ref_csv = Path(str(ref_deck) + ".csv")
    py_csv = Path(str(py_deck) + ".csv")
    ref_csv.unlink(missing_ok=True)
    py_csv.unlink(missing_ok=True)
    rc_ref, to_ref, wall_ref = run_xyce(ref_deck)
    rc_py, to_py, wall_py = run_xyce(py_deck)
    row: dict[str, object] = {
        "case": case.key,
        "xyce_ref_rc": rc_ref,
        "xyce_ref_timed_out": to_ref,
        "xyce_ref_wall_s": wall_ref,
        "xyce_pybis_rc": rc_py,
        "xyce_pybis_timed_out": to_py,
        "xyce_pybis_wall_s": wall_py,
        "xyce_ref_output": ref_csv.exists(),
        "xyce_pybis_output": py_csv.exists(),
    }
    if rc_ref == 0 and rc_py == 0 and ref_csv.exists() and py_csv.exists():
        row.update(analyze_case(case, run_dir))
    return row


def plot_fixed_channel(rows: list[dict[str, object]]) -> None:
    plot_dir = OUT_DIR / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    fixed = [r for r in rows if r.get("length_cm") == 30 and r.get("loss_scale") == 5.0]
    post_values = sorted({int(r["post_high"]) for r in fixed})
    fig, axes = plt.subplots(1, len(post_values), figsize=(5.0 * len(post_values), 4.4), sharey=True)
    if len(post_values) == 1:
        axes = [axes]
    for ax, post in zip(axes, post_values):
        sub = [r for r in fixed if int(r["post_high"]) == post]
        pre_vals = sorted({int(r["pre_high"]) for r in sub})
        gap_vals = sorted({int(r["low_gap"]) for r in sub})
        z = np.full((len(pre_vals), len(gap_vals)), np.nan)
        for r in sub:
            i = pre_vals.index(int(r["pre_high"]))
            j = gap_vals.index(int(r["low_gap"]))
            z[i, j] = float(r["rise_maxabs_py_minus_ref_abs_v"])
        im = ax.imshow(z, origin="lower", aspect="auto", cmap="magma", vmin=0, vmax=np.nanmax(z))
        ax.set_xticks(range(len(gap_vals)), [str(v) for v in gap_vals])
        ax.set_yticks(range(len(pre_vals)), [str(v) for v in pre_vals])
        ax.set_xlabel("Low gap before target rise (UI)")
        ax.set_title(f"Post-high run = {post} UI")
        for i in range(len(pre_vals)):
            for j in range(len(gap_vals)):
                ax.text(j, i, f"{z[i, j]:.2f}", ha="center", va="center", color="white", fontsize=8)
    axes[0].set_ylabel("Previous high run (UI)")
    fig.colorbar(im, ax=axes, label="Max |pybis-ref| after rise (V)")
    fig.suptitle("Spike strength vs local bit history, 30 cm coarse RLGC loss x5")
    fig.savefig(plot_dir / "fixed_channel_spike_history_heatmap.png", dpi=180)
    plt.close(fig)


def plot_channel(rows: list[dict[str, object]]) -> None:
    plot_dir = OUT_DIR / "plots"
    channel_rows = [r for r in rows if str(r["case"]).startswith("ch_")]
    if not channel_rows:
        return
    lengths = sorted({int(r["length_cm"]) for r in channel_rows})
    losses = sorted({float(r["loss_scale"]) for r in channel_rows})
    z = np.full((len(losses), len(lengths)), np.nan)
    for r in channel_rows:
        i = losses.index(float(r["loss_scale"]))
        j = lengths.index(int(r["length_cm"]))
        z[i, j] = float(r["rise_maxabs_py_minus_ref_abs_v"])
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    im = ax.imshow(z, origin="lower", aspect="auto", cmap="viridis", vmin=0, vmax=np.nanmax(z))
    ax.set_xticks(range(len(lengths)), [str(v) for v in lengths])
    ax.set_yticks(range(len(losses)), [str(v) for v in losses])
    ax.set_xlabel("Channel length (cm)")
    ax.set_ylabel("Loss scale")
    for i in range(len(losses)):
        for j in range(len(lengths)):
            ax.text(j, i, f"{z[i, j]:.2f}", ha="center", va="center", color="white", fontsize=9)
    fig.colorbar(im, ax=ax, label="Max |pybis-ref| after rise (V)")
    ax.set_title("Spike strength for 1UI high / 1UI low / 3UI high pattern")
    fig.tight_layout()
    fig.savefig(plot_dir / "channel_spike_strength_heatmap.png", dpi=180)
    plt.close(fig)


def validate_ngspice(selected: list[PatternCase], rows: list[dict[str, object]]) -> None:
    model = ensure_ngspice_edge50_model()
    out_rows = []
    for case in selected:
        run_dir = OUT_DIR / "runs" / case.key / "ngspice_pybis_corrected"
        run_dir.mkdir(parents=True, exist_ok=True)
        deck = run_dir / f"{case.key}_ngspice_pybis_corrected.sp"
        raw = run_dir / f"{case.key}_ngspice_pybis_corrected.raw"
        deck.write_text(make_ngspice_pybis_deck(case, run_dir, model), encoding="ascii")
        raw.unlink(missing_ok=True)
        rc, timed_out, wall = run_ngspice(deck, raw)
        row = {
            "case": case.key,
            "pre_high": case.pre_high,
            "low_gap": case.low_gap,
            "post_high": case.post_high,
            "ngspice_rc": rc,
            "ngspice_timed_out": timed_out,
            "ngspice_wall_s": wall,
            "ngspice_output": raw.exists(),
        }
        if rc == 0 and raw.exists():
            t_ng, v_ng = load_signal(raw, "ngspice", "v(n10b)")
            py_path = OUT_DIR / "runs" / case.key / "xyce_pybis" / f"{case.key}_xyce_pybis.cir.csv"
            t_xy, v_xy = load_signal(py_path, "xyce", "v(n10b)")
            x0 = case.target_rise_s
            x1 = x0 + 1.4e-9
            grid = np.arange(x0, x1, 2e-12)
            ng_i = np.interp(grid, t_ng, v_ng)
            xy_i = np.interp(grid, t_xy, v_xy)
            d = ng_i - xy_i
            row.update(
                {
                    "ng_xy_rise_rmse_v": float(np.sqrt(np.mean(d * d))),
                    "ng_xy_rise_maxabs_v": float(np.max(np.abs(d))),
                }
            )
        out_rows.append(row)
    write_csv(OUT_DIR / "ngspice_validation.csv", out_rows)


def main() -> int:
    if not XYCE.exists():
        raise FileNotFoundError(XYCE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "plots").mkdir(exist_ok=True)

    fixed_channel = StressCase(
        "sweep_30cm_loss5_coarse10",
        UI,
        3,
        5.0,
        "2 ns UI, 30 cm channel, R/G loss x5, 10 coarse sections",
        n_sections_override=10,
    )
    cases: list[PatternCase] = []
    for pre in [1, 2, 3, 4]:
        for gap in [1, 2, 3, 4]:
            for post in [1, 2, 3, 4]:
                cases.append(
                    PatternCase(
                        f"hist_h{pre}_g{gap}_p{post}_30cm_loss5",
                        pre,
                        gap,
                        post,
                        fixed_channel,
                    )
                )

    # Channel dependence for the strongest-history pattern.
    for length_scale in [1, 2, 3]:
        for loss in [1.0, 3.0, 5.0]:
            channel = StressCase(
                f"ch_{length_scale * 10}cm_loss{loss:g}_coarse10",
                UI,
                length_scale,
                loss,
                f"2 ns UI, {length_scale * 10} cm, loss x{loss:g}, 10 coarse sections",
                n_sections_override=10,
            )
            cases.append(
                PatternCase(
                    f"ch_len{length_scale * 10}cm_loss{loss:g}_h1_g1_p3",
                    1,
                    1,
                    3,
                    channel,
                )
            )

    rows = []
    for idx, case in enumerate(cases, 1):
        print(f"[{idx:03d}/{len(cases):03d}] {case.key}", flush=True)
        rows.append(run_case(case))
        write_csv(OUT_DIR / "spike_trend_summary_partial.csv", rows)

    write_csv(OUT_DIR / "spike_trend_summary.csv", rows)
    plot_fixed_channel(rows)
    plot_channel(rows)

    selected = [
        PatternCase("hist_h1_g1_p3_30cm_loss5", 1, 1, 3, fixed_channel),
        PatternCase("hist_h1_g2_p3_30cm_loss5", 1, 2, 3, fixed_channel),
        PatternCase("hist_h1_g4_p3_30cm_loss5", 1, 4, 3, fixed_channel),
        PatternCase("hist_h3_g1_p3_30cm_loss5", 3, 1, 3, fixed_channel),
    ]
    if NGSPICE.exists():
        validate_ngspice(selected, rows)

    (OUT_DIR / "README.md").write_text(
        "\n".join(
            [
                "# Pybis Spike Trend Sweep",
                "",
                "Pattern family: `0000 + 1*pre_high + 0*low_gap + 1*post_high + 0000`.",
                "",
                "Main sweep uses the same stressed channel as the corrected PRBS run:",
                "2 ns UI, 30 cm coarse10 RLGC, loss x5.",
                "",
                "Outputs:",
                "",
                "- `spike_trend_summary.csv`: per-pattern metrics.",
                "- `ngspice_validation.csv`: corrected ngspice pybis validation on selected patterns.",
                "- `plots/fixed_channel_spike_history_heatmap.png`: history dependence.",
                "- `plots/channel_spike_strength_heatmap.png`: length/loss dependence.",
            ]
        )
        + "\n",
        encoding="ascii",
    )
    print(f"Wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
