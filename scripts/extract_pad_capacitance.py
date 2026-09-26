#!/usr/bin/env python3
"""The buffer's real pad capacitance versus bias, from the transistor netlist.

C_comp is declared as one number and installed as a fixed **linear** capacitor.
`ccomp_accumulation_2026-09-04` showed that capacitor is what makes both IBIS
implementations fall progressively behind the transistor on the way out of an
event. The live hypothesis is that it is the wrong *shape* rather than the wrong
*size*: real die capacitance is a junction capacitance and varies with bias, and
the way out is where the pad spends longest at intermediate voltages.

Nobody has measured what the netlist's capacitance actually is. This does.

**Method: a ramp minus a DC sweep.** At the pad,

    I_total(V) = I_conduction(V) + C(V) dV/dt

A single ramp cannot separate those -- the driver's own I-V swamps the
displacement current. A DC sweep is the conduction term with dV/dt exactly zero,
so subtracting it leaves the displacement current alone:

    C(V) = [I_ramp(V) - I_dc(V)] / slope

Differencing *two ramps* was tried first and does not work here: at a slope slow
enough to stay quasi-static the displacement current is ~0.3% of the conduction
current, and the subtraction returned capacitances as negative as -8 pF. Against a
DC sweep the subtraction is exact rather than a difference of two large,
nearly-equal numbers.

**And a cross-check that needs no subtraction at all.** io_buf has an output
enable; with the output disabled the conduction term is gone and the ramp current
*is* the displacement current. That is the textbook C_comp measurement, and it
gives an independent read on the same quantity.

Measured in both driven states as well, because the IBIS spec allows C_comp to be
split per branch (`C_comp_pullup` / `C_comp_pulldown`) precisely because they
differ -- and none of our files use it.

    py -3.14 scripts/extract_pad_capacitance.py
    py -3.14 scripts/extract_pad_capacitance.py --device ex2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
import spicelab as sl  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

OUT = ROOT / "results" / "pad_capacitance_2026-09-04"
FIGS = ROOT / "results" / "meeting_deck_2026-09-04" / "figures"

# Fast enough that the displacement current is a workable fraction of the
# conduction current, slow enough that the buffer stays quasi-static: io_buf's
# internal nodes settle in ~100 ps, so a 2 ns ramp is 20x slower than the circuit
# it is probing.
RAMP_NS = 2.0
SETTLE_NS = 20.0        # let the state establish before the ramp starts

DECLARED_PF = {"io_buf": 1.2, "inv_chain": 0.468, "ex2": 5.0}
NL = "\n"


def core_lines(device, oe_v: float | None) -> str:
    if device.device_id == "io_buf":
        return (".include 'hspice.mod'" + NL
                + ".subckt SPICE_BUF in oe out in_sense vdd vss" + NL
                + ".include 'io_buf.sp'" + NL
                + ".ends SPICE_BUF" + NL
                + f"Voe oe 0 DC {device.supply_v if oe_v is None else oe_v}" + NL
                + "XBUF in_dig oe pad in_sense vdd 0 SPICE_BUF")
    if device.device_id == "inv_chain":
        return (".include 'HL18G-S3.7S.lib'" + NL
                + ".include 'invchain_ref_ngspice.sub'" + NL
                + "XBUF in_dig pad vdd 0 invchain_ref")
    return (".include 'hspice.mod'" + NL
            + ".subckt ex2_buffer in out vdd gnd" + NL
            + ".include 'buffer.sp'" + NL
            + ".ends ex2_buffer" + NL
            + "XBUF in_dig pad vdd 0 ex2_buffer")


def deck(device, v_in: float, analysis: str, oe_v: float | None = None) -> str:
    """Buffer held in one state; `analysis` is 'ramp' or 'dc'."""
    supply = device.supply_v
    if analysis == "dc":
        drive = "Vpad pad 0 DC 0"
        run_line = (f".dc Vpad 0 {supply} {supply / 400:.6f}" + NL
                    + ".probe dc I(Vpad)")
    else:
        drive = (f"Vpad pad 0 PWL(0n 0  {SETTLE_NS}n 0  "
                 f"{SETTLE_NS + RAMP_NS}n {supply})")
        run_line = (".probe tran V(pad) I(Vpad)" + NL
                    + f".tran {RAMP_NS / 4000:.6f}n {SETTLE_NS + RAMP_NS}n")
    return (f"* {device.device_id} pad capacitance, {analysis}, in={v_in}" + NL
            + ".title pad capacitance" + NL
            + ".option post=2 probe ingold=2" + NL
            + ".temp 27" + NL
            + f"Vdd vdd 0 DC {supply}" + NL
            + f"Vin in_dig 0 DC {v_in}" + NL
            + core_lines(device, oe_v) + NL
            + drive + NL
            + run_line + NL
            + ".end" + NL)


def run(device, v_in: float, analysis: str, tag: str, hspice: Path,
        oe_v: float | None = None):
    """(pad voltage, current drawn by the pad) over the swept range."""
    d = OUT / device.device_id / tag
    d.mkdir(parents=True, exist_ok=True)
    base.copy_transistor_inputs(device, d)
    (d / "run.sp").write_text(deck(device, v_in, analysis, oe_v), encoding="utf-8")
    result = d / ("run.sw0" if analysis == "dc" else "run.tr0")
    if not result.exists():
        # sl.hspice reports success by returning the .tr0 path, and a DC-only
        # deck never writes one -- so check for the file this analysis actually
        # produces rather than trusting the return value.
        sl.hspice(d, timeout_s=1800, hspice_path=hspice)
        if not result.exists():
            raise RuntimeError(f"{tag} failed -- see run.lis")
    if analysis == "dc":
        # A .sw0 is byte-for-byte a .tr0 except that its independent variable is
        # named VOLTS rather than TIME, which is the only thing the shared parser
        # keys on. Both names are five characters, so swapping them in a scratch
        # copy keeps the fixed-width layout intact.
        patched = d / "run_as_tr0.tr0"
        patched.write_bytes(result.read_bytes().replace(b"VOLTS", b"TIME ", 1))
        raw = sl.parse_hspice_tr0(patched)
        return sl.time_ns(raw) / 1e9, -sl.signal(raw, "i(vpad)", "i1(vpad)")
    raw = sl.parse_hspice_tr0(result)
    # I(Vpad) is reported flowing from the source's + node through the source, so
    # the current the pad draws from it is the negative of that.
    cur = -sl.signal(raw, "i(vpad)", "i1(vpad)")
    t = sl.time_ns(raw)
    v = sl.trace(raw, "pad")
    w = (t > SETTLE_NS + 0.02 * RAMP_NS) & (t < SETTLE_NS + 0.98 * RAMP_NS)
    return v[w], cur[w]


def capacitance(device, v_in: float, hspice: Path):
    """C(V) in farads: the ramp's current less the DC sweep's, over the slope."""
    supply = device.supply_v
    state = "hi" if v_in > supply / 2 else "lo"
    v_r, i_r = run(device, v_in, "ramp", f"in{state}_ramp", hspice)
    v_d, i_d = run(device, v_in, "dc", f"in{state}_dc", hspice)
    # Stop at 85% of the rail. Above that the driven device's own conduction is
    # collapsing toward zero and changing steeply with V, the quasi-static
    # assumption behind the subtraction fails, and the pull-up state returns
    # capacitances as negative as -4 pF. The physics of interest is well inside.
    grid = np.linspace(0.05 * supply, 0.85 * supply, 200)
    slope = supply / (RAMP_NS * 1e-9)
    return grid, (np.interp(grid, v_r, i_r) - np.interp(grid, v_d, i_d)) / slope


def high_z(device, hspice: Path):
    """io_buf only: output disabled, so the ramp current is displacement alone."""
    supply = device.supply_v
    v, i = run(device, 0.0, "ramp", "hiz_ramp", hspice, oe_v=0.0)
    grid = np.linspace(0.05 * supply, 0.85 * supply, 200)
    return grid, np.interp(grid, v, i) / (supply / (RAMP_NS * 1e-9))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--device", action="append",
                    choices=[d.device_id for d in base.DEVICES])
    args = ap.parse_args()
    hspice = default_hspice()
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = [d for d in base.DEVICES
              if d.device_id in set(args.device or ["io_buf"])]

    fig, axes = plt.subplots(1, len(wanted), figsize=(6.0 * len(wanted), 4.6),
                             squeeze=False)
    for ax, device in zip(axes[0], wanted):
        declared = DECLARED_PF[device.device_id]
        print(f"\n  {device.device_id}: declared C_comp {declared} pF")
        for v_in, label, colour in ((0.0, "input low (pull-down on)", "#2E8B57"),
                                    (device.supply_v, "input high (pull-up on)",
                                     "#C05621")):
            v, c = capacitance(device, v_in, hspice)
            ax.plot(v, c * 1e12, color=colour, lw=2.4, label=label)
            print(f"    {label:<28} {c.min()*1e12:6.2f} .. {c.max()*1e12:6.2f} pF"
                  f"   mid-rail {np.interp(device.supply_v/2, v, c)*1e12:6.2f}")
            np.savetxt(OUT / device.device_id /
                       f"cv_in{'hi' if v_in else 'lo'}.csv",
                       np.column_stack([v, c]), delimiter=",",
                       header="pad_v,c_farad", comments="")
        if device.device_id == "io_buf":
            v, c = high_z(device, hspice)
            ax.plot(v, c * 1e12, color="#2B6CA3", lw=2.0, ls=":",
                    label="output disabled (high-Z)")
            print(f"    {'output disabled (high-Z)':<28} "
                  f"{c.min()*1e12:6.2f} .. {c.max()*1e12:6.2f} pF"
                  f"   mid-rail {np.interp(device.supply_v/2, v, c)*1e12:6.2f}")
            np.savetxt(OUT / device.device_id / "cv_hiz.csv",
                       np.column_stack([v, c]), delimiter=",",
                       header="pad_v,c_farad", comments="")
        ax.axhline(declared, color="#111", ls="--", lw=1.8,
                   label=f"declared C_comp {declared} pF")
        ax.set_title(device.device_id, fontsize=13, fontweight="bold")
        ax.set_xlabel("Pad voltage (V)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=10)
    axes[0][0].set_ylabel("pad capacitance (pF)")
    fig.suptitle("What the netlist's pad capacitance actually is",
                 fontsize=15, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "pad_capacitance.png", dpi=200)
    plt.close(fig)
    print("\n  pad_capacitance.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
