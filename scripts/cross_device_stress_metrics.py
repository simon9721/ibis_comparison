#!/usr/bin/env python3
"""One instrument, every stressed buffer: the io_buf findings tested for generality.

Everything established on io_buf short-high in the 2026-09-07 series is a claim
about one buffer. This runs the same measurements over every stressed short-high
case that exists -- the three base buffers in the stress matrix and the nine
variants at five depths -- so trends can be read across families.

v2. The first pass scored Ku in a window 50-400 ps *after the pad peak*, which is
right for io_buf and empty for everyone else: on inv_chain the whole event is a
~200 ps spike, on ex2 the pull-up is fully off by then. So the scoring window is
now the **event itself**, bounded by the transistor's own coefficients:

    t_on   first time after the reversal the transistor's Ku exceeds 0.10
    t_off  first time after the pad peak its Kd is back above 0.90

and the timing metrics are the two crossings that the traces showed carry the
defect on every buffer:

    ku_off50   when Ku falls back through 0.5 after its peak   (pull-up turn-off)
    kd_on50    when Kd rises back through 0.5                  (pull-down re-engage)

reported as model minus transistor, ps, so positive means late.

The reference is the transistor: pad into the study load, Ku/Kd re-solved from
its two fixture runs at 5 ps (2/10 ps spread recorded in-window). Native is
flagged invalid where its pad never rises (all ex2 variants and inv_stage4 on the
tr1ps IBIS files); our `delay_cmd` build is scored everywhere.

The "bump" is kept only where it is a genuine secondary event: the pad must fall
below 5% of its peak and then rise by more than 5 mV. io_buf has one; ex2 and
inv_chain do not, and v1's argmax on a monotone tail was an artifact.

Depth (% of the settled full-swing excursion) comes from the variant dir name,
and for the matrix cases from the transistor plateau: io_buf 1.5233 V
(`defect_b_full_swing`, hspice.mod -- the loaded-swing control used the ngspice
card), inv_chain 1.4222, ex2 1.5451.

    py -3.14 scripts/cross_device_stress_metrics.py
"""
from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from extract_silicon_kukd import solve_silicon_kukd  # noqa: E402
from pedestal_localization import best_lag, outward_window, read  # noqa: E402

R = ROOT / "results"
VAR = R / "variant_stress_cases_2026-09-04"
MATRIX = R / "stress_method_matrix_2026-08-20" / "delay_cmd"
INV = R / "inv_chain_variants_2026-09-02"
EX2 = R / "ex2_variants_2026-09-03"
OUT = R / "cross_device_stress_2026-09-08"
RISE_NS = 5.0
PLATEAU = {"io_buf": 1.5233, "inv_chain": 1.4222, "ex2": 1.5451}

VARIANTS = {
    "inv_base8":  ("inv_chain", 1.8, INV / "base8/selection/tr1ps/invchain_base8_tr1ps.ibs"),
    "inv_stage4": ("inv_chain", 1.8, INV / "stage4/selection/tr1ps/invchain_stage4_tr1ps.ibs"),
    "inv_skewp":  ("inv_chain", 1.8, INV / "skewp/selection/tr1ps/invchain_skewp_tr1ps.ibs"),
    "inv_weak":   ("inv_chain", 1.8, INV / "weak/selection/tr1ps/invchain_weak_tr1ps.ibs"),
    "ex2_base":     ("ex2", 3.3, EX2 / "base/selection/tr1ps/ex2_base_tr1ps.ibs"),
    "ex2_slowpre":  ("ex2", 3.3, EX2 / "slowpre/selection/tr1ps/ex2_slowpre_tr1ps.ibs"),
    "ex2_skewp":    ("ex2", 3.3, EX2 / "skewp/selection/tr1ps/ex2_skewp_tr1ps.ibs"),
    "ex2_weak":     ("ex2", 3.3, EX2 / "weak/selection/tr1ps/ex2_weak_tr1ps.ibs"),
    "ex2_nomiller": ("ex2", 3.3, EX2 / "nomiller/selection/tr1ps/ex2_nomiller_tr1ps.ibs"),
}
BASE = {
    "io_buf": ("io_buf", 3.3, R / "io_buf_fast_edge_regen_2026-08-19/source/io_buf_fast_50ps.ibs"),
    "inv_chain": ("inv_chain", 1.8, R / "stress_method_matrix_2026-08-20/pad_match/hspice_references"
                  "/inv_chain/fast_5ps/r50_c2pf/short_high_w104ps_104ps/native/input.ibs"),
    "ex2": ("ex2", 3.3, R / "stress_method_matrix_2026-08-20/pad_match/hspice_references"
            "/ex2/fast_5ps/r50_c2pf/short_high_w810ps_810ps/native/input.ibs"),
}


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #

def ibis_names(ibis: Path) -> tuple[str, str]:
    text = ibis.read_text(encoding="utf-8", errors="ignore")
    comp = re.search(r"^\[Component\]\s+(.+?)\s*$", text, re.M).group(1)
    model = re.search(r"^\[Model\]\s+(\S+)", text, re.M).group(1)
    return model, comp


def ibis_ccomp(ibis: Path) -> float:
    m = re.search(r"^C_comp\s+([0-9.]+)\s*([pfn]?)F", ibis.read_text(errors="ignore"), re.M | re.I)
    return float(m.group(1)) * {"p": 1.0, "f": 1e-3, "n": 1e3, "": 1e12}[m.group(2).lower()]


def pwl_width(sp: Path) -> float:
    m = re.search(r"PWL\(([^)]*)\)", sp.read_text(errors="ignore"), re.S)
    nums = re.findall(r"([0-9.]+)n\s+[0-9.]+", m.group(1))
    return float(nums[3]) - RISE_NS


def tr0_pad(path: Path) -> tuple[np.ndarray, np.ndarray]:
    raw = sl.parse_hspice_tr0(path)
    key = next(k for k in raw if "pad" in k)
    return np.asarray(raw["time"], float) * 1e9, np.asarray(raw[key], float)


def fixture(path: Path) -> np.ndarray:
    raw = sl.parse_hspice_tr0(path)
    t = np.asarray(raw["time"], float)
    v = np.asarray(raw[next(k for k in raw if "pad" in k)], float)
    return np.column_stack([t, v, v, v])


def delays(sub: Path | None) -> dict[str, float]:
    """The four command delays and the two gate time constants, ns.

    The gate state is an RC toward its commanded target with separate rise and
    fall constants:  BGUP GUP 0 I = -{c} * (target - GUP) / (rising ? tau_r : tau_f)
    """
    out = {k: float("nan") for k in ("pu_on", "pu_off", "pd_off", "pd_on",
                                     "tau_rise", "tau_fall")}
    if sub is None or not sub.exists():
        return out
    text = sub.read_text(errors="ignore")
    for tag, key in (("TPUONP", "pu_on"), ("TPUOFFP", "pu_off"),
                     ("TPDOFFP", "pd_off"), ("TPDONP", "pd_on")):
        m = re.search(rf"^{tag}\s.*?Td=([0-9.e+-]+)n", text, re.M)
        if m:
            out[key] = float(m.group(1))
    m = re.search(r"^BGUP GUP 0 I = .*?\?\s*([0-9.e+-]+)n\s*:\s*([0-9.e+-]+)n", text, re.M)
    if m:
        out["tau_rise"], out["tau_fall"] = float(m.group(1)), float(m.group(2))
    return out


@dataclass
class Case:
    source: str
    family: str
    variant: str
    depth: int
    width_ns: float
    supply: float
    ibis: Path
    transistor: tuple
    fixtures: tuple
    models: dict
    delays: dict


def variant_cases() -> list[Case]:
    cases: list[Case] = []
    for name, (fam, sup, ibis) in VARIANTS.items():
        for d in sorted((VAR / name).glob("depth*_w*ps"), key=lambda p: p.stat().st_mtime):
            need = [d / "transistor/run.tr0", d / "native/run.tr0", d / "delay_cmd/run.raw",
                    d / "fixture_0/run.tr0", d / "fixture_vcc/run.tr0"]
            if not all(p.exists() for p in need):
                continue
            depth = int(re.match(r"depth(\d+)_", d.name).group(1))
            cases = [c for c in cases if not (c.variant == name and c.depth == depth)]
            nat = sl.parse_hspice_tr0(d / "native/run.tr0")
            models = {"native": (sl.time_ns(nat), sl.trace(nat, "pad"),
                                 sl.trace(nat, "ku"), sl.trace(nat, "kd"))}
            for b in ("delay_cmd", "gate_state"):
                if (d / b / "run.raw").exists():
                    raw = sl.parse_ngspice_raw(d / b / "run.raw")
                    models[b] = (sl.time_ns(raw), sl.trace(raw, "out"),
                                 sl.signal(raw, "v(x1.ku)"), sl.signal(raw, "v(x1.kd)"))
            cases.append(Case("variant", fam, name, depth, pwl_width(d / "transistor/run.sp"),
                              sup, ibis, tr0_pad(d / "transistor/run.tr0"),
                              (fixture(d / "fixture_0/run.tr0"), fixture(d / "fixture_vcc/run.tr0")),
                              models, delays(d / "delay_cmd/driver.sub")))
    return cases


def matrix_cases() -> list[Case]:
    cases = []
    for dev, (fam, sup, ibis) in BASE.items():
        sub = next(iter((MATRIX / "generated_models" / dev).glob("*.sub")), None)
        for csvp in sorted((MATRIX / "waveforms").glob(f"{dev}_short_high_w*ps.csv")):
            w = int(re.search(r"_w(\d+)ps", csvp.stem).group(1))
            fx = MATRIX / "hspice_fixtures" / dev / f"short_high_w{w}ps"
            if not (fx / "vfix_0/run.tr0").exists():
                continue
            ref = read(csvp)
            t = ref["time_ns"]
            models = {"native": (t, ref["hspice_pad"], ref["hspice_ku"], ref["hspice_kd"]),
                      "delay_cmd": (t, ref["pybis_pad"], ref["pybis_ku"], ref["pybis_kd"])}
            depth = int(round(100 * float(np.max(ref["silicon_pad"])) / PLATEAU[fam]))
            cases.append(Case("matrix", fam, dev, depth, w / 1000.0, sup, ibis,
                              (t, ref["silicon_pad"]),
                              (fixture(fx / "vfix_0/run.tr0"), fixture(fx / "vfix_vcc/run.tr0")),
                              models, delays(sub)))
    return cases


# --------------------------------------------------------------------------- #
# Measurements
# --------------------------------------------------------------------------- #

def first_cross(t, y, level, after, rising, until=None):
    """First time after `after` that y crosses `level` in the given direction."""
    m = t > after
    if until is not None:
        m &= t < until
    tt, yy = t[m], y[m]
    idx = np.where(yy > level)[0] if rising else np.where(yy < level)[0]
    return float(tt[idx[0]]) if len(idx) else float("nan")


def peak_in(t, y, lo, hi):
    g = np.arange(lo, hi, 0.001)
    v = np.interp(g, t, y)
    i = int(np.argmax(v))
    return float(g[i]), float(v[i])


def true_bump(t, y, tpk, pk):
    """(amplitude_V, time_ns) of a genuine secondary maximum, else (nan, nan)."""
    g = np.arange(tpk, 21.5, 0.001)
    v = np.interp(g, t, y)
    coll = np.where(v < 0.05 * pk)[0]
    if not len(coll):
        return float("nan"), float("nan")
    tc = g[coll[0]]
    m = g > tc
    imin = int(np.argmin(v[m]))
    after = m.copy()
    after[np.where(m)[0][:imin]] = False
    imax = int(np.argmax(v[after]))
    amp = float(v[after][imax])
    if amp - float(v[m][imin]) < 0.005:
        return float("nan"), float("nan")
    return amp, float(g[after][imax])


def measure(c: Case, data) -> tuple[dict, list[dict]]:
    t_si, pad_si = c.transistor
    rev = RISE_NS + c.width_ns
    tpk, pk = peak_in(t_si, pad_si, rev - 0.1, rev + 3.0)

    sols = {}
    for ups in (2.0, 5.0, 10.0):
        s = solve_silicon_kukd(data, c.fixtures[0], c.fixtures[1], c.supply, uniform_ps=ups)
        sols[ups] = (s[:, 0] * 1e9, s[:, 1], s[:, 2], s[:, 3])
    ts, ku_si, kd_si, cond = sols[5.0]

    # The event window, from the transistor's own coefficients.
    t_on = first_cross(ts, ku_si, 0.10, rev - 0.15, rising=True, until=tpk)
    if np.isnan(t_on):
        t_on = rev
    si_ku_pk = peak_in(ts, ku_si, t_on, tpk + 0.30)
    t_off = first_cross(ts, kd_si, 0.90, si_ku_pk[0], rising=True, until=tpk + 3.0)
    if np.isnan(t_off):
        t_off = tpk + 0.6
    win = np.arange(t_on, t_off, 0.002)
    si_u, si_d = np.interp(win, ts, ku_si), np.interp(win, ts, kd_si)
    spread = float(np.mean(np.std([np.interp(win, s[0], s[1]) for s in sols.values()], axis=0)))
    ok = si_u > 0.10

    si_off50 = first_cross(ts, ku_si, 0.5, si_ku_pk[0], rising=False, until=t_off + 0.5)
    si_on50 = first_cross(ts, kd_si, 0.5, si_ku_pk[0], rising=True, until=t_off + 0.5)
    # The Kd-residual window must clear the differentiation-noise zone, which sits
    # within ~90 ps of the reversal (`silicon_kukd_conditioning_2026-09-07`). On
    # io_buf the pad peak is only ~100 ps after the reversal, so tpk-0.1 would
    # reach back into it.
    kd_lo = max(tpk - 0.1, rev + 0.09)
    kd_win = (ts > kd_lo) & (ts < t_off)
    # How saturated can our gate be when the reversal takes effect? The pull-up is
    # commanded on for (W - |pu_on - pu_off|) and rises with tau_rise, so this is
    # the number of time constants it gets. >~3 means GUP ~ 1 regardless of W.
    commanded = c.width_ns - abs(c.delays["pu_on"] - c.delays["pu_off"])
    sat_ratio = commanded / c.delays["tau_rise"] if c.delays["tau_rise"] > 0 else np.nan
    si_bump = true_bump(t_si, pad_si, tpk, pk)

    lo, hi = outward_window(t_si, pad_si, RISE_NS)
    g = np.arange(lo, hi, 0.002)
    si_pad_g = np.interp(g, t_si, pad_si)

    scalars = dict(source=c.source, family=c.family, variant=c.variant, depth=c.depth,
                   width_ps=round(c.width_ns * 1e3, 1), supply=c.supply,
                   c_comp_pF=round(ibis_ccomp(c.ibis), 3),
                   rev_ns=round(rev, 4), tpk_after_rev_ps=round((tpk - rev) * 1e3, 1),
                   t_on_after_rev_ps=round((t_on - rev) * 1e3, 1),
                   event_len_ps=round((t_off - t_on) * 1e3, 1),
                   si_peak_V=round(pk, 4),
                   si_ku_at_tpk=round(float(np.interp(tpk, ts, ku_si)), 4),
                   si_ku_peak=round(si_ku_pk[1], 4),
                   si_ku_peak_after_rev_ps=round((si_ku_pk[0] - rev) * 1e3, 1),
                   si_ku_off50_after_rev_ps=round((si_off50 - rev) * 1e3, 1),
                   si_kd_on50_after_rev_ps=round((si_on50 - rev) * 1e3, 1),
                   si_kd_min=round(float(kd_si[kd_win].min()), 4) if kd_win.any() else np.nan,
                   si_bump_mV=round(si_bump[0] * 1e3, 1),
                   si_bump_after_rev_ps=round((si_bump[1] - rev) * 1e3, 1),
                   grid_spread=round(spread, 4), cond_max=round(float(np.nanmax(cond)), 2),
                   **{k: round(v * 1e3, 1) for k, v in c.delays.items()},
                   slice_ps=round(abs(c.delays["pu_on"] - c.delays["pu_off"]) * 1e3, 1),
                   commanded_ps=round(commanded * 1e3, 1),
                   sat_ratio=round(sat_ratio, 2))

    nat_t, nat_pad = c.models["native"][:2]
    # Native is dead on the tr1ps variant IBIS files for ex2 and inv_stage4: its
    # Ku never rises and its Kd never leaves 1. Score it only where it lives.
    nat_ku = np.interp(np.arange(rev, tpk + 0.5, 0.002), c.models["native"][0], c.models["native"][2])
    nat_kd = np.interp(np.arange(tpk - 0.1, t_off, 0.002), c.models["native"][0], c.models["native"][3])
    # inv_stage4 d80/d85 pass the coefficient test with a pad that never rises, so
    # the pad itself is the deciding criterion.
    nat_pk = peak_in(c.models["native"][0], c.models["native"][1], rev - 0.1, rev + 3.0)[1]
    nat_valid = bool(nat_ku.max() > 0.3 and nat_kd.min() < 0.9 and nat_pk > 0.3 * pk)
    scalars["native_valid"] = int(nat_valid)
    nat_pad_g = np.interp(g, nat_t, nat_pad)

    rows = []
    for name, (tm, pad, ku, kd) in c.models.items():
        mu, md = np.interp(win, tm, ku), np.interp(win, tm, kd)
        m_pk = peak_in(tm, pad, rev - 0.1, rev + 3.0)
        ku_pk = peak_in(tm, ku, t_on - 0.05, tpk + 0.30)
        m_off50 = first_cross(tm, ku, 0.5, ku_pk[0], rising=False, until=t_off + 0.8)
        m_on50 = first_cross(tm, kd, 0.5, ku_pk[0], rising=True, until=t_off + 0.8)
        mwin = (tm > kd_lo) & (tm < t_off)
        pad_g = np.interp(g, tm, pad)
        lag_si, res_si = best_lag(g, si_pad_g, pad_g, lo, hi)
        lag_nat, res_nat = (best_lag(g, nat_pad_g, pad_g, lo, hi)
                            if (name != "native" and nat_valid) else (np.nan, np.nan))
        b = true_bump(tm, pad, tpk, pk)
        rows.append(dict(
            variant=c.variant, depth=c.depth, family=c.family, model=name,
            valid=int(nat_valid) if name == "native" else 1,
            ku_ratio=round(float(np.median(mu[ok] / si_u[ok])), 3) if ok.sum() > 5 else np.nan,
            ku_rms=round(float(np.sqrt(np.mean((mu - si_u) ** 2))), 4),
            kd_rms=round(float(np.sqrt(np.mean((md - si_d) ** 2))), 4),
            ku_at_tpk=round(float(np.interp(tpk, tm, ku)), 4),
            ku_entry_excess=round(float(np.interp(tpk, tm, ku)) - scalars["si_ku_at_tpk"], 4),
            ku_peak=round(ku_pk[1], 4),
            ku_peak_shift_ps=round((ku_pk[0] - (si_ku_pk[0])) * 1e3, 1),
            ku_off50_late_ps=round((m_off50 - si_off50) * 1e3, 1),
            kd_on50_late_ps=round((m_on50 - si_on50) * 1e3, 1),
            kd_min=round(float(kd[mwin].min()), 4) if mwin.any() else np.nan,
            pad_peak_err_mV=round((m_pk[1] - pk) * 1e3, 1),
            pad_peak_err_pct=round(100 * (m_pk[1] - pk) / pk, 1),
            pad_peak_shift_ps=round((m_pk[0] - tpk) * 1e3, 1),
            lag_vs_si_ps=round(lag_si, 1), lag_res_si=round(res_si, 3),
            lag_vs_native_ps=round(lag_nat, 1) if not np.isnan(lag_nat) else np.nan,
            bump_mV=round(b[0] * 1e3, 1),
            bump_after_rev_ps=round((b[1] - rev) * 1e3, 1)))
    return scalars, rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = variant_cases() + matrix_cases()
    print(f"  {len(cases)} short-high cases")
    scal, rows, failed = [], [], []
    dm_cache: dict[Path, object] = {}
    for c in cases:
        try:
            if c.ibis not in dm_cache:
                model, comp = ibis_names(c.ibis)
                dm_cache[c.ibis] = pb.DataModel(pb.get_ibis_model_ecdtools(str(c.ibis)),
                                                model_name=model, component_name=comp)
            s, r = measure(c, dm_cache[c.ibis])
            scal.append(s)
            rows.extend(r)
            dc = next(x for x in r if x["model"] == "delay_cmd")
            print(f"    {c.variant:<13}d{c.depth:<4}W={c.width_ns*1e3:6.1f}  event {s['t_on_after_rev_ps']:5.0f}"
                  f"..{s['t_on_after_rev_ps']+s['event_len_ps']:5.0f}ps  spread {s['grid_spread']:.4f}"
                  f"  nat_ok={s['native_valid']}  dc: Ku{dc['ku_ratio']:.2f} off+{dc['ku_off50_late_ps']:.0f}"
                  f" on+{dc['kd_on50_late_ps']:.0f} pk{dc['pad_peak_err_pct']:+.0f}% lag{dc['lag_vs_si_ps']:+.0f}")
        except Exception as exc:                        # noqa: BLE001
            failed.append((c.variant, c.depth, repr(exc)[:160]))
            print(f"    {c.variant} d{c.depth}: FAILED {exc!r}"[:170])
    with (OUT / "cases.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(scal[0].keys()))
        w.writeheader()
        w.writerows(scal)
    with (OUT / "metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (OUT / "failed.txt").write_text("\n".join(map(str, failed)), encoding="utf-8")
    print(f"\n  wrote {len(scal)} cases, {len(rows)} rows, {len(failed)} failed -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
