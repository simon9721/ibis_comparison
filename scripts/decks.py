#!/usr/bin/env python3
"""Deck construction shared across the study: HSPICE, ngspice, and pybis subckts.

`spicelab` owns *running* a simulator and reading what comes back. This owns
*writing* what goes in. The two halves were split because deck text had been
copied between scripts far more than anything else here:

    .option post=2 ... header      14 active scripts
    BIBIS native IBIS element      15
    Rload / Cload                  13
    .SUBCKT parsing                11
    pin mapping (nd = {"OUT"...})   7
    NENABLE enable-polarity         5

Copying is not the real cost -- drift is. Two of these have already bitten:

  * `.option post=2` written as the deck's **first** line is consumed as the
    title, so no .tr0 is produced and the run looks like a silent failure. That
    is why `hspice_header` takes the title and emits both, in order.
  * driving EN to the wrong rail silently disables the buffer and the pad never
    moves. `PybisSubckt.enable_level` reads the polarity out of the generated
    subcircuit instead of trusting a flag, which is how the open-drain bench was
    wrong once already.

Nothing here decides *what* to simulate. Stress targets, buffer registries and
model-build names live elsewhere -- see docs/reusable_modules.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "hspice_header", "ngspice_header", "tran", "load", "fixture",
    "supply", "native_ibis", "PybisSubckt",
]


# --------------------------------------------------------------------------- #
# HSPICE
# --------------------------------------------------------------------------- #

def hspice_header(title: str, *, options: str = "post=2 probe accurate ingold=2",
                  temp_c: float = 27.0, comment: str | None = None) -> str:
    """Deck preamble: comment line, `.title`, `.option`, `.temp`.

    The order is not cosmetic. HSPICE treats the first line of a deck as its
    title, so a deck that opens with `.option post=2` loses the option and
    produces no .tr0 -- a failure that looks like the simulator silently doing
    nothing. Emitting a comment line first, then an explicit `.title`, makes that
    unrepresentable.
    """
    lead = f"* {comment}" if comment else f"* {title}"
    return f"{lead}\n.title {title}\n.option {options}\n.temp {temp_c:g}\n"


def tran(step_ns: float, stop_ns: float, *, probe: str | None = None) -> str:
    """`.probe` (optional) and `.tran`, in that order, plus `.end`."""
    out = f".probe tran {probe}\n" if probe else ""
    return f"{out}.tran {step_ns:g}n {stop_ns:g}n\n.end\n"


def supply(node: str, volts: float, *, name: str | None = None) -> str:
    name = name or f"V{node}"
    return f"{name} {node} 0 DC {volts:g}\n"


def load(node: str, r_ohm: float, c_pf: float | None = None, *,
         prefix: str = "") -> str:
    """The study load: a resistor to ground, optionally with a shunt capacitor.

    50 ohm and 2 pF is this study's standard; it is also the load the stress axis
    was defined against, so changing it invalidates the depth targets.
    """
    out = f"R{prefix}load {node} 0 {r_ohm:g}\n"
    if c_pf:
        out += f"C{prefix}load {node} 0 {c_pf:g}p\n"
    return out


def fixture(node: str, v_fixture: float, r_fixture: float = 50.0, *,
            prefix: str = "") -> str:
    """An IBIS-style fixture: `R` from the pad to a DC source at `v_fixture`.

    Deliberately has no shunt capacitance. The two-fixture Ku/Kd solve was tested
    with the 2 pF study load standing in for one leg, and it does not hold -- Ku
    differed by up to 0.352 against a 0.880 peak, because the c_fix correction
    needs a numerical derivative of the load waveform.
    """
    return (f"V{prefix}fix {prefix}fix 0 DC {v_fixture:g}\n"
            f"R{prefix}fix {node} {prefix}fix {r_fixture:g}\n")


def native_ibis(*, ibis_file: str, model: str, supply_v: float,
                mode: int = 2, buffer_type: int | None = None,
                enable: bool = False, probe_state: bool = False,
                pad: str = "pad", data_in: str = "in_dig") -> str:
    """The HSPICE B-element native-IBIS driver, with its reference supplies.

    `mode` is `ramp_rwf`/`ramp_fwf`: 0 uses [Ramp] data, 1 one waveform table, 2
    two (the documented default, and the two-fixture solve IBIS intends). It is
    **not** a table index. Mode 2 silently produces a dead pad on ex2 -- see
    docs/native_vt_waveform_modes.md -- so a native non-response should be
    re-checked at mode 1 before it is believed.

    `probe_state` adds `xv_pu`/`xv_pd`, which the PrimeSim Elements manual
    documents as exposing St_pu/St_pd (0 to 1) on extra nodes -- native's own
    Ku/Kd, the only way to compare coefficients against it.
    """
    out = (supply("pu_ref", supply_v, name="VPU")
           + supply("pd_ref", 0.0, name="VPD")
           + supply("pc_ref", supply_v, name="VPC")
           + supply("gc_ref", 0.0, name="VGC"))
    if enable:
        out += supply("en_sig", supply_v, name="Ven")
        pins = f"pu_ref pd_ref {pad} {data_in} en_sig dig_q pc_ref gc_ref"
    else:
        pins = f"pu_ref pd_ref {pad} {data_in} pc_ref gc_ref"
    btype = "" if buffer_type is None else f" buffer={buffer_type}"
    state = " xv_pu=ku xv_pd=kd" if probe_state else ""
    out += (f"BIBIS {pins}\n"
            f"+ file='{ibis_file}' model='{model}'{btype} typ=typ power=off interpol=1\n"
            f"+ ramp_rwf={mode} ramp_fwf={mode}{state}\n")
    if enable:
        out += "Rdig dig_q 0 1k\n"
    return out


# --------------------------------------------------------------------------- #
# ngspice / pybis
# --------------------------------------------------------------------------- #

def ngspice_header(*, reltol: float = 1e-3, abstol: float = 1e-9,
                   vntol: float = 1e-6, gmin: float | None = 1e-10,
                   method: str | None = "gear", extra: str = "") -> str:
    """`.options` for a pybis subcircuit run.

    The loose default (reltol 1e-3, gear) is what the stressed sweeps use. The
    gate-state build has a convergence floor and aborts around reltol 1e-5 with a
    0.5 ps step, so tightening these is not free.
    """
    parts = [f"reltol={reltol:g}", f"abstol={abstol:g}", f"vntol={vntol:g}"]
    if gmin is not None:
        parts.append(f"gmin={gmin:g}")
    if method:
        parts.append(f"method={method}")
    if extra:
        parts.append(extra)
    return ".options " + " ".join(parts) + "\n"


@dataclass
class PybisSubckt:
    """A generated pybis subcircuit, parsed well enough to instantiate correctly.

    Reading the pin order and the enable polarity out of the file beats trusting
    a flag: pybis emits `NENABLE ... V(EN,VSS) < thr` for an active-low enable and
    `>` for active-high, and driving EN to the wrong rail silently disables the
    buffer so the pad never moves. That produced a false finding on the open-drain
    bench once already.
    """

    path: Path
    text: str
    name: str
    pins: tuple[str, ...]

    @classmethod
    def parse(cls, path: Path | str) -> "PybisSubckt":
        path = Path(path)
        text = path.read_text(errors="ignore")
        m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)", text, re.M | re.I)
        if not m:
            raise ValueError(f"{path}: no .SUBCKT line")
        pins = tuple(p for p in m.group(2).split("params:")[0].split() if "=" not in p)
        return cls(path, text, m.group(1), pins)

    def enable_level(self, supply_v: float) -> float:
        """The EN voltage that *enables* this buffer, read off the subcircuit."""
        m = re.search(r"NENABLE\s+0\s+V\s*=\s*\(\s*V\(EN[^)]*\)\s*([<>])", self.text)
        if not m:
            return supply_v
        return 0.0 if m.group(1) == "<" else supply_v

    def nodes(self, mapping: dict[str, str] | None = None) -> list[str]:
        """Circuit nodes for each pin, in the subcircuit's own order."""
        nd = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
        nd.update({k.upper(): v for k, v in (mapping or {}).items()})
        return [nd.get(p.upper(), p) for p in self.pins]

    def instance(self, ref: str = "X1", mapping: dict[str, str] | None = None) -> str:
        return f"{ref} {' '.join(self.nodes(mapping))} {self.name}\n"
