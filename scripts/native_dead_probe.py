#!/usr/bin/env python3
"""Why is HSPICE native IBIS dead on the regenerated variant files?

The dead files differ from the working shipped ones only in the V-T tables' time base
(1000 rows over 2.67 ns at 2.7 ps, against 1000 rows over 8 ns at 8 ps on ex2). This takes
the dead ex2_base file, edits nothing but the V-T tables' time base, and runs native on the
same 812 ps bench that was dead:

    asis        the file as used (dead)
    span8ns     the same waveforms resampled onto 8 ps steps out to 8 ns (final value held)
    span8ns_500 same, 500 rows
    coarse      the original 2.67 ns span resampled onto 100 rows
    span4ns     resampled out to 4 ns
    full10ns    the 'asis' file driven with a 10 ns pulse (full swing) instead of 812 ps

    py -3.14 scripts/native_dead_probe.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402

R = ROOT / "results"
SRC = R / "variant_stress_cases_2026-09-04/ex2_base/depth50_w812ps/native/input.ibs"
OUT = R / "native_dead_probe_2026-09-11"
SUP = 3.3


def resample_tables(text: str, t_end_ns: float | None, rows: int) -> str:
    """Rewrite every [Rising Waveform]/[Falling Waveform] table onto `rows` points spanning
    0..t_end_ns (default: the table's own span), holding the last value beyond the data."""
    out, i, lines = [], 0, text.splitlines()
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if line.strip() in ("[Rising Waveform]", "[Falling Waveform]"):
            i += 1
            while i < len(lines) and not re.match(r"^\s*[-+0-9.eE]+[a-zA-Z]*\s+[-+0-9.eE]", lines[i]):
                out.append(lines[i]); i += 1
            rows_t, rows_v = [], []
            while i < len(lines) and re.match(r"^\s*[-+0-9.eE]+[a-zA-Z]*\s+[-+0-9.eE]", lines[i]):
                parts = lines[i].split()
                rows_t.append(_num(parts[0])); rows_v.append([_num(x) for x in parts[1:4]])
                i += 1
            t = np.array(rows_t); v = np.array(rows_v)
            te = t_end_ns * 1e-9 if t_end_ns else t[-1]
            tn = np.linspace(0, te, rows)
            for k in range(rows):
                vals = [np.interp(tn[k], t, v[:, c]) if tn[k] <= t[-1] else v[-1, c] for c in range(v.shape[1])]
                out.append(f"{tn[k]:.6e}s\t" + "\t".join(f"{x:.6f}V" for x in vals))
            continue
        i += 1
    return "\n".join(out) + "\n"


def _num(s: str) -> float:
    m = re.match(r"^([-+0-9.eE]+)([a-zA-Z]*)$", s)
    val, unit = float(m.group(1)), m.group(2)
    scale = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "": 1.0}
    u = unit[:1] if unit and unit[0] in "fpnum" else ""
    return val * scale.get(u, 1.0)


def run_native(d: Path, ibis_text: str, width_ns: float):
    d.mkdir(parents=True, exist_ok=True)
    (d / "input.ibs").write_text(ibis_text, encoding="utf-8")
    deck = f"""* native dead probe
.title native probe
.option post=2 probe accurate ingold=2
.temp 27
Vin in_dig 0 PWL(0n 0  5n 0  5.001n {SUP}  {5 + width_ns}n {SUP}  {5 + width_ns + 0.001}n 0  22n 0)
VPU pu_ref 0 DC {SUP}
VPD pd_ref 0 DC 0
VPC pc_ref 0 DC {SUP}
VGC gc_ref 0 DC 0
BIBIS pu_ref pd_ref pad in_dig pc_ref gc_ref
+ file='input.ibs' model='driver' buffer=2 typ=typ power=off interpol=1
+ ramp_rwf=2 ramp_fwf=2 xv_pu=ku xv_pd=kd
Rload pad 0 50.0
Cload pad 0 2.0p
.probe tran V(pad) V(ku) V(kd)
.tran 0.002n 22.0n
.end
"""
    (d / "run.sp").write_text(deck, encoding="utf-8")
    rc = base.run_process([str(default_hspice()), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 600)
    if rc != 0 or not (d / "run.tr0").exists():
        return None
    raw = sl.parse_hspice_tr0(d / "run.tr0")
    t = sl.time_ns(raw)
    pad, ku, kd = (np.asarray(raw[k], float) for k in ("v(pad)", "v(ku)", "v(kd)"))
    m = (t > 5.0) & (t < 5.0 + width_ns + 3.0)
    return dict(pad_max=float(pad[m].max()), ku_max=float(ku[m].max()), kd_min=float(kd[m].min()),
                t_pad_max=float(t[m][np.argmax(pad[m])]))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    src = SRC.read_text(errors="ignore")
    variants = {
        "asis": (src, 0.8125),
        "full10ns": (src, 10.0),
        "span4ns": (resample_tables(src, 4.0, 1000), 0.8125),
        "span8ns": (resample_tables(src, 8.0, 1000), 0.8125),
        "span8ns_500": (resample_tables(src, 8.0, 500), 0.8125),
        "coarse100": (resample_tables(src, None, 100), 0.8125),
        "coarse300": (resample_tables(src, None, 300), 0.8125),
    }
    print(f"  {'case':14s} {'rows/span':>14s} | {'pad max (V)':>11s} {'at (ns)':>8s} {'Ku max':>7s} {'Kd min':>7s}")
    for name, (txt, w) in variants.items():
        r = run_native(OUT / name, txt, w)
        # describe the first rising table
        lines = txt.splitlines()
        k = next(i for i, l in enumerate(lines) if l.strip() == "[Rising Waveform]")
        rows = []
        for l in lines[k + 1:]:
            if re.match(r"^\s*[-+0-9.eE]+[a-zA-Z]*\s+[-+0-9.eE]", l):
                rows.append(l)
            elif rows:
                break
        span = _num(rows[-1].split()[0]) * 1e9
        desc = f"{len(rows)} / {span:.2f} ns"
        if r is None:
            print(f"  {name:14s} {desc:>14s} | hspice failed")
        else:
            print(f"  {name:14s} {desc:>14s} | {r['pad_max']:11.3f} {r['t_pad_max']:8.2f} {r['ku_max']:7.2f} {r['kd_min']:7.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
