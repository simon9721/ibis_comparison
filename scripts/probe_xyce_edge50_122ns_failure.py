"""Probe the Xyce edge50_flat4p2 PRBS failure around the 122 ns edge.

The cross-flow stress runner showed:

- PRBS60, 2 ns UI, 30 cm coarse RLGC, loss x5: Xyce pybis edge50 passes.
- PRBS62 with the same setup: Xyce pybis stalls at about 122.26 ns.

This script reruns focused Xyce-only decks with extra internal pybis control
nodes printed so the failing edge can be inspected without rerunning the whole
cross-flow matrix.
"""

from __future__ import annotations

import csv
import math
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

import run_edge_family_stress_crossflow as base  # noqa: E402
from eye_diagram import load_waveform, sanitize_waveform  # noqa: E402

OUT_DIR = ROOT / "results" / "xyce_edge50_122ns_failure_probe_2026-05-12"
XYCE = Path(r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")

PROBE_PRINT = (
    ".print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) "
    "V(XDRV:NINX) V(XDRV:NI) V(XDRV:N2) V(XDRV:N3) V(XDRV:N4) "
    "V(XDRV:N6) V(XDRV:N8) V(XDRV:N9) V(XDRV:NX) "
    "V(XDRV:KUR0) V(XDRV:KDR0) V(XDRV:KUF0) V(XDRV:KDF0) "
    "V(XDRV:NKUR) V(XDRV:NKDR) V(XDRV:NKUF) V(XDRV:NKDF) "
    "V(XDRV:Ku) V(XDRV:Kd)"
)


@dataclass(frozen=True)
class ProbeRun:
    key: str
    n_bits: int
    loss_scale: float
    timeout_s: float
    note: str


RUNS = [
    ProbeRun("prbs60_loss5_pass", 60, 5.0, 90.0, "verified passing boundary run"),
    ProbeRun("prbs62_loss5_fail", 62, 5.0, 90.0, "includes the 122 ns 00->10 edge"),
    ProbeRun("prbs62_loss1_check", 62, 1.0, 90.0, "same edge with lower channel loss"),
]


def reset_out_dir() -> None:
    resolved = OUT_DIR.resolve()
    expected_parent = (ROOT / "results").resolve()
    if resolved.parent != expected_parent:
        raise RuntimeError(f"Refusing to remove unexpected output dir: {resolved}")
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "plots").mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def configure(n_bits: int) -> None:
    base.configure_suite(
        [
            "--suite",
            "coarse10_edge50",
            "--n-bits",
            str(n_bits),
            "--timeout-s",
            "90",
        ]
    )


def probe_case(run: ProbeRun) -> base.StressCase:
    return base.StressCase(
        f"ui2_len30cm_loss{run.loss_scale:g}_coarse10",
        2e-9,
        3,
        run.loss_scale,
        f"2 ns UI, 30 cm coarse channel, loss x{run.loss_scale:g}",
        n_sections_override=10,
    )


def make_probe_deck(run: ProbeRun, run_dir: Path) -> tuple[Path, Path]:
    configure(run.n_bits)
    case = probe_case(run)
    flow = base.Flow("xyce_pybis", "Xyce", "pybis edge50_flat4p2", "xyce", "#d62728")
    deck_text, _ = base.make_deck(case, flow, run_dir)
    deck_text = deck_text.replace(
        ".print tran format=csv time V(in_dig) V(pad) V(tx_out) V(n10b) "
        "V(XDRV:Ku) V(XDRV:Kd) V(XDRV:NX)",
        PROBE_PRINT,
    )
    deck = run_dir / f"{run.key}.cir"
    deck.write_text(deck_text, encoding="ascii")
    return deck, run_dir / f"{deck.name}.csv"


def run_xyce(run: ProbeRun) -> dict[str, object]:
    run_dir = OUT_DIR / "runs" / run.key
    run_dir.mkdir(parents=True, exist_ok=True)
    deck, output = make_probe_deck(run, run_dir)
    output.unlink(missing_ok=True)
    log = run_dir / f"{run.key}.log"

    started = time.time()
    try:
        proc = subprocess.run(
            [str(XYCE), deck.name],
            cwd=run_dir,
            timeout=run.timeout_s,
            capture_output=True,
            text=True,
        )
        timed_out = False
        return_code: int | str = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = "timeout"
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    wall_s = time.time() - started

    log.write_text(
        "COMMAND: " + str(XYCE) + " " + deck.name + "\n"
        f"RETURN_CODE: {return_code}\nTIMED_OUT: {timed_out}\n"
        f"WALL_SECONDS: {wall_s:.3f}\n\n"
        "STDOUT:\n" + stdout + "\n\nSTDERR:\n" + stderr,
        encoding="utf-8",
    )

    row: dict[str, object] = {
        "run": run.key,
        "n_bits": run.n_bits,
        "loss_scale": run.loss_scale,
        "note": run.note,
        "return_code": return_code,
        "timed_out": timed_out,
        "wall_s": wall_s,
        "deck": str(deck.relative_to(ROOT)).replace("\\", "/"),
        "output": str(output.relative_to(ROOT)).replace("\\", "/"),
        "log": str(log.relative_to(ROOT)).replace("\\", "/"),
        "output_exists": output.exists(),
    }
    if output.exists():
        data = load_waveform(output, fmt="xyce")
        time_vec, _ = sanitize_waveform(data["time"], data["time"])
        row["points"] = len(time_vec)
        row["t_end_ns"] = float(time_vec[-1] * 1e9)
        row["completed"] = bool(time_vec[-1] >= run.n_bits * 2e-9 - 1e-12)
    return row


def prbs_context_rows(n_bits: int) -> list[dict[str, object]]:
    states = [0 if bit == 1 else 1 for bit in base.prbs7(n_bits)]
    rows = []
    for i in range(1, n_bits):
        if states[i - 1] == states[i]:
            continue
        ctx = (
            (str(states[i - 2]) if i >= 2 else "x")
            + str(states[i - 1])
            + "->"
            + str(states[i])
            + (str(states[i + 1]) if i + 1 < n_bits else "x")
        )
        rows.append(
            {
                "bit_index": i,
                "edge_time_ns": i * 2.0,
                "from": states[i - 1],
                "to": states[i],
                "direction": "rise" if states[i] > states[i - 1] else "fall",
                "context": ctx,
            }
        )
    return rows


def load_run(run_key: str):
    path = OUT_DIR / "runs" / run_key / f"{run_key}.cir.csv"
    return load_waveform(path, fmt="xyce")


def key(data: dict[str, np.ndarray], preferred: str) -> str:
    preferred = preferred.lower()
    if preferred in data:
        return preferred
    raise KeyError(f"Missing {preferred}; available={list(data)[:12]}")


def series(data: dict[str, np.ndarray], name: str) -> tuple[np.ndarray, np.ndarray]:
    return sanitize_waveform(data["time"], data[key(data, name)])


def last_rows(run_key: str, t0_ns: float = 121.6) -> list[dict[str, object]]:
    data = load_run(run_key)
    t, _ = sanitize_waveform(data["time"], data["time"])
    selected = np.where(t * 1e9 >= t0_ns)[0]
    if len(selected) > 240:
        selected = selected[-240:]
    names = [
        "v(in_dig)",
        "v(pad)",
        "v(tx_out)",
        "v(n10b)",
        "v(xdrv:ni)",
        "v(xdrv:n2)",
        "v(xdrv:n3)",
        "v(xdrv:n4)",
        "v(xdrv:n6)",
        "v(xdrv:n8)",
        "v(xdrv:nx)",
        "v(xdrv:ku)",
        "v(xdrv:kd)",
    ]
    arrays = {name: series(data, name)[1] for name in names if name in data}
    rows = []
    for idx in selected:
        row: dict[str, object] = {"time_ns": t[idx] * 1e9}
        for name, values in arrays.items():
            row[name] = float(values[idx])
        rows.append(row)
    return rows


def plot_failure_window() -> None:
    data = load_run("prbs62_loss5_fail")
    t, vin = series(data, "v(in_dig)")
    _, pad = series(data, "v(pad)")
    _, tx = series(data, "v(tx_out)")
    _, rx = series(data, "v(n10b)")
    _, ni = series(data, "v(xdrv:ni)")
    _, n2 = series(data, "v(xdrv:n2)")
    _, n3 = series(data, "v(xdrv:n3)")
    _, n4 = series(data, "v(xdrv:n4)")
    _, n6 = series(data, "v(xdrv:n6)")
    _, n8 = series(data, "v(xdrv:n8)")
    _, nx = series(data, "v(xdrv:nx)")
    _, ku = series(data, "v(xdrv:ku)")
    _, kd = series(data, "v(xdrv:kd)")
    _, kur0 = series(data, "v(xdrv:kur0)")
    _, kdr0 = series(data, "v(xdrv:kdr0)")
    _, nkur = series(data, "v(xdrv:nkur)")
    _, nkdr = series(data, "v(xdrv:nkdr)")

    x_ns = t * 1e9
    mask = (x_ns >= 118.0) & (x_ns <= max(122.35, x_ns[-1]))

    fig, axes = plt.subplots(5, 1, figsize=(13, 11), sharex=True)
    axes[0].plot(x_ns[mask], vin[mask], label="in_dig", color="#111111")
    axes[0].plot(x_ns[mask], pad[mask], label="pad", color="#1f77b4")
    axes[0].plot(x_ns[mask], tx[mask], label="tx_out", color="#17becf", alpha=0.75)
    axes[0].plot(x_ns[mask], rx[mask], label="n10b", color="#d62728")
    axes[0].set_ylabel("V")
    axes[0].legend(loc="best", fontsize=8)

    axes[1].plot(x_ns[mask], ku[mask], label="Ku", color="#2ca02c")
    axes[1].plot(x_ns[mask], kd[mask], label="Kd", color="#9467bd")
    axes[1].plot(x_ns[mask], kur0[mask], label="KUR0", color="#98df8a", ls="--")
    axes[1].plot(x_ns[mask], kdr0[mask], label="KDR0", color="#c5b0d5", ls="--")
    axes[1].set_ylabel("coeff")
    axes[1].legend(loc="best", fontsize=8)

    axes[2].plot(x_ns[mask], n6[mask], label="N6", color="#ff7f0e")
    axes[2].plot(x_ns[mask], n8[mask], label="N8", color="#8c564b")
    axes[2].plot(x_ns[mask], nx[mask], label="NX", color="#e377c2")
    axes[2].axhline(5.96, color="#777777", ls=":", lw=1)
    axes[2].set_ylabel("ns-scale")
    axes[2].legend(loc="best", fontsize=8)

    axes[3].plot(x_ns[mask], ni[mask], label="NI", color="#1f77b4")
    axes[3].plot(x_ns[mask], n2[mask], label="N2", color="#d62728")
    axes[3].plot(x_ns[mask], n3[mask], label="N3", color="#2ca02c")
    axes[3].plot(x_ns[mask], n4[mask], label="N4", color="#ff7f0e")
    axes[3].set_ylabel("edge sense")
    axes[3].legend(loc="best", fontsize=8)

    axes[4].plot(x_ns[mask], nkur[mask], label="NKUR", color="#2ca02c")
    axes[4].plot(x_ns[mask], nkdr[mask], label="NKDR", color="#9467bd")
    axes[4].set_ylabel("selected coeff")
    axes[4].set_xlabel("Time (ns)")
    axes[4].legend(loc="best", fontsize=8)

    for ax in axes:
        ax.axvline(120.0, color="#999999", ls=":", lw=1)
        ax.axvline(122.0, color="#b2182b", ls="--", lw=1)
        ax.axvline(122.2, color="#b2182b", ls=":", lw=1)
        ax.grid(True, alpha=0.25)
    fig.suptitle("Xyce edge50_flat4p2 PRBS62 failing window: 122 ns edge", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT_DIR / "plots" / "edge50_prbs62_fail_internal_window.png", dpi=180)
    plt.close(fig)


def plot_pass_fail_overlay() -> None:
    fig, axes = plt.subplots(3, 1, figsize=(13, 8.5), sharex=True)
    specs = [
        ("prbs60_loss5_pass", "#1f77b4", "PRBS60 pass"),
        ("prbs62_loss5_fail", "#d62728", "PRBS62 fail"),
    ]
    for run_key, color, label in specs:
        data = load_run(run_key)
        t, vin = series(data, "v(in_dig)")
        _, rx = series(data, "v(n10b)")
        _, nx = series(data, "v(xdrv:nx)")
        _, ku = series(data, "v(xdrv:ku)")
        _, kd = series(data, "v(xdrv:kd)")
        x_ns = t * 1e9
        mask = (x_ns >= 112.0) & (x_ns <= min(124.0, x_ns[-1]))
        axes[0].plot(x_ns[mask], vin[mask], color=color, alpha=0.35, lw=1.0)
        axes[0].plot(x_ns[mask], rx[mask], color=color, lw=1.4, label=label)
        axes[1].plot(x_ns[mask], ku[mask], color=color, lw=1.4, label=f"{label} Ku")
        axes[1].plot(x_ns[mask], kd[mask], color=color, lw=1.1, ls="--", label=f"{label} Kd")
        axes[2].plot(x_ns[mask], nx[mask], color=color, lw=1.4, label=label)
    axes[0].set_ylabel("V")
    axes[1].set_ylabel("Ku/Kd")
    axes[2].set_ylabel("NX (ns)")
    axes[2].set_xlabel("Time (ns)")
    for ax in axes:
        ax.axvline(122.0, color="#b2182b", ls="--", lw=1)
        ax.axvline(122.2, color="#b2182b", ls=":", lw=1)
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best", fontsize=8)
    fig.suptitle("PRBS60 pass vs PRBS62 fail near boundary", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT_DIR / "plots" / "edge50_pass_fail_boundary_overlay.png", dpi=180)
    plt.close(fig)


def write_readme(run_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Xyce Edge50 122 ns Failure Probe",
        "",
        "Focused Xyce-only probe for the `edge50_flat4p2` model under the stressed",
        "2 ns UI / 30 cm coarse RLGC / loss x5 setup.",
        "",
        "## Runs",
        "",
        "| Run | Bits | Loss | Return | Timeout | End ns | Completed | Note |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in run_rows:
        fmt_row = dict(row)
        fmt_row["t_end_ns"] = float(fmt_row.get("t_end_ns", float("nan")))
        fmt_row["completed"] = fmt_row.get("completed", False)
        lines.append(
            "| {run} | {n_bits} | {loss_scale:g} | {return_code} | {timed_out} | "
            "{t_end_ns:.3f} | {completed} | {note} |".format(**fmt_row)
        )
    lines.extend(
        [
            "",
            "## Key Files",
            "",
            "- `run_summary.csv`: run status and stop time",
            "- `edge_contexts_prbs62.csv`: PRBS edge contexts through the failing edge",
            "- `tail_prbs62_loss5_fail.csv`: last printed values before timeout",
            "- `plots/edge50_prbs62_fail_internal_window.png`: internal controls around 122 ns",
            "- `plots/edge50_pass_fail_boundary_overlay.png`: pass/fail boundary comparison",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    if not XYCE.exists():
        raise FileNotFoundError(XYCE)
    reset_out_dir()
    run_rows = []
    for run in RUNS:
        print(f"Running {run.key}", flush=True)
        run_rows.append(run_xyce(run))
    write_csv(OUT_DIR / "run_summary.csv", run_rows)
    write_csv(OUT_DIR / "edge_contexts_prbs62.csv", prbs_context_rows(62))
    write_csv(OUT_DIR / "tail_prbs62_loss5_fail.csv", last_rows("prbs62_loss5_fail"))
    plot_failure_window()
    plot_pass_fail_overlay()
    write_readme(run_rows)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
