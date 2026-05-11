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

XYCE_EXE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")
NGSPICE_EXE = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")

XYCE_TIMEINT = ".options timeint method=trap maxord=1 erroption=1 delmax=20p nlmin=3 nlmax=8 timestepsreversal=1"
XYCE_OUTPUT = ".options output initial_interval=10p"


@dataclass(frozen=True)
class Stimulus:
    name: str
    title: str
    source: str
    stop: str
    end_ns: float


@dataclass(frozen=True)
class Variant:
    name: str
    title: str
    include_file: str
    factor: int


STIMULI = [
    Stimulus(
        name="pulse5p",
        title="SPISim pulse, 5 ps edges",
        source="PULSE(0 3.3 1n 5p 5p 1.5n 3n)",
        stop="20n",
        end_ns=20.0,
    ),
    Stimulus(
        name="pulse200p",
        title="Practical pulse, 200 ps edges",
        source="PULSE(0 3.3 1n 200p 200p 1.5n 3n)",
        stop="20n",
        end_ns=20.0,
    ),
    Stimulus(
        name="rfr5p",
        title="Rise-fall-rise, 5 ps edges",
        source="PWL(0 0 1n 0 1.005n 3.3 9n 3.3 9.005n 0 17n 0 17.005n 3.3 25n 3.3 25.005n 0)",
        stop="26n",
        end_ns=26.0,
    ),
    Stimulus(
        name="rfr200p",
        title="Rise-fall-rise, 200 ps edges",
        source="PWL(0 0 1n 0 1.2n 3.3 9n 3.3 9.2n 0 17n 0 17.2n 3.3 25n 3.3 25.2n 0)",
        stop="26n",
        end_ns=26.0,
    ),
]

VARIANTS = [
    Variant("direct", "direct tanh200", "driver_OutputInput_Typical.sub", 200),
    Variant("tanh92", "tanh92", "driver_OutputInput_Typical_xyce_relaxed92.sub", 92),
    Variant("tanh50", "tanh50", "driver_OutputInput_Typical_xyce_relaxed50.sub", 50),
    Variant("tanh20", "tanh20", "driver_OutputInput_Typical_xyce_relaxed.sub", 20),
    Variant("tanh15", "tanh15", "driver_OutputInput_Typical_xyce_relaxed15.sub", 15),
]


def ns(v):
    return v * 1e9


def clean_key(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()


def xyce_deck_path(stim: Stimulus, variant: Variant) -> Path:
    return XYCE_DIR / f"tb_spisim_val_{stim.name}_xyce_{variant.name}_be.cir"


def xyce_csv_path(stim: Stimulus, variant: Variant) -> Path:
    return Path(str(xyce_deck_path(stim, variant)) + ".csv")


def ngspice_deck_path(stim: Stimulus) -> Path:
    return NGSPICE_DIR / f"tb_spisim_val_{stim.name}_ngspice_pybis.sp"


def ngspice_raw_path(stim: Stimulus) -> Path:
    return NGSPICE_DIR / f"tb_spisim_val_{stim.name}_ngspice_pybis.raw"


def write_ngspice_deck(stim: Stimulus) -> Path:
    path = ngspice_deck_path(stim)
    path.write_text(
        f"""* Generated SPISim-style pybis validation bench: {stim.title}

.temp 27
.options method=gear maxord=2 reltol=1e-4 abstol=1e-10 vntol=1e-6 gmin=1e-12

Vin   in_dig   0  {stim.source}
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include 'driver_OutputInput_Typical.sub'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

TVAL  pad  0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0  50

.save V(in_dig) V(pad) V(ntst) V(xdrv.ku) V(xdrv.kd)
.tran 10p {stim.stop}
.end
""",
        encoding="ascii",
    )
    return path


def write_xyce_deck(stim: Stimulus, variant: Variant) -> Path:
    path = xyce_deck_path(stim, variant)
    path.write_text(
        f"""* Generated SPISim-style Xyce pybis validation bench: {stim.title}
* Variant: {variant.title}

Vin   in_dig   0  {stim.source}
Ven   en_sig   0  DC 3.3
Vdd   vdd      0  DC 3.3

.include '{variant.include_file}'
XDRV  pad  in_dig  en_sig  vdd  0  driver_OutputInput_Typical

TVAL  pad  0  ntst  0  Z0=50 Td=30p
RLOAD ntst 0  50

.ic V(pad)=0 V(ntst)=0 V(XDRV:Ku)=0 V(XDRV:Kd)=1 V(XDRV:NX)=0 V(XDRV:N6)=0 V(XDRV:N8)=0
{XYCE_TIMEINT}
{XYCE_OUTPUT}
.tran 10p {stim.stop} uic
.print tran format=csv time V(in_dig) V(pad) V(ntst) V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX) I(Vdd)
.end
""",
        encoding="ascii",
    )
    return path


def load_xyce_csv(path: Path):
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


def load_ngspice_raw(path: Path):
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


def col(data, name: str):
    key = name.lower()
    if key not in data:
        raise KeyError(f"{name} not in {sorted(data)}")
    return data[key]


def run_process(cmd, cwd: Path, timeout_s: float):
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout_s,
            capture_output=True,
            text=True,
        )
        return proc.returncode, round(time.time() - t0, 2), False
    except subprocess.TimeoutExpired:
        return None, round(time.time() - t0, 2), True


def run_ngspice(stim: Stimulus, timeout_s: float, dry_run: bool):
    deck = write_ngspice_deck(stim)
    raw = ngspice_raw_path(stim)
    if dry_run:
        return raw.exists(), 0.0, False
    raw.unlink(missing_ok=True)
    rc, wall_s, timed_out = run_process(
        [str(NGSPICE_EXE), "-b", "-r", str(raw.name), str(deck.name)],
        NGSPICE_DIR,
        timeout_s,
    )
    return rc == 0 and raw.exists(), wall_s, timed_out


def run_xyce(stim: Stimulus, variant: Variant, timeout_s: float, dry_run: bool):
    deck = write_xyce_deck(stim, variant)
    csv_path = xyce_csv_path(stim, variant)
    if dry_run:
        return csv_path.exists(), 0.0, False
    csv_path.unlink(missing_ok=True)
    rc, wall_s, timed_out = run_process([str(XYCE_EXE), str(deck.name)], XYCE_DIR, timeout_s)
    return rc == 0 and csv_path.exists(), wall_s, timed_out


def summarize_xyce(stim: Stimulus, variant: Variant, ng_data, run_ok: bool, wall_s: float, timed_out: bool):
    path = xyce_csv_path(stim, variant)
    row = {
        "simulator": "xyce",
        "stimulus": stim.name,
        "stimulus_title": stim.title,
        "variant": variant.name,
        "variant_title": variant.title,
        "relaxation_factor": variant.factor,
        "target_end_ns": stim.end_ns,
        "run_ok": run_ok,
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(path.relative_to(ROOT)).replace("\\", "/").replace(".csv", ""),
        "output": str(path.relative_to(ROOT)).replace("\\", "/"),
    }
    try:
        d = load_xyce_csv(path)
        t = col(d, "time")
        ntst = col(d, "v(ntst)")
        pad = col(d, "v(pad)")
        row.update(
            {
                "rows": len(t),
                "t_end_ns": float(ns(t[-1])),
                "completed": float(ns(t[-1])) >= stim.end_ns - 0.05,
                "ntst_min": float(np.min(ntst)),
                "ntst_max": float(np.max(ntst)),
                "pad_min": float(np.min(pad)),
                "pad_max": float(np.max(pad)),
                "ku_min": float(np.min(col(d, "v(xdrv:ku)"))),
                "ku_max": float(np.max(col(d, "v(xdrv:ku)"))),
                "kd_min": float(np.min(col(d, "v(xdrv:kd)"))),
                "kd_max": float(np.max(col(d, "v(xdrv:kd)"))),
                "nx_max": float(np.max(col(d, "v(xdrv:nx)"))),
            }
        )
        ng_t = ns(col(ng_data, "time"))
        ng_ntst = col(ng_data, "v(ntst)")
        ng_pad = col(ng_data, "v(pad)")
        xy_t = ns(t)
        lo = max(float(ng_t[0]), float(xy_t[0]))
        hi = min(float(ng_t[-1]), float(xy_t[-1]))
        if hi > lo:
            sample_t = np.linspace(lo, hi, 2500)
            ng_ntst_i = np.interp(sample_t, ng_t, ng_ntst)
            xy_ntst_i = np.interp(sample_t, xy_t, ntst)
            ng_pad_i = np.interp(sample_t, ng_t, ng_pad)
            xy_pad_i = np.interp(sample_t, xy_t, pad)
            row.update(
                {
                    "compare_end_ns": hi,
                    "ntst_rmse_vs_ngspice_v": float(np.sqrt(np.mean((xy_ntst_i - ng_ntst_i) ** 2))),
                    "ntst_max_delta_vs_ngspice_v": float(np.max(ntst) - np.max(ng_ntst)),
                    "pad_rmse_vs_ngspice_v": float(np.sqrt(np.mean((xy_pad_i - ng_pad_i) ** 2))),
                    "pad_max_delta_vs_ngspice_v": float(np.max(pad) - np.max(ng_pad)),
                }
            )
    except Exception as exc:
        row.update({"completed": False, "error": str(exc)})
    return row


def summarize_ngspice(stim: Stimulus, run_ok: bool, wall_s: float, timed_out: bool):
    path = ngspice_raw_path(stim)
    row = {
        "simulator": "ngspice",
        "stimulus": stim.name,
        "stimulus_title": stim.title,
        "variant": "baseline",
        "variant_title": "ngspice direct pybis",
        "relaxation_factor": 200,
        "target_end_ns": stim.end_ns,
        "run_ok": run_ok,
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(ngspice_deck_path(stim).relative_to(ROOT)).replace("\\", "/"),
        "output": str(path.relative_to(ROOT)).replace("\\", "/"),
    }
    try:
        d = load_ngspice_raw(path)
        t = col(d, "time")
        ntst = col(d, "v(ntst)")
        pad = col(d, "v(pad)")
        row.update(
            {
                "rows": len(t),
                "t_end_ns": float(ns(t[-1])),
                "completed": float(ns(t[-1])) >= stim.end_ns - 0.05,
                "ntst_min": float(np.min(ntst)),
                "ntst_max": float(np.max(ntst)),
                "pad_min": float(np.min(pad)),
                "pad_max": float(np.max(pad)),
                "ku_min": float(np.min(col(d, "v(xdrv.ku)"))),
                "ku_max": float(np.max(col(d, "v(xdrv.ku)"))),
                "kd_min": float(np.min(col(d, "v(xdrv.kd)"))),
                "kd_max": float(np.max(col(d, "v(xdrv.kd)"))),
            }
        )
        if "v(xdrv.nx)" in d:
            row["nx_max"] = float(np.max(col(d, "v(xdrv.nx)")))
    except Exception as exc:
        row.update({"completed": False, "error": str(exc)})
    return row


def write_metrics(rows):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path = OUT_DIR / "xyce_pybis_spisim_tline_validation_metrics.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(path)
    return path


def plot_overlays():
    colors = {
        "direct": "#d62728",
        "tanh92": "#9467bd",
        "tanh50": "#ff7f0e",
        "tanh20": "#2ca02c",
        "tanh15": "#17becf",
    }
    fig, axes = plt.subplots(len(STIMULI), 1, figsize=(11.5, 11), sharex=False)
    for ax, stim in zip(axes, STIMULI):
        ng = load_ngspice_raw(ngspice_raw_path(stim))
        ng_t = ns(col(ng, "time"))
        ax.plot(ng_t, col(ng, "v(ntst)"), color="black", lw=1.5, label="ngspice baseline")
        for variant in VARIANTS:
            path = xyce_csv_path(stim, variant)
            if not path.exists():
                continue
            try:
                xy = load_xyce_csv(path)
            except Exception:
                continue
            xy_t = ns(col(xy, "time"))
            label = variant.title
            ls = "-" if xy_t[-1] >= stim.end_ns - 0.05 else "--"
            ax.plot(
                xy_t,
                col(xy, "v(ntst)"),
                lw=1.0,
                alpha=0.88,
                color=colors.get(variant.name),
                ls=ls,
                label=label,
            )
        ax.set_title(stim.title)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("V(ntst) (V)")
        ax.grid(True, alpha=0.28)
        ax.legend(loc="best", fontsize=8, ncol=2)
    fig.tight_layout()
    path = OUT_DIR / "xyce_pybis_spisim_tline_validation_overlay.png"
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(path)


def plot_matrix(metrics_rows):
    xy_rows = [r for r in metrics_rows if r["simulator"] == "xyce"]
    stimuli = [s.name for s in STIMULI]
    variants = [v.name for v in VARIANTS]
    end = np.full((len(stimuli), len(variants)), np.nan)
    rmse = np.full_like(end, np.nan, dtype=float)
    complete = np.zeros_like(end, dtype=bool)
    for row in xy_rows:
        i = stimuli.index(row["stimulus"])
        j = variants.index(row["variant"])
        end[i, j] = float(row.get("t_end_ns") or np.nan)
        rmse[i, j] = float(row.get("ntst_rmse_vs_ngspice_v") or np.nan)
        complete[i, j] = bool(row.get("completed"))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    im = axes[0].imshow(end, aspect="auto", cmap="viridis")
    axes[0].set_title("Completed Time (ns)")
    axes[0].set_xticks(range(len(variants)), [v.title for v in VARIANTS], rotation=35, ha="right")
    axes[0].set_yticks(range(len(stimuli)), [s.title for s in STIMULI])
    for i in range(len(stimuli)):
        for j in range(len(variants)):
            if np.isnan(end[i, j]):
                text = "no data"
            else:
                text = f"{end[i, j]:.1f}"
                if not complete[i, j]:
                    text += "*"
            axes[0].text(j, i, text, ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)

    im2 = axes[1].imshow(rmse * 1e3, aspect="auto", cmap="magma_r")
    axes[1].set_title("V(ntst) RMSE vs ngspice (mV)")
    axes[1].set_xticks(range(len(variants)), [v.title for v in VARIANTS], rotation=35, ha="right")
    axes[1].set_yticks(range(len(stimuli)), [s.title for s in STIMULI])
    for i in range(len(stimuli)):
        for j in range(len(variants)):
            if not np.isnan(rmse[i, j]):
                axes[1].text(j, i, f"{rmse[i, j] * 1e3:.1f}", ha="center", va="center", color="black", fontsize=8)
    fig.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)
    fig.tight_layout()
    path = OUT_DIR / "xyce_pybis_spisim_tline_validation_matrix.png"
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(path)


def main():
    parser = argparse.ArgumentParser(description="Run SPISim-style pybis validation benches in ngspice and Xyce.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-simulation timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Do not run simulators; rebuild plots/CSV from existing data.")
    parser.add_argument("--skip-ngspice", action="store_true", help="Reuse existing ngspice raw files.")
    parser.add_argument("--skip-xyce", action="store_true", help="Reuse existing Xyce CSV files.")
    args = parser.parse_args()

    if not args.dry_run and not args.skip_xyce:
        if not XYCE_EXE.exists():
            raise SystemExit(f"Xyce not found: {XYCE_EXE}")
    if not args.dry_run and not args.skip_ngspice:
        if not NGSPICE_EXE.exists():
            raise SystemExit(f"ngspice not found: {NGSPICE_EXE}")

    rows = []
    ng_data_by_stim = {}

    for stim in STIMULI:
        if args.skip_ngspice:
            write_ngspice_deck(stim)
            raw = ngspice_raw_path(stim)
            ok, wall_s, timed_out = raw.exists(), 0.0, False
        else:
            ok, wall_s, timed_out = run_ngspice(stim, args.timeout, args.dry_run)
        ng_row = summarize_ngspice(stim, ok, wall_s, timed_out)
        rows.append(ng_row)
        ng_data_by_stim[stim.name] = load_ngspice_raw(ngspice_raw_path(stim))
        status = "PASS" if ng_row.get("completed") else "PARTIAL"
        print(f"ngspice {stim.name:<9} {status:<7} t_end={ng_row.get('t_end_ns', 0):.3f} ns wall={wall_s:.2f}s")

    for stim in STIMULI:
        ng_data = ng_data_by_stim[stim.name]
        for variant in VARIANTS:
            if args.skip_xyce:
                write_xyce_deck(stim, variant)
                csv_path = xyce_csv_path(stim, variant)
                ok, wall_s, timed_out = csv_path.exists(), 0.0, False
            else:
                ok, wall_s, timed_out = run_xyce(stim, variant, args.timeout, args.dry_run)
            row = summarize_xyce(stim, variant, ng_data, ok, wall_s, timed_out)
            rows.append(row)
            status = "PASS" if row.get("completed") else ("TIMEOUT" if timed_out else "PARTIAL")
            t_end = row.get("t_end_ns")
            t_end_s = f"{t_end:.3f}" if isinstance(t_end, (float, int)) else "n/a"
            rmse = row.get("ntst_rmse_vs_ngspice_v")
            rmse_s = f"{rmse * 1e3:.1f} mV" if isinstance(rmse, (float, int)) else "n/a"
            print(f"Xyce {stim.name:<9} {variant.name:<7} {status:<7} t_end={t_end_s} ns RMSE={rmse_s} wall={wall_s:.2f}s")

    write_metrics(rows)
    plot_overlays()
    plot_matrix(rows)


if __name__ == "__main__":
    main()
