#!/usr/bin/env python3
"""Hypothesis: the gate should be a SLOW ramp with a STEEP map, not a delay plus a fast ramp.

`gate_physics_2026-09-08` measured the real predriver gate and found Ku to be a
static map of it. The real gate is a slow node: on inv_chain it takes ~250 ps to
arrive, on ex2 ~700 ps. Our shipped model instead represents the same Ku(t) as

    command delay (pu_on, 0.27 ns on inv)  ->  fast RC gate (tau_rise 20 ps)  ->  map

At full swing the two descriptions are indistinguishable -- both reproduce the
same Ku(t) -- so the characterisation cannot tell them apart. Under truncation
they differ completely: a delay-then-fast-ramp is either fully on or fully off
at the reversal, while a slow ramp is *partway*, and a steep map turns "partway"
into a Ku that has not reached 1. `cross_device_stress_2026-09-08` measured that
exact symptom (entry excess, r = 0.889 with the peak error).

So this rebuilds the gate as slow-ramp-plus-steep-map, **derived so that the
full-swing Ku(t) is preserved by construction**: pick tau_rise' = k x shipped,
take the shipped full-swing gate-part Ku(t) on the rise, and define

    map'(g) = Ku_shipped(t)   where   g = 1 - exp(-(t - t_on) / tau_rise')

Two variants of the fall: `dual` keeps a separate fall map derived the same way
(exact at full swing, may jump at a truncated reversal); `single` uses the rise
map for both branches -- the physics -- with tau_fall' fitted to the shipped fall.

Then run the stressed widths and score against the transistor. If the peak excess
collapses as k grows while full swing stays put, the hypothesis stands.

    py -3.14 scripts/gate_ramp_prototype.py --variant inv_base8
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spice_decks as dk  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402
from pedestal_localization import best_lag, outward_window  # noqa: E402

R = ROOT / "results"
VAR = R / "variant_stress_cases_2026-09-04"
INV = R / "inv_chain_variants_2026-09-02"
EX2 = R / "ex2_variants_2026-09-03"
BUILD = "InputDrivenTwoStateGateDelayCommandFull"
RISE_NS, STOP_NS, R_LOAD, C_LOAD_PF = 5.0, 22.0, 50.0, 2.0
PROBES = ("ku", "kd", "gup", "guptarget", "kugate_base", "kugate_on", "kugate_off", "kures_table",
          "gdn", "gdntarget", "kdgate_base", "pucmdlvl", "pup5", "pup6", "pucmdraw")

VARIANTS = {
    "inv_base8": (1.8, INV / "base8/selection/tr1ps/invchain_base8_tr1ps.ibs"),
    "inv_stage4": (1.8, INV / "stage4/selection/tr1ps/invchain_stage4_tr1ps.ibs"),
    "inv_skewp": (1.8, INV / "skewp/selection/tr1ps/invchain_skewp_tr1ps.ibs"),
    "inv_weak": (1.8, INV / "weak/selection/tr1ps/invchain_weak_tr1ps.ibs"),
    "ex2_base": (3.3, EX2 / "base/selection/tr1ps/ex2_base_tr1ps.ibs"),
    "ex2_slowpre": (3.3, EX2 / "slowpre/selection/tr1ps/ex2_slowpre_tr1ps.ibs"),
    "ex2_skewp": (3.3, EX2 / "skewp/selection/tr1ps/ex2_skewp_tr1ps.ibs"),
    "ex2_weak": (3.3, EX2 / "weak/selection/tr1ps/ex2_weak_tr1ps.ibs"),
    "ex2_nomiller": (3.3, EX2 / "nomiller/selection/tr1ps/ex2_nomiller_tr1ps.ibs"),
    # io_buf comes from the stress matrix: five probed transistor runs, 50 ps edges,
    # native from the matrix CSVs. The other regime -- it must NOT get worse.
    "io_buf": (3.3, R / "io_buf_fast_edge_regen_2026-08-19/source/io_buf_fast_50ps.ibs"),
    # the probed base buffers of the matrix (n4 / vout7 recorded in the transistor runs)
    "ex2": (3.3, R / "stress_method_matrix_2026-08-20/pad_match/hspice_references/ex2/fast_5ps/r50_c2pf/short_high_w810ps_810ps/native/input.ibs"),
    "inv_chain": (1.8, R / "stress_method_matrix_2026-08-20/pad_match/hspice_references/inv_chain/fast_5ps/r50_c2pf/short_high_w104ps_104ps/native/input.ibs"),
}
MX = R / "stress_method_matrix_2026-08-20"
MATRIX_SET = ("io_buf", "ex2", "inv_chain")
EDGE_PS = {"io_buf": 50.0, "ex2": 50.0, "inv_chain": 50.0}


def ibis_names(ibis: Path) -> tuple[str, str]:
    t = ibis.read_text(errors="ignore")
    return (re.search(r"^\[Model\]\s+(\S+)", t, re.M).group(1),
            re.search(r"^\[Component\]\s+(.+?)\s*$", t, re.M).group(1))


def pwl_width(sp: Path) -> float:
    m = re.search(r"PWL\(([^)]*)\)", sp.read_text(errors="ignore"), re.S)
    nums = re.findall(r"([0-9.]+)n\s+[0-9.]+", m.group(1))
    return float(nums[3]) - RISE_NS


def cases(variant: str) -> list[tuple[int, float, Path]]:
    """(depth, width_ns, case dir) for the current dir per depth."""
    if variant in MATRIX_SET:
        out_m = []
        for d in sorted((MX / f"pad_match/hspice_references/{variant}/transistor/r50_c2pf").glob("short_high_w*ps_*")):
            w = int(re.search(r"_w(\d+)ps", d.name).group(1))
            out_m.append((w, w / 1000.0, d))     # "depth" label is the width in ps
        return sorted(out_m, reverse=True)
    out: dict[int, tuple[float, Path]] = {}
    for d in sorted((VAR / variant).glob("depth*_w*ps"), key=lambda p: p.stat().st_mtime):
        if not (d / "transistor/run.tr0").exists():
            continue
        depth = int(re.match(r"depth(\d+)_", d.name).group(1))
        out[depth] = (pwl_width(d / "transistor/run.sp"), d)
    return sorted([(k, w, d) for k, (w, d) in out.items()], reverse=True)


# --------------------------------------------------------------------------- #
# Running ours
# --------------------------------------------------------------------------- #

def run_ours(d: Path, sub_text: str, sup: float, width: float):
    d.mkdir(parents=True, exist_ok=True)
    (d / "driver.sub").write_text(sub_text, encoding="utf-8")
    sub = dk.PybisSubckt.parse(d / "driver.sub")
    pwl = sl.pulse(0.0, sup, [RISE_NS, RISE_NS + width], edge_ps=EDGE_PS.get(VARIANT_NAME, 1.0), stop_ns=STOP_NS)
    saves = " ".join(f"V(X1.{p})" for p in PROBES)
    deck = (dk.ngspice_header() + ".include driver.sub\n" + dk.supply("VCC", sup, name="Vdd")
            + f"Vin IN 0 {pwl}\n" + dk.supply("EN", sub.enable_level(sup), name="Ven")
            + sub.instance("X1") + dk.load("OUT", R_LOAD, C_LOAD_PF)
            + f".tran 0.002n {STOP_NS}n\n.save V(OUT) {saves}\n.end\n")
    # Cache on BOTH the deck and the subcircuit: the deck is identical across
    # builds (it only includes driver.sub), and keying on it alone reused stale
    # results once (the "fenced" residual builds, 2026-09-09).
    prev = d / "run.sp"
    stamp = d / "driver.sub.used"
    fresh = (prev.exists() and prev.read_text(encoding="utf-8") == deck and (d / "run.raw").exists()
             and stamp.exists() and stamp.read_text(encoding="utf-8") == sub_text)
    if not fresh:
        prev.write_text(deck, encoding="utf-8")
        stamp.write_text(sub_text, encoding="utf-8")
        if sl.ngspice(d, timeout_s=1800) is None:
            raise RuntimeError(f"ngspice failed: {d}")
    raw = sl.parse_ngspice_raw(d / "run.raw")
    t = sl.time_ns(raw)
    out = {"t": t, "pad": sl.trace(raw, "out")}
    for p in PROBES:
        try:
            out[p] = sl.signal(raw, f"v(x1.{p})")
        except Exception:                               # noqa: BLE001
            out[p] = np.full(len(t), np.nan)
    return out


# --------------------------------------------------------------------------- #
# Deriving the slow-ramp gate
# --------------------------------------------------------------------------- #

def gate_taus(sub_text: str) -> tuple[float, float]:
    m = re.search(r"^BGUP GUP 0 I = .*?\?\s*([0-9.e+-]+)n\s*:\s*([0-9.e+-]+)n", sub_text, re.M)
    return float(m.group(1)), float(m.group(2))


def as_pwl(node_line_prefix: str, xs, ys) -> str:
    pairs = ", ".join(f"{x:.6g}, {y:.6g}" for x, y in zip(xs, ys))
    return f"{node_line_prefix} pwl(min(max(V(GUP), 0), 1), {pairs})"


def derive(full: dict, tau_r_new: float, tau_f_ship: float, mode: str):
    """Return (rise map xs, ys), (fall map xs, ys) or None, tau_fall_new, fall fit rms."""
    t, tgt, gb = full["t"], full["guptarget"], full["kugate_base"]
    on = np.where((t > RISE_NS - 0.1) & (tgt > 0.5))[0]
    t_on = float(t[on[0]])
    off = np.where((t > t_on) & (tgt < 0.5))[0]
    t_off = float(t[off[0]])
    # rise map: g = 1 - exp(-(t - t_on)/tau)  ->  t = t_on - tau ln(1 - g)
    g = np.linspace(0.0, 0.999, 240)
    tr = t_on - tau_r_new * np.log(1.0 - g)
    tr = np.minimum(tr, t_off - 0.002)
    y_rise = np.interp(tr, t, gb)
    rise = (np.append(g, 1.0), np.append(y_rise, y_rise[-1]))
    # fall data: gate part after t_off
    tf = t[(t >= t_off) & (t < t_off + 6.0)]
    y_fall = np.interp(tf, t, gb)
    g_off = 1.0 - np.exp(-(t_off - t_on) / tau_r_new)
    if mode == "dual":
        # separate fall map with tau_fall scaled like the rise
        tau_f_new = tau_f_ship * (tau_r_new / gate_taus_cache["r"])
        gf = g_off * np.exp(-(tf - t_off) / tau_f_new)
        order = np.argsort(gf)
        xs, ys = gf[order], y_fall[order]
        keep = np.concatenate([[True], np.diff(xs) > 1e-4])
        fall = (xs[keep], ys[keep])
        return rise, fall, tau_f_new, 0.0
    # single map: fit tau_fall so that rise_map(g_off exp(-(t-t_off)/tau_f)) ~ y_fall
    best = (None, 1e9)
    for tau_f in np.geomspace(0.5 * tau_f_ship, 200 * tau_f_ship, 80):
        gf = g_off * np.exp(-(tf - t_off) / tau_f)
        pred = np.interp(gf, rise[0], rise[1])
        err = float(np.sqrt(np.mean((pred - y_fall) ** 2)))
        if err < best[1]:
            best = (tau_f, err)
    return rise, None, best[0], best[1]


gate_taus_cache: dict[str, float] = {}
VARIANT_NAME = ""


def patch(sub_text: str, tau_r: float, tau_f: float, rise, fall) -> str:
    s = re.sub(r"^(BGUP GUP 0 I = .*?\?\s*)[0-9.e+-]+n(\s*:\s*)[0-9.e+-]+n",
               lambda m: f"{m.group(1)}{tau_r:.12g}n{m.group(2)}{tau_f:.12g}n", sub_text, count=1, flags=re.M)
    s = re.sub(r"^BKUGATE_ON KUGATE_ON 0 V = .*$", as_pwl("BKUGATE_ON KUGATE_ON 0 V =", *rise), s, count=1, flags=re.M)
    f = fall if fall is not None else rise
    s = re.sub(r"^BKUGATE_OFF KUGATE_OFF 0 V = .*$", as_pwl("BKUGATE_OFF KUGATE_OFF 0 V =", *f), s, count=1, flags=re.M)
    return s


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

def tr0_pad(p: Path):
    raw = sl.parse_hspice_tr0(p)
    return sl.time_ns(raw), np.asarray(raw[next(k for k in raw if "pad" in k)], float)


def native_pad(variant: str, depth: int, d: Path):
    if variant in MATRIX_SET:
        from pedestal_localization import read
        ref = read(MX / "delay_cmd/waveforms" / f"{variant}_short_high_w{depth}ps.csv")
        return ref["time_ns"], ref["hspice_pad"]
    return tr0_pad(d / "native/run.tr0")


def score(t_si, si, t_m, m, width):
    rev = RISE_NS + width
    g = np.arange(rev - 0.1, rev + 3.0, 0.001)
    a, b = np.interp(g, t_si, si), np.interp(g, t_m, m)
    ia = int(np.argmax(a))
    lo, hi = outward_window(t_si, si, RISE_NS)
    gg = np.arange(lo, hi, 0.002)
    lag, res = best_lag(gg, np.interp(gg, t_si, si), np.interp(gg, t_m, m), lo, hi)
    return 100.0 * (b.max() - a[ia]) / a[ia], lag, res, g[ia]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="inv_base8")
    ap.add_argument("--ks", type=float, nargs="+", default=[1, 2, 4, 8, 16, 32])
    ap.add_argument("--modes", nargs="+", default=["single", "dual"])
    args = ap.parse_args()
    sup, ibis = VARIANTS[args.variant]
    global VARIANT_NAME
    VARIANT_NAME = args.variant
    OUT = R / "gate_ramp_prototype_2026-09-09" / args.variant
    OUT.mkdir(parents=True, exist_ok=True)

    model, comp = ibis_names(ibis)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
    ship_dir = OUT / "shipped"
    ship_dir.mkdir(parents=True, exist_ok=True)
    if not (ship_dir / "driver.sub").exists():
        subcircuit.generate_spice_model("Output", BUILD, data, "Typical", str(ship_dir / "driver.sub"))
    ship = (ship_dir / "driver.sub").read_text(encoding="utf-8")
    tau_r0, tau_f0 = gate_taus(ship)
    gate_taus_cache["r"] = tau_r0
    print(f"  {args.variant}: shipped tau_rise {tau_r0*1e3:.1f} ps, tau_fall {tau_f0*1e3:.1f} ps")

    full = run_ours(ship_dir / "full", ship, sup, 10.0)
    cs = cases(args.variant)
    refs = {depth: tr0_pad(d / "run.tr0" if args.variant in MATRIX_SET else d / "transistor/run.tr0")
            for depth, _, d in cs}
    nats = {depth: native_pad(args.variant, depth, d) for depth, _, d in cs}

    rows = []
    print(f"\n    {'mode':<7}{'k':>4}{'tau_r ps':>9}{'tau_f ps':>9}{'fallfit':>8}{'FS Ku rms':>10} | "
          + "".join(f"{f'd{dp} pk%':>9}" for dp, _, _ in cs) + " | "
          + "".join(f"{f'd{dp} lag':>9}" for dp, _, _ in cs))
    # references: shipped and native rows
    for name, getter in (("shipped", None), ("native", nats)):
        cells_pk, cells_lag = [], []
        for depth, w, d in cs:
            if getter is None:
                r = run_ours(ship_dir / f"d{depth}", ship, sup, w)
                pk, lag, res, _ = score(*refs[depth], r["t"], r["pad"], w)
            else:
                pk, lag, res, _ = score(*refs[depth], *nats[depth], w)
            cells_pk.append(pk)
            cells_lag.append(lag)
        rows.append(dict(mode=name, k=0, tau_r_ps=tau_r0 * 1e3, tau_f_ps=tau_f0 * 1e3, fallfit=0, fs_ku_rms=0,
                         **{f"pk_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, cells_pk)},
                         **{f"lag_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, cells_lag)}))
        print(f"    {name:<7}{'-':>4}{tau_r0*1e3:>9.1f}{tau_f0*1e3:>9.1f}{'-':>8}{'-':>10} | "
              + "".join(f"{v:>9.1f}" for v in cells_pk) + " | " + "".join(f"{v:>9.0f}" for v in cells_lag))

    tf_full = full["t"]
    for mode in args.modes:
        for k in args.ks:
            tau_r = tau_r0 * k
            rise, fall, tau_f, fit = derive(full, tau_r, tau_f0, mode)
            text = patch(ship, tau_r, tau_f, rise, fall)
            tag = OUT / f"{mode}_k{k:g}"
            fs = run_ours(tag / "full", text, sup, 10.0)
            m = (tf_full > RISE_NS - 0.5) & (tf_full < 17.0)
            ku_rms = float(np.sqrt(np.mean((np.interp(tf_full[m], fs["t"], fs["ku"]) - full["ku"][m]) ** 2)))
            cells_pk, cells_lag = [], []
            for depth, w, d in cs:
                r = run_ours(tag / f"d{depth}", text, sup, w)
                pk, lag, res, _ = score(*refs[depth], r["t"], r["pad"], w)
                cells_pk.append(pk)
                cells_lag.append(lag)
            rows.append(dict(mode=mode, k=k, tau_r_ps=round(tau_r * 1e3, 1), tau_f_ps=round(tau_f * 1e3, 1),
                             fallfit=round(fit, 4), fs_ku_rms=round(ku_rms, 4),
                             **{f"pk_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, cells_pk)},
                             **{f"lag_d{dp}": round(v, 1) for (dp, _, _), v in zip(cs, cells_lag)}))
            print(f"    {mode:<7}{k:>4g}{tau_r*1e3:>9.1f}{tau_f*1e3:>9.1f}{fit:>8.3f}{ku_rms:>10.4f} | "
                  + "".join(f"{v:>9.1f}" for v in cells_pk) + " | " + "".join(f"{v:>9.0f}" for v in cells_lag))

    with (OUT / "sweep.csv").open("w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wri.writeheader()
        wri.writerows(rows)
    print(f"\n  wrote {OUT / 'sweep.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
