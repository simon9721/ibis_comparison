from pathlib import Path
import csv
import re
import struct

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
XYCE = ROOT / "xyce_pybis"
NGSPICE = ROOT / "ngspice_pybis"
OUT = ROOT / "plots" / "xyce_pybis"


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

    payload = data[idx + len(marker):]
    if npts == 0:
        npts = len(payload) // (8 * nvars)
    values = struct.unpack("<" + "d" * (nvars * npts), payload[: 8 * nvars * npts])
    arr = np.asarray(values, dtype=float).reshape((npts, nvars))
    return {name: arr[:, i] for i, name in enumerate(variables)}


def ns(v):
    return v * 1e9


def col(data, name):
    key = name.lower()
    if key not in data:
        raise KeyError(f"{name} not in {sorted(data)}")
    return data[key]


def style(ax, title, ylabel="Voltage (V)"):
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.28)
    ax.legend(loc="best", fontsize=8)


def savefig(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(path)


def plot_rload_cases():
    cases = [
        ("Single delayed rise", XYCE / "tb_test_rise_late_xyce_uic_relaxed.cir.csv"),
        ("Fast rise/fall", XYCE / "tb_test_rfr_xyce_uic_relaxed.cir.csv"),
        ("Slow delayed rise/fall", XYCE / "tb_test_rfall_late_xyce_uic_relaxed.cir.csv"),
    ]
    fig, axes = plt.subplots(len(cases), 1, figsize=(11, 8), sharex=False)
    for ax, (title, path) in zip(axes, cases):
        d = load_xyce_csv(path)
        t = ns(col(d, "TIME"))
        ax.plot(t, col(d, "V(IN_DIG)"), label="input", lw=1.1)
        ax.plot(t, col(d, "V(PAD)"), label="pad/load", lw=1.4)
        ax2 = ax.twinx()
        ax2.plot(t, col(d, "V(XDRV:KU)"), label="Ku", color="#2ca02c", lw=0.8, alpha=0.75)
        ax2.plot(t, col(d, "V(XDRV:KD)"), label="Kd", color="#d62728", lw=0.8, alpha=0.75)
        ax2.set_ylabel("Ku/Kd")
        ax2.set_ylim(-0.15, 1.15)
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="best", fontsize=8)
        ax.set_title(title)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Voltage (V)")
        ax.grid(True, alpha=0.28)
    savefig(fig, "xyce_pybis_relaxed_rload_cases.png")


def plot_ngspice_rload_overlay():
    cases = [
        (
            "Single delayed rise",
            NGSPICE / "tb_test_rise_late.raw",
            XYCE / "tb_test_rise_late_xyce_uic_relaxed.cir.csv",
        ),
        (
            "Fast rise/fall",
            NGSPICE / "tb_test_rfr.raw",
            XYCE / "tb_test_rfr_xyce_uic_relaxed.cir.csv",
        ),
        (
            "Slow delayed rise/fall (stored ngspice raw stops early)",
            NGSPICE / "tb_test_rfall_late.raw",
            XYCE / "tb_test_rfall_late_xyce_uic_relaxed.cir.csv",
        ),
    ]
    fig, axes = plt.subplots(len(cases), 1, figsize=(11, 8), sharex=False)
    metric_rows = []
    for ax, (title, ng_path, xy_path) in zip(axes, cases):
        ng = load_ngspice_raw(ng_path)
        xy = load_xyce_csv(xy_path)
        ng_t = ns(col(ng, "time"))
        xy_t = ns(col(xy, "TIME"))
        ng_pad = col(ng, "v(pad)")
        xy_pad = col(xy, "V(PAD)")
        ax.plot(ng_t, ng_pad, label="ngspice pybis pad", lw=1.4)
        ax.plot(xy_t, xy_pad, label="Xyce relaxed pad", lw=1.0, alpha=0.9)
        ax.plot(xy_t, col(xy, "V(IN_DIG)"), label="input", lw=0.8, alpha=0.55)
        style(ax, title)

        lo = max(float(ng_t[0]), float(xy_t[0]))
        hi = min(float(ng_t[-1]), float(xy_t[-1]))
        sample_t = np.linspace(lo, hi, 2000)
        ng_i = np.interp(sample_t, ng_t, ng_pad)
        xy_i = np.interp(sample_t, xy_t, xy_pad)
        metric_rows.append({
            "case": title,
            "ngspice_t_end_ns": float(ng_t[-1]),
            "xyce_t_end_ns": float(xy_t[-1]),
            "ngspice_pad_max": float(np.max(ng_pad)),
            "xyce_pad_max": float(np.max(xy_pad)),
            "pad_max_delta": float(np.max(xy_pad) - np.max(ng_pad)),
            "pad_rmse_v": float(np.sqrt(np.mean((xy_i - ng_i) ** 2))),
        })

    savefig(fig, "xyce_vs_ngspice_pybis_rload_overlay.png")

    path = OUT / "xyce_vs_ngspice_pybis_rload_metrics.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(metric_rows[0]))
        writer.writeheader()
        writer.writerows(metric_rows)
    print(path)


def plot_channel_cases():
    cases = [
        ("Single 200 ps rise through new 50-ohm RLGC channel", XYCE / "tb_channel_rise_200p_xyce_relaxed.cir.csv"),
        ("200 ps rise/fall through new 50-ohm RLGC channel", XYCE / "tb_channel_rfr_200p_xyce_relaxed.cir.csv"),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=False)
    for ax, (title, path) in zip(axes, cases):
        d = load_xyce_csv(path)
        t = ns(col(d, "TIME"))
        ax.plot(t, col(d, "V(IN_DIG)"), label="input", lw=1.0, alpha=0.85)
        ax.plot(t, col(d, "V(PAD)"), label="driver pad", lw=1.2)
        ax.plot(t, col(d, "V(N10B)"), label="receiver n10b", lw=1.5)
        style(ax, title)
    savefig(fig, "xyce_pybis_relaxed_channel_cases.png")


def plot_pulsetrain_boundary():
    path = XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed.cir.csv"
    if not path.exists():
        return
    d = load_xyce_csv(path)
    t = ns(col(d, "TIME"))
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(t, col(d, "V(IN_DIG)"), label="input", lw=1.0)
    axes[0].plot(t, col(d, "V(PAD)"), label="driver pad", lw=1.0)
    axes[0].plot(t, col(d, "V(N10B)"), label="receiver n10b", lw=1.2)
    style(axes[0], "Pulse-train diagnostic before timeout")

    axes[1].plot(t, col(d, "V(XDRV:KU)"), label="Ku", lw=1.0)
    axes[1].plot(t, col(d, "V(XDRV:KD)"), label="Kd", lw=1.0)
    axes[1].plot(t, col(d, "V(XDRV:NX)"), label="NX", lw=1.0)
    style(axes[1], "Internal state near repeated-transition boundary", ylabel="Coefficient / ns")
    savefig(fig, "xyce_pybis_relaxed_pulsetrain_timeout.png")


def plot_twopulse_case():
    path = XYCE / "tb_channel_twopulse_200p_xyce_relaxed.cir.csv"
    if not path.exists():
        return
    d = load_xyce_csv(path)
    t = ns(col(d, "TIME"))
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(t, col(d, "V(IN_DIG)"), label="input", lw=1.0)
    axes[0].plot(t, col(d, "V(PAD)"), label="driver pad", lw=1.0)
    axes[0].plot(t, col(d, "V(N10B)"), label="receiver n10b", lw=1.2)
    style(axes[0], "Two 200 ps pulses through new 50-ohm RLGC channel")

    axes[1].plot(t, col(d, "V(XDRV:KU)"), label="Ku", lw=1.0)
    axes[1].plot(t, col(d, "V(XDRV:KD)"), label="Kd", lw=1.0)
    axes[1].plot(t, col(d, "V(XDRV:NX)"), label="NX", lw=1.0)
    style(axes[1], "Internal state with two isolated pulses", ylabel="Coefficient / ns")
    savefig(fig, "xyce_pybis_relaxed_twopulse.png")


def plot_relaxed10_pulsetrain():
    path = XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed10.cir.csv"
    if not path.exists():
        return
    d = load_xyce_csv(path)
    t = ns(col(d, "TIME"))
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(t, col(d, "V(IN_DIG)"), label="input", lw=1.0)
    axes[0].plot(t, col(d, "V(PAD)"), label="driver pad", lw=1.0)
    axes[0].plot(t, col(d, "V(N10B)"), label="receiver n10b", lw=1.2)
    style(axes[0], "Pulse train completed with tanh10 relaxed pybis model")

    axes[1].plot(t, col(d, "V(XDRV:KU)"), label="Ku", lw=1.0)
    axes[1].plot(t, col(d, "V(XDRV:KD)"), label="Kd", lw=1.0)
    axes[1].plot(t, col(d, "V(XDRV:NX)"), label="NX", lw=1.0)
    style(axes[1], "Internal state after additional transition smoothing", ylabel="Coefficient / ns")
    savefig(fig, "xyce_pybis_relaxed10_pulsetrain.png")


def plot_pulsetrain_smoothing_sweep():
    sweep = [
        (20, XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed.cir.csv"),
        (18, XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed18.cir.csv"),
        (17, XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed17.cir.csv"),
        (16, XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed16.cir.csv"),
        (15, XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed15.cir.csv"),
        (12, XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed12.cir.csv"),
        (10, XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed10.cir.csv"),
    ]
    rows = []
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=False)
    colors = plt.cm.viridis(np.linspace(0.08, 0.92, len(sweep)))

    for (factor, path), color in zip(sweep, colors):
        if not path.exists():
            continue
        d = load_xyce_csv(path)
        t = ns(col(d, "TIME"))
        n10b = col(d, "V(N10B)")
        pad = col(d, "V(PAD)")
        complete = t[-1] >= 39.999
        label = f"tanh{factor}" + ("" if complete else f" stopped {t[-1]:.1f} ns")
        axes[0].plot(t, n10b, label=label, lw=1.0, color=color, alpha=0.95)
        rows.append({
            "tanh_factor": factor,
            "complete_40ns": complete,
            "rows": len(t),
            "t_end_ns": float(t[-1]),
            "pad_min": float(np.min(pad)),
            "pad_max": float(np.max(pad)),
            "n10b_min": float(np.min(n10b)),
            "n10b_max": float(np.max(n10b)),
            "nx_min": float(np.min(col(d, "V(XDRV:NX)"))),
            "nx_max": float(np.max(col(d, "V(XDRV:NX)"))),
        })

    style(axes[0], "Repeated pulse train: receiver waveform by smoothing factor")
    axes[1].plot([r["tanh_factor"] for r in rows], [r["t_end_ns"] for r in rows], marker="o", label="final written time")
    axes[1].axhline(40, color="0.35", lw=0.9, ls="--", label="target stop time")
    axes[1].invert_xaxis()
    axes[1].set_xlabel("tanh smoothing factor")
    axes[1].set_ylabel("Final time (ns)")
    axes[1].set_title("Completion boundary for 40 ns pulse train")
    axes[1].grid(True, alpha=0.28)
    axes[1].legend(loc="best", fontsize=8)
    savefig(fig, "xyce_pybis_pulsetrain_smoothing_sweep.png")

    path = OUT / "xyce_pybis_pulsetrain_smoothing_sweep.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(path)


def plot_bitpattern_case():
    path = XYCE / "tb_channel_bitpattern_200p_xyce_relaxed15.cir.csv"
    if not path.exists():
        return
    d = load_xyce_csv(path)
    t = ns(col(d, "TIME"))
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(t, col(d, "V(IN_DIG)"), label="input", lw=1.0)
    axes[0].plot(t, col(d, "V(PAD)"), label="driver pad", lw=1.0)
    axes[0].plot(t, col(d, "V(N10B)"), label="receiver n10b", lw=1.2)
    style(axes[0], "Deterministic 10110010 pattern through new 50-ohm RLGC channel")

    axes[1].plot(t, col(d, "V(XDRV:KU)"), label="Ku", lw=1.0)
    axes[1].plot(t, col(d, "V(XDRV:KD)"), label="Kd", lw=1.0)
    axes[1].plot(t, col(d, "V(XDRV:NX)"), label="NX", lw=1.0)
    style(axes[1], "Internal state for deterministic bit pattern", ylabel="Coefficient / ns")
    savefig(fig, "xyce_pybis_relaxed15_bitpattern.png")


def compare_on_common_time(ref_t, ref_v, test_t, test_v):
    lo = max(float(ref_t[0]), float(test_t[0]))
    hi = min(float(ref_t[-1]), float(test_t[-1]))
    sample_t = np.linspace(lo, hi, 3000)
    ref_i = np.interp(sample_t, ref_t, ref_v)
    test_i = np.interp(sample_t, test_t, test_v)
    return float(np.sqrt(np.mean((test_i - ref_i) ** 2)))


def plot_ngspice_xyce_channel_deterministic():
    cases = [
        (
            "Repeated 200 ps pulse train",
            NGSPICE / "tb_channel_pulsetrain_200p_ngspice_pybis.raw",
            [
                ("Xyce tanh20 BE/non-LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed_timeint_nlte_be.cir.csv", True),
                ("Xyce direct BE/non-LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_direct_timeint_nlte_be.cir.csv", False),
            ],
            40.0,
        ),
        (
            "Deterministic 10110010 bit pattern",
            NGSPICE / "tb_channel_bitpattern_200p_ngspice_pybis.raw",
            [
                ("Xyce tanh20 BE/non-LTE", XYCE / "tb_channel_bitpattern_200p_xyce_relaxed_timeint_nlte_be.cir.csv", True),
                ("Xyce direct BE/non-LTE", XYCE / "tb_channel_bitpattern_200p_xyce_direct_timeint_nlte_be.cir.csv", False),
            ],
            45.0,
        ),
    ]

    fig, axes = plt.subplots(len(cases), 1, figsize=(11, 7), sharex=False)
    rows = []
    for ax, (title, ng_path, xy_entries, target_ns) in zip(axes, cases):
        ng = load_ngspice_raw(ng_path)
        ng_t = ns(col(ng, "time"))
        ng_pad = col(ng, "v(pad)")
        ng_n10b = col(ng, "v(n10b)")
        ax.plot(ng_t, ng_n10b, label="ngspice n10b", lw=1.4, color="#1f77b4")
        ax.plot(ng_t, col(ng, "v(in_dig)"), label="input", lw=0.7, color="0.55", alpha=0.5)

        for label, xy_path, preferred in xy_entries:
            if not xy_path.exists():
                continue
            xy = load_xyce_csv(xy_path)
            xy_t = ns(col(xy, "TIME"))
            xy_pad = col(xy, "V(PAD)")
            xy_n10b = col(xy, "V(N10B)")
            complete = xy_t[-1] >= target_ns - 1e-6
            suffix = "" if complete else f" stopped {xy_t[-1]:.1f} ns"
            ax.plot(
                xy_t,
                xy_n10b,
                label=f"{label}{suffix}",
                lw=1.2 if preferred else 0.9,
                alpha=0.95 if preferred else 0.75,
                ls="-" if preferred else "--",
            )
            rows.append({
                "case": title,
                "xyce_case": label,
                "complete": complete,
                "xyce_t_end_ns": float(xy_t[-1]),
                "ngspice_n10b_max": float(np.max(ng_n10b)),
                "xyce_n10b_max": float(np.max(xy_n10b)),
                "n10b_max_delta": float(np.max(xy_n10b) - np.max(ng_n10b)),
                "n10b_rmse_v": compare_on_common_time(ng_t, ng_n10b, xy_t, xy_n10b),
                "ngspice_pad_max": float(np.max(ng_pad)),
                "xyce_pad_max": float(np.max(xy_pad)),
                "pad_max_delta": float(np.max(xy_pad) - np.max(ng_pad)),
                "pad_rmse_v": compare_on_common_time(ng_t, ng_pad, xy_t, xy_pad),
            })
        style(ax, title)

    savefig(fig, "xyce_vs_ngspice_pybis_channel_deterministic.png")

    path = OUT / "xyce_vs_ngspice_pybis_channel_deterministic_metrics.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(path)


def plot_timeint_option_results():
    entries = [
        ("tanh20 default", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed.cir.csv", 40.0),
        ("tanh20 Gear LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed_timeint_gear.cir.csv", 40.0),
        ("tanh20 Gear non-LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed_timeint_nlte.cir.csv", 40.0),
        ("tanh20 BE non-LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed_timeint_nlte_be.cir.csv", 40.0),
        ("tanh18 Gear non-LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed18_timeint_nlte.cir.csv", 40.0),
        ("tanh17 Gear non-LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed17_timeint_nlte.cir.csv", 40.0),
        ("tanh16 Gear non-LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed16_timeint_nlte.cir.csv", 40.0),
        ("direct BE non-LTE", XYCE / "tb_channel_pulsetrain_200p_xyce_direct_timeint_nlte_be.cir.csv", 40.0),
    ]
    rows = []
    for label, path, target_ns in entries:
        if not path.exists():
            continue
        d = load_xyce_csv(path)
        t = ns(col(d, "TIME"))
        rows.append({
            "case": label,
            "complete": bool(t[-1] >= target_ns - 1e-6),
            "rows": len(t),
            "t_end_ns": float(t[-1]),
            "n10b_min": float(np.min(col(d, "V(N10B)"))) if "v(n10b)" in d else "",
            "n10b_max": float(np.max(col(d, "V(N10B)"))) if "v(n10b)" in d else "",
            "pad_min": float(np.min(col(d, "V(PAD)"))),
            "pad_max": float(np.max(col(d, "V(PAD)"))),
        })

    fig, ax = plt.subplots(1, 1, figsize=(11, 5))
    labels = [r["case"] for r in rows]
    times = [r["t_end_ns"] for r in rows]
    colors = ["#2ca02c" if r["complete"] else "#d62728" for r in rows]
    ax.barh(labels, times, color=colors, alpha=0.78)
    ax.axvline(40, color="0.25", lw=0.9, ls="--", label="target 40 ns")
    ax.set_xlabel("Final written time (ns)")
    ax.set_title("Xyce pybis pulse-train completion with time-integration options")
    ax.grid(True, axis="x", alpha=0.28)
    ax.legend(loc="lower right")
    savefig(fig, "xyce_pybis_timeint_option_results.png")

    path = OUT / "xyce_pybis_timeint_option_results.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(path)


def summarize_xyce_if_exists(label, path: Path, target_ns):
    if not path.exists():
        return None
    d = load_xyce_csv(path)
    t = ns(col(d, "TIME"))
    row = {
        "case": label,
        "complete": bool(t[-1] >= target_ns - 1e-6),
        "target_ns": float(target_ns),
        "rows": len(t),
        "t_end_ns": float(t[-1]),
        "pad_min": float(np.min(col(d, "V(PAD)"))),
        "pad_max": float(np.max(col(d, "V(PAD)"))),
    }
    if "v(n10b)" in d:
        row["n10b_min"] = float(np.min(col(d, "V(N10B)")))
        row["n10b_max"] = float(np.max(col(d, "V(N10B)")))
    if "v(xdrv:nx)" in d:
        row["nx_min"] = float(np.min(col(d, "V(XDRV:NX)")))
        row["nx_max"] = float(np.max(col(d, "V(XDRV:NX)")))
    return row


def write_rows_csv(name, rows):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path = OUT / name
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(path)


def plot_minimal_relaxation_sweep():
    entries = [
        ("direct tanh200", XYCE / "tb_channel_pulsetrain_200p_xyce_direct_timeint_nlte_be.cir.csv", 40.0),
        ("tanh100", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed100_timeint_nlte_be.cir.csv", 40.0),
        ("tanh98", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed98_timeint_nlte_be.cir.csv", 40.0),
        ("tanh95", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed95_timeint_nlte_be.cir.csv", 40.0),
        ("tanh94", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed94_timeint_nlte_be.cir.csv", 40.0),
        ("tanh92", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed92_timeint_nlte_be.cir.csv", 40.0),
        ("tanh90", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed90_timeint_nlte_be.cir.csv", 40.0),
        ("tanh75", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed75_timeint_nlte_be.cir.csv", 40.0),
        ("tanh60", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed60_timeint_nlte_be.cir.csv", 40.0),
        ("tanh50", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed50_timeint_nlte_be.cir.csv", 40.0),
        ("tanh30", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed30_timeint_nlte_be.cir.csv", 40.0),
        ("tanh20", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed_timeint_nlte_be.cir.csv", 40.0),
        ("tanh15", XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed15_timeint_nlte.cir.csv", 40.0),
    ]
    rows = [row for label, path, target in entries if (row := summarize_xyce_if_exists(label, path, target))]
    if not rows:
        return

    fig, ax = plt.subplots(1, 1, figsize=(11, 6))
    labels = [r["case"] for r in rows]
    times = [r["t_end_ns"] for r in rows]
    colors = ["#2ca02c" if r["complete"] else "#d62728" for r in rows]
    ax.barh(labels, times, color=colors, alpha=0.78)
    ax.axvline(40, color="0.25", lw=0.9, ls="--", label="target 40 ns")
    ax.set_xlabel("Final written time (ns)")
    ax.set_title("Minimal tanh relaxation sweep: 40 ns pulse train")
    ax.grid(True, axis="x", alpha=0.28)
    ax.legend(loc="lower right")
    savefig(fig, "xyce_pybis_minimal_relaxation_sweep.png")
    write_rows_csv("xyce_pybis_minimal_relaxation_sweep.csv", rows)


def plot_prbs_relaxation_candidates():
    entries = [
        ("tanh15 PRBS1000", XYCE / "tb_pybis_prbs7_new50ohm_xyce_relaxed15_timeint_nlte_be_1000n.cir.csv", 1000.0),
        ("tanh20 PRBS1000", XYCE / "tb_pybis_prbs7_new50ohm_xyce_relaxed_timeint_nlte_be_1000n.cir.csv", 1000.0),
        ("tanh50 PRBS200", XYCE / "tb_pybis_prbs7_new50ohm_xyce_relaxed50_timeint_nlte_be_200n.cir.csv", 200.0),
        ("tanh50 PRBS1000 out10p", XYCE / "tb_pybis_prbs7_new50ohm_xyce_relaxed50_timeint_nlte_be_1000n_out10p.cir.csv", 1000.0),
        ("tanh75 PRBS200", XYCE / "tb_pybis_prbs7_new50ohm_xyce_relaxed75_timeint_nlte_be_200n.cir.csv", 200.0),
        ("tanh90 PRBS200", XYCE / "tb_pybis_prbs7_new50ohm_xyce_relaxed90_timeint_nlte_be_200n.cir.csv", 200.0),
        ("tanh10 PRBS200", XYCE / "tb_pybis_prbs7_new50ohm_xyce_relaxed10_timeint_nlte_be_200n.cir.csv", 200.0),
    ]
    rows = [row for label, path, target in entries if (row := summarize_xyce_if_exists(label, path, target))]
    if not rows:
        return

    fig, ax = plt.subplots(1, 1, figsize=(11, 5.5))
    labels = [r["case"] for r in rows]
    progress = [100.0 * r["t_end_ns"] / r["target_ns"] for r in rows]
    colors = ["#2ca02c" if r["complete"] else "#d62728" for r in rows]
    ax.barh(labels, progress, color=colors, alpha=0.78)
    ax.axvline(100, color="0.25", lw=0.9, ls="--", label="target")
    ax.set_xlabel("Percent of requested PRBS window completed")
    ax.set_title("Xyce pybis PRBS candidates by relaxation factor")
    ax.set_xlim(0, 105)
    ax.grid(True, axis="x", alpha=0.28)
    ax.legend(loc="lower right")
    savefig(fig, "xyce_pybis_prbs_relaxation_candidates.png")
    write_rows_csv("xyce_pybis_prbs_relaxation_candidates.csv", rows)


def plot_prbs1000_overlay():
    ng_path = NGSPICE / "tb_pybis_prbs7_new50ohm.raw"
    xy_path = XYCE / "tb_pybis_prbs7_new50ohm_xyce_relaxed15_timeint_nlte_be_1000n.cir.csv"
    if not ng_path.exists() or not xy_path.exists():
        return

    ng = load_ngspice_raw(ng_path)
    xy = load_xyce_csv(xy_path)
    ng_t = ns(col(ng, "time"))
    xy_t = ns(col(xy, "TIME"))
    ng_pad = col(ng, "v(pad)")
    ng_n10b = col(ng, "v(n10b)")
    xy_pad = col(xy, "V(PAD)")
    xy_n10b = col(xy, "V(N10B)")

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=False)
    mask_ng = ng_t <= 200
    mask_xy = xy_t <= 200
    axes[0].plot(ng_t[mask_ng], ng_n10b[mask_ng], label="ngspice n10b", lw=1.2)
    axes[0].plot(xy_t[mask_xy], xy_n10b[mask_xy], label="Xyce tanh15 BE/non-LTE n10b", lw=1.0)
    axes[0].plot(xy_t[mask_xy], col(xy, "V(IN_DIG)")[mask_xy], label="input", lw=0.7, color="0.55", alpha=0.45)
    style(axes[0], "PRBS7 first 200 ns: ngspice vs Xyce pybis")

    # Plot the full run with light decimation for readability.
    ng_step = max(1, len(ng_t) // 12000)
    xy_step = max(1, len(xy_t) // 12000)
    axes[1].plot(ng_t[::ng_step], ng_n10b[::ng_step], label="ngspice n10b", lw=1.0)
    axes[1].plot(xy_t[::xy_step], xy_n10b[::xy_step], label="Xyce tanh15 BE/non-LTE n10b", lw=0.9)
    style(axes[1], "PRBS7 full 1000 ns receiver waveform")
    savefig(fig, "xyce_vs_ngspice_pybis_prbs1000_overlay.png")

    rows = [{
        "case": "PRBS7 1000 ns",
        "xyce_case": "tanh15 BE/non-LTE",
        "ngspice_t_end_ns": float(ng_t[-1]),
        "xyce_t_end_ns": float(xy_t[-1]),
        "ngspice_n10b_min": float(np.min(ng_n10b)),
        "xyce_n10b_min": float(np.min(xy_n10b)),
        "n10b_min_delta": float(np.min(xy_n10b) - np.min(ng_n10b)),
        "ngspice_n10b_max": float(np.max(ng_n10b)),
        "xyce_n10b_max": float(np.max(xy_n10b)),
        "n10b_max_delta": float(np.max(xy_n10b) - np.max(ng_n10b)),
        "n10b_rmse_v": compare_on_common_time(ng_t, ng_n10b, xy_t, xy_n10b),
        "ngspice_pad_max": float(np.max(ng_pad)),
        "xyce_pad_max": float(np.max(xy_pad)),
        "pad_max_delta": float(np.max(xy_pad) - np.max(ng_pad)),
        "pad_rmse_v": compare_on_common_time(ng_t, ng_pad, xy_t, xy_pad),
    }]
    path = OUT / "xyce_vs_ngspice_pybis_prbs1000_metrics.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(path)


def summarize_csv(path: Path, signals):
    d = load_xyce_csv(path)
    t = col(d, "TIME")
    row = {
        "case": path.stem.replace(".cir", ""),
        "rows": len(t),
        "t_end_ns": float(t[-1] * 1e9),
    }
    for sig in signals:
        v = col(d, sig)
        clean = re.sub(r"[^A-Za-z0-9]+", "_", sig).strip("_").lower()
        row[f"{clean}_min"] = float(np.min(v))
        row[f"{clean}_max"] = float(np.max(v))
    return row


def write_metrics():
    rows = [
        summarize_csv(XYCE / "tb_test_rise_late_xyce_uic_relaxed.cir.csv", ["V(PAD)", "V(XDRV:KU)", "V(XDRV:KD)"]),
        summarize_csv(XYCE / "tb_test_rfr_xyce_uic_relaxed.cir.csv", ["V(PAD)", "V(XDRV:KU)", "V(XDRV:KD)"]),
        summarize_csv(XYCE / "tb_test_rfall_late_xyce_uic_relaxed.cir.csv", ["V(PAD)", "V(XDRV:KU)", "V(XDRV:KD)"]),
        summarize_csv(XYCE / "tb_channel_rise_200p_xyce_relaxed.cir.csv", ["V(PAD)", "V(N10B)", "V(XDRV:KU)", "V(XDRV:KD)"]),
        summarize_csv(XYCE / "tb_channel_rfr_200p_xyce_relaxed.cir.csv", ["V(PAD)", "V(N10B)", "V(XDRV:KU)", "V(XDRV:KD)"]),
    ]
    pulse = XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed.cir.csv"
    if pulse.exists():
        rows.append(summarize_csv(pulse, ["V(PAD)", "V(N10B)", "V(XDRV:KU)", "V(XDRV:KD)", "V(XDRV:NX)"]))
    two_pulse = XYCE / "tb_channel_twopulse_200p_xyce_relaxed.cir.csv"
    if two_pulse.exists():
        rows.append(summarize_csv(two_pulse, ["V(PAD)", "V(N10B)", "V(XDRV:KU)", "V(XDRV:KD)", "V(XDRV:NX)"]))
    pulse10 = XYCE / "tb_channel_pulsetrain_200p_xyce_relaxed10.cir.csv"
    if pulse10.exists():
        rows.append(summarize_csv(pulse10, ["V(PAD)", "V(N10B)", "V(XDRV:KU)", "V(XDRV:KD)", "V(XDRV:NX)"]))
    bits = XYCE / "tb_channel_bitpattern_200p_xyce_relaxed15.cir.csv"
    if bits.exists():
        rows.append(summarize_csv(bits, ["V(PAD)", "V(N10B)", "V(XDRV:KU)", "V(XDRV:KD)", "V(XDRV:NX)"]))

    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "xyce_pybis_relaxed_metrics.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(path)


def main():
    plot_rload_cases()
    plot_ngspice_rload_overlay()
    plot_channel_cases()
    plot_pulsetrain_boundary()
    plot_twopulse_case()
    plot_relaxed10_pulsetrain()
    plot_pulsetrain_smoothing_sweep()
    plot_bitpattern_case()
    plot_ngspice_xyce_channel_deterministic()
    plot_timeint_option_results()
    plot_minimal_relaxation_sweep()
    plot_prbs_relaxation_candidates()
    plot_prbs1000_overlay()
    write_metrics()


if __name__ == "__main__":
    main()
