"""Compare clean refspice/pybis RSF runs against the source IBIS VT tables.

The purpose is to answer a narrow correlation question:

* Does the converted pybis model follow the IBIS waveform timing?
* Does the transistor refspice run follow that same IBIS timing?

The script writes timing CSVs and compact overlay plots for the two clean
comparison packages:

* clean_ibis_vs_pybis_matched_pkg          (io_buf)
* inv_chain/clean_ibis_vs_pybis_matched_pkg (inv_chain)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import math
import re

import matplotlib.pyplot as plt
import numpy as np

from plot_validation_results import parse_ngspice_raw


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results" / "refspice_pybis_correlation_study_2026-05-27"


@dataclass
class IbisWaveform:
    model: str
    kind: str
    r_fixture: float
    v_fixture: float
    time_ns: np.ndarray
    v_typ: np.ndarray


@dataclass
class Case:
    name: str
    package_dir: Path
    ibis_file: str
    pybis_raw: str
    ref_raw: str
    input_threshold: float
    rise_search_ns: tuple[float, float]
    fall_search_ns: tuple[float, float]
    r_fixture: float = 50.0
    v_fixture: float = 0.0


CASES = [
    Case(
        name="io_buf",
        package_dir=ROOT / "clean_ibis_vs_pybis_matched_pkg",
        ibis_file="io_buf.ibs",
        pybis_raw="tb_ibis_vs_pybis_rsf_12n_batch.raw",
        ref_raw="tb_refspice_rsf_14n_batch.raw",
        input_threshold=1.4,
        rise_search_ns=(0.9, 1.2),
        fall_search_ns=(8.9, 9.2),
    ),
    Case(
        name="inv_chain",
        package_dir=ROOT / "inv_chain" / "clean_ibis_vs_pybis_matched_pkg",
        ibis_file="t2b_0615_v5.ibs",
        pybis_raw="tb_ibis_vs_pybis_rsf_6p5n_batch.raw",
        ref_raw="tb_refspice_rsf_7n_batch.raw",
        input_threshold=0.9,
        rise_search_ns=(0.9, 1.2),
        fall_search_ns=(3.9, 4.2),
    ),
]


NUMBER_RE = re.compile(
    r"^\s*(?P<num>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"\s*(?P<unit>[a-zA-Z]*)\s*$"
)

UNIT_SCALE = {
    "": 1.0,
    "v": 1.0,
    "s": 1e9,  # time values are returned in ns
    "ps": 1e-3,
    "p": 1e-3,
    "ns": 1.0,
    "n": 1e-9,  # voltage values such as nV
    "us": 1e3,
    "u": 1e-6,
    "ms": 1e6,
    "m": 1e-3,
    "a": 1.0,
}


def parse_number(token: str, *, quantity: str) -> float:
    match = NUMBER_RE.match(token.strip())
    if not match:
        raise ValueError(f"Could not parse numeric token {token!r}")

    value = float(match.group("num"))
    unit = match.group("unit").lower()

    if quantity == "time":
        if unit in ("", "s"):
            return value * 1e9
        if unit in ("ps", "p"):
            return value * 1e-3
        if unit in ("ns", "n"):
            return value
        if unit in ("us", "u"):
            return value * 1e3
        if unit in ("ms",):
            return value * 1e6
    elif quantity == "voltage":
        if unit.endswith("v"):
            prefix = unit[:-1]
        else:
            prefix = unit
        if prefix == "":
            return value
        if prefix == "m":
            return value * 1e-3
        if prefix == "u":
            return value * 1e-6
        if prefix == "n":
            return value * 1e-9
        if prefix == "p":
            return value * 1e-12
    elif quantity == "fixture":
        unit = unit.rstrip("v")
        if unit == "":
            return value
        if unit == "m":
            return value * 1e-3
        if unit == "u":
            return value * 1e-6
        if unit == "n":
            return value * 1e-9

    if unit in UNIT_SCALE:
        return value * UNIT_SCALE[unit]
    raise ValueError(f"Unsupported unit {unit!r} in token {token!r}")


def parse_fixture_value(line: str) -> float:
    return parse_number(line.split("=", 1)[1].strip(), quantity="fixture")


def parse_ibis_waveforms(path: Path) -> list[IbisWaveform]:
    lines = path.read_text().splitlines()
    waveforms: list[IbisWaveform] = []
    current_model = ""
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        lower = stripped.lower()

        if lower == "[model]":
            if i + 1 < len(lines):
                current_model = lines[i + 1].strip()
            i += 1
            continue
        if lower.startswith("[model] "):
            current_model = stripped.split("]", 1)[1].strip()
            i += 1
            continue

        if lower not in ("[rising waveform]", "[falling waveform]"):
            i += 1
            continue

        kind = "rising" if "rising" in lower else "falling"
        r_fixture: float | None = None
        v_fixture: float | None = None
        samples: list[tuple[float, float]] = []
        i += 1

        while i < len(lines):
            raw = lines[i]
            stripped = raw.strip()
            lower = stripped.lower()

            if stripped.startswith("["):
                break
            if not stripped or stripped.startswith("|"):
                i += 1
                continue
            if lower.startswith("r_fixture"):
                r_fixture = parse_fixture_value(stripped)
                i += 1
                continue
            if lower.startswith("v_fixture"):
                v_fixture = parse_fixture_value(stripped)
                i += 1
                continue

            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    t_ns = parse_number(parts[0], quantity="time")
                    v_typ = parse_number(parts[1], quantity="voltage")
                except ValueError:
                    i += 1
                    continue
                samples.append((t_ns, v_typ))
            i += 1

        if r_fixture is not None and v_fixture is not None and samples:
            arr = np.asarray(samples, dtype=float)
            order = np.argsort(arr[:, 0])
            arr = arr[order]
            waveforms.append(
                IbisWaveform(
                    model=current_model,
                    kind=kind,
                    r_fixture=float(r_fixture),
                    v_fixture=float(v_fixture),
                    time_ns=arr[:, 0],
                    v_typ=arr[:, 1],
                )
            )

    return waveforms


def choose_waveform(
    waveforms: list[IbisWaveform], kind: str, r_fixture: float, v_fixture: float
) -> IbisWaveform:
    candidates = [wf for wf in waveforms if wf.kind == kind]
    if not candidates:
        raise RuntimeError(f"No {kind} waveform in parsed IBIS data")

    def score(wf: IbisWaveform) -> tuple[float, float]:
        return (abs(wf.r_fixture - r_fixture), abs(wf.v_fixture - v_fixture))

    return min(candidates, key=score)


def crossing_time(
    time_ns: np.ndarray,
    y: np.ndarray,
    threshold: float,
    direction: str,
    search_ns: tuple[float, float] | None = None,
) -> float:
    mask = np.ones_like(time_ns, dtype=bool)
    if search_ns is not None:
        mask = (time_ns >= search_ns[0]) & (time_ns <= search_ns[1])

    t = time_ns[mask]
    v = y[mask]
    if len(t) < 2:
        return math.nan

    if direction == "rising":
        hits = np.where((v[:-1] < threshold) & (v[1:] >= threshold))[0]
    else:
        hits = np.where((v[:-1] > threshold) & (v[1:] <= threshold))[0]

    if len(hits) == 0:
        return math.nan

    idx = int(hits[0])
    t0, t1 = float(t[idx]), float(t[idx + 1])
    v0, v1 = float(v[idx]), float(v[idx + 1])
    if v1 == v0:
        return t0
    return t0 + (threshold - v0) * (t1 - t0) / (v1 - v0)


def raw_time_ns(data: dict[str, np.ndarray]) -> np.ndarray:
    return data["time"] * 1e9


def first_existing(data: dict[str, np.ndarray], names: tuple[str, ...]) -> np.ndarray:
    for name in names:
        if name in data:
            return data[name]
    raise KeyError(f"None of these signals were found: {names}")


def waveform_threshold(wf: IbisWaveform, pct: float) -> float:
    return float(wf.v_typ[0] + pct * (wf.v_typ[-1] - wf.v_typ[0]))


def windowed_trace(
    time_ns: np.ndarray,
    y: np.ndarray,
    center_ns: float,
    window_ns: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray]:
    rel = time_ns - center_ns
    mask = (rel >= window_ns[0]) & (rel <= window_ns[1])
    return rel[mask], y[mask]


def analyze_case(case: Case) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    waveforms = parse_ibis_waveforms(case.package_dir / case.ibis_file)
    rise_wf = choose_waveform(waveforms, "rising", case.r_fixture, case.v_fixture)
    fall_wf = choose_waveform(waveforms, "falling", case.r_fixture, case.v_fixture)

    pybis = parse_ngspice_raw(case.package_dir / case.pybis_raw)
    ref = parse_ngspice_raw(case.package_dir / case.ref_raw)

    pyb_t = raw_time_ns(pybis)
    ref_t = raw_time_ns(ref)
    pyb_in = first_existing(pybis, ("v(in_dig)",))
    ref_in = first_existing(ref, ("v(in_dig)",))
    pyb_pad = first_existing(pybis, ("v(pad)",))
    ref_pad = first_existing(ref, ("v(pad_ref)", "v(pad)"))

    edge_rows: list[dict[str, object]] = []
    shape_rows: list[dict[str, object]] = []

    input_cross = {
        "rising": (
            crossing_time(pyb_t, pyb_in, case.input_threshold, "rising", case.rise_search_ns),
            crossing_time(ref_t, ref_in, case.input_threshold, "rising", case.rise_search_ns),
        ),
        "falling": (
            crossing_time(pyb_t, pyb_in, case.input_threshold, "falling", case.fall_search_ns),
            crossing_time(ref_t, ref_in, case.input_threshold, "falling", case.fall_search_ns),
        ),
    }

    for kind, wf, search in (
        ("rising", rise_wf, case.rise_search_ns),
        ("falling", fall_wf, case.fall_search_ns),
    ):
        direction = kind
        pyb_input_t, ref_input_t = input_cross[kind]
        for pct in (0.25, 0.50, 0.75):
            thr = waveform_threshold(wf, pct)
            ibis_dt = crossing_time(wf.time_ns, wf.v_typ, thr, direction)
            pyb_cross = crossing_time(pyb_t, pyb_pad, thr, direction, (search[0], search[1] + 3.0))
            ref_cross = crossing_time(ref_t, ref_pad, thr, direction, (search[0], search[1] + 3.0))

            pyb_dt = pyb_cross - pyb_input_t
            ref_dt = ref_cross - ref_input_t
            edge_rows.append(
                {
                    "case": case.name,
                    "edge": kind,
                    "threshold_pct": pct,
                    "threshold_v": thr,
                    "ibis_after_input_ps": ibis_dt * 1000.0,
                    "pybis_after_input_ps": pyb_dt * 1000.0,
                    "refspice_after_input_ps": ref_dt * 1000.0,
                    "pybis_minus_ibis_ps": (pyb_dt - ibis_dt) * 1000.0,
                    "refspice_minus_ibis_ps": (ref_dt - ibis_dt) * 1000.0,
                    "pybis_minus_refspice_ps": (pyb_dt - ref_dt) * 1000.0,
                    "ibis_r_fixture": wf.r_fixture,
                    "ibis_v_fixture": wf.v_fixture,
                }
            )

        # Shape residuals on a common time-after-input axis.
        sample_rel = np.linspace(0.0, min(3.0, float(wf.time_ns[-1])), 1500)
        ibis_v = np.interp(sample_rel, wf.time_ns, wf.v_typ)
        pyb_v = np.interp(sample_rel + pyb_input_t, pyb_t, pyb_pad)
        ref_v = np.interp(sample_rel + ref_input_t, ref_t, ref_pad)
        shape_rows.append(
            {
                "case": case.name,
                "edge": kind,
                "window_ns": float(sample_rel[-1]),
                "pybis_vs_ibis_rmse_mv": float(np.sqrt(np.mean((pyb_v - ibis_v) ** 2)) * 1000.0),
                "refspice_vs_ibis_rmse_mv": float(np.sqrt(np.mean((ref_v - ibis_v) ** 2)) * 1000.0),
                "pybis_vs_refspice_rmse_mv": float(np.sqrt(np.mean((pyb_v - ref_v) ** 2)) * 1000.0),
                "ibis_r_fixture": wf.r_fixture,
                "ibis_v_fixture": wf.v_fixture,
            }
        )

    make_case_plot(case, rise_wf, fall_wf, pyb_t, pyb_in, pyb_pad, ref_t, ref_in, ref_pad, input_cross)
    return edge_rows, shape_rows


def make_case_plot(
    case: Case,
    rise_wf: IbisWaveform,
    fall_wf: IbisWaveform,
    pyb_t: np.ndarray,
    pyb_in: np.ndarray,
    pyb_pad: np.ndarray,
    ref_t: np.ndarray,
    ref_in: np.ndarray,
    ref_pad: np.ndarray,
    input_cross: dict[str, tuple[float, float]],
) -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (11.5, 7.5),
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8.5,
        }
    )
    fig, axes = plt.subplots(2, 1, sharex=False)

    for ax, kind, wf, window in (
        (axes[0], "rising", rise_wf, (-0.15, min(3.0, rise_wf.time_ns[-1]))),
        (axes[1], "falling", fall_wf, (-0.15, min(3.0, fall_wf.time_ns[-1]))),
    ):
        pyb_input_t, ref_input_t = input_cross[kind]
        pyb_rel, pyb_v = windowed_trace(pyb_t, pyb_pad, pyb_input_t, window)
        ref_rel, ref_v = windowed_trace(ref_t, ref_pad, ref_input_t, window)
        in_rel, in_v = windowed_trace(pyb_t, pyb_in, pyb_input_t, window)

        wf_mask = (wf.time_ns >= max(0.0, window[0])) & (wf.time_ns <= window[1])
        ax.plot(wf.time_ns[wf_mask], wf.v_typ[wf_mask], label="IBIS VT table", color="#111111", linewidth=2.3)
        ax.plot(pyb_rel, pyb_v, label="pybis converted pad", color="#d95f02", linewidth=1.9)
        ax.plot(ref_rel, ref_v, label="refspice pad", color="#1b75bb", linewidth=1.9)
        ax.plot(in_rel, in_v, label="input", color="#777777", linewidth=1.1, linestyle="--", alpha=0.65)
        ax.axvline(0.0, color="#555555", linewidth=0.8, alpha=0.45)
        ax.grid(True, alpha=0.28)
        ax.set_ylabel("Voltage (V)")
        ax.set_title(f"{case.name}: {kind} edge, aligned to input threshold crossing")
        ax.legend(loc="best")

    axes[-1].set_xlabel("Time after input threshold crossing (ns)")
    fig.tight_layout()
    out = OUT_DIR / f"{case.name}_ibis_pybis_refspice_edge_overlay.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_timing: list[dict[str, object]] = []
    all_shape: list[dict[str, object]] = []

    for case in CASES:
        timing, shape = analyze_case(case)
        all_timing.extend(timing)
        all_shape.extend(shape)

    write_csv(OUT_DIR / "ibis_refspice_pybis_crossing_timing.csv", all_timing)
    write_csv(OUT_DIR / "ibis_refspice_pybis_shape_rmse.csv", all_shape)

    print(f"Wrote {OUT_DIR / 'ibis_refspice_pybis_crossing_timing.csv'}")
    print(f"Wrote {OUT_DIR / 'ibis_refspice_pybis_shape_rmse.csv'}")
    print("Generated overlays:")
    for case in CASES:
        print(f"  {OUT_DIR / f'{case.name}_ibis_pybis_refspice_edge_overlay.png'}")


if __name__ == "__main__":
    main()
