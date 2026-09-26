#!/usr/bin/env python3
"""Does the pull-up off-delay explain the pedestal on the other two buffers?

On io_buf, scaling `pu_off` alone takes the stress pedestal from +73..+103 ps to
about zero at every one of nine widths, with alignment residuals of 0.00-0.02, and
*improves* the unstressed case at the same time (RMSE against the transistor
38.7 -> 20.1 mV, falling crossing +65.6 -> +1.7 ps).

io_buf's fit is also a striking outlier:

    device      PU on-delay   PU off-delay   ratio
    io_buf         0.9926        0.0677      14.66
    ex2            1.0015        0.6683       1.50
    inv_chain      0.2684        0.2473       1.09

and io_buf is the one device whose pedestal is **positive** (ours later); on
inv_chain and ex2 ours runs *earlier* than native. So the hypothesis is that the
pedestal is the off-delay, and io_buf's sign and size come from its off-delay
being 15x shorter than its on-delay where the others are near 1.

If that holds, the other two should respond to the same knob -- and, since their
pedestal has the opposite sign, respond in the opposite direction.

Each device is run on its own bench and checked against the stress matrix's own
`pybis_pad` column before anything is concluded, so a wrong load cannot be
mistaken for a result.

    py -3.14 scripts/pu_off_across_devices.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
from pedestal_localization import best_lag, outward_window, read  # noqa: E402

R = ROOT / "results"
MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
MODELS = R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "generated_models"
OUT = R / "pu_off_devices_2026-09-04"

BUILD = "InputDrivenTwoStateGateDelayCommandFull"
R_LOAD, C_LOAD_PF = 50.0, 2.0
RISE_NS, EDGE_NS, STOP_NS = 5.000, 0.050, 22.0
SCALES = (1.0, 0.5, 0.25, 0.0)


def fitted_pu_off(device) -> float:
    """The pull-up off-delay, read off the model the matrix actually ran."""
    sub = next(iter((MODELS / device.device_id).glob("*.sub")))
    text = sub.read_text(encoding="utf-8")
    m = re.search(r"^\* PU on/off delay=([0-9.]+)/([0-9.]+)ns", text, re.M)
    if m is None:
        raise RuntimeError(f"{device.device_id}: no PU delay comment")
    return float(m.group(2))


def build(device, pu_off: float, scale: float, width_ps: int) -> Path:
    d = OUT / device.device_id / f"x{scale:g}".replace(".", "p") / f"w{width_ps}"
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "driver.sub").exists():
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                            model_name=device.model,
                            component_name=device.component)
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical",
                                        str(d / "driver.sub"))
        text = (d / "driver.sub").read_text(encoding="utf-8")
        # The comment is rounded; find the full-precision Td that matches it.
        cand = sorted({float(x) for x in re.findall(r"Td=([0-9.e-]+)n", text)},
                      key=lambda v: abs(v - pu_off))
        text, n = re.subn(rf"Td={re.escape(f'{cand[0]:.12g}')}n",
                          f"Td={max(cand[0] * scale, 1e-4):.12g}n", text)
        if n == 0:
            raise RuntimeError(f"{device.device_id}: could not patch pu_off")
        (d / "driver.sub").write_text(text, encoding="utf-8")
    fall = RISE_NS + width_ps / 1000.0
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    supply = device.supply_v
    pwl = (f"PWL(0n 0  {RISE_NS}n 0  {RISE_NS + EDGE_NS}n {supply}  "
           f"{fall}n {supply}  {fall + EDGE_NS}n 0  {STOP_NS}n 0)")
    (d / "run.sp").write_text(
        dk.ngspice_header()
        + ".include driver.sub\n"
        + dk.supply("VCC", supply, name="Vdd")
        + f"Vin IN 0 {pwl}\n"
        + dk.supply("EN", sub.enable_level(supply), name="Ven")
        + sub.instance("X1")
        + dk.load("OUT", R_LOAD, C_LOAD_PF)
        + f".tran 0.002n {STOP_NS}n\n.save V(OUT)\n.end\n", encoding="utf-8")
    if not (d / "run.raw").exists():
        if sl.ngspice(d, timeout_s=1200) is None:
            raise RuntimeError(f"{d} failed")
    return d


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for device in base.DEVICES:
        widths = sorted((int(p.stem.split("_w")[1].rstrip("ps"))
                         for p in MATRIX.glob(f"{device.device_id}_short_high_w*ps.csv")),
                        reverse=True)
        if not widths:
            continue
        pu_off = fitted_pu_off(device)
        print(f"\n  {device.device_id}: fitted pu_off {pu_off:.4f} ns, "
              f"{len(widths)} widths, supply {device.supply_v} V")
        print(f"    {'width':<9}" + "".join(f"{f'x{s:g}':>16}" for s in SCALES)
              + f"{'bench check':>14}")
        for width in widths:
            ref = read(MATRIX / f"{device.device_id}_short_high_w{width}ps.csv")
            t_ref = ref["time_ns"]
            lo, hi = outward_window(t_ref, ref["silicon_pad"], RISE_NS)
            g = np.arange(lo, hi, 0.002)
            nat = np.interp(g, t_ref, ref["hspice_pad"])
            matrix_ours = np.interp(g, t_ref, ref["pybis_pad"])
            cells, check = [], ""
            for scale in SCALES:
                try:
                    d = build(device, pu_off, scale, width)
                except Exception as exc:                    # noqa: BLE001
                    cells.append("   failed")
                    continue
                raw = sl.parse_ngspice_raw(d / "run.raw")
                pad = np.interp(g, sl.time_ns(raw), sl.trace(raw, "out"))
                lag, res = best_lag(g, nat, pad, lo, hi)
                cells.append(f"{lag:+6.0f}({res:4.2f})")
                if scale == 1.0:
                    # Does our x1 rebuild reproduce the matrix's own column?
                    check = f"{np.abs(pad - matrix_ours).max() * 1e3:8.1f} mV"
            print(f"    {width:<9}" + "".join(f"{c:>16}" for c in cells)
                  + f"{check:>14}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
