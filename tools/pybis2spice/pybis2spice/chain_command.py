"""Current-limited-chain command layer for the gate-state model (converter-side, pure text).

The physics (results/current_limited_stages_2026-09-10, gate_chain_prototype_2026-09-10):
the predriver is K identical current-limited stages

    dv/dt = s_up * h(u) * r(1 - v) - s_dn * h(1 - u) * r(v)
    h(x)  = clip((x - vt) / (1 - vt), 0, 1) ** p
    r(x)  = min(1, x / x_lin)

driven by a mid-supply comparator on the input pin; the output gate GUP is the
last stage, GDN = 1 - GUP (one inverter drives both halves); Ku/Kd are static
maps of the gate with a MOSFET-shaped prior

    Ku(g) = ((g - vt_m) / (gs - vt_m)) ** alpha,   clipped to [0, 1]

This module only rewrites a generated `InputDrivenTwoStateGateDelayCommandFull`
subcircuit text; fitting the stage numbers (from the tables' full-swing Ku(t))
and the one-point calibration live in scripts/build_chain_model.py.
"""
from __future__ import annotations

import re

import numpy as np

DEADBAND = 0.005
XLIN_DN_RATIO = 1.0      # discharge-direction resistive fraction = x_lin * ratio


def prior(g, vt, alpha, gs=1.0):
    x = np.clip((np.asarray(g, float) - vt) / (gs - vt), 0.0, 1.0)
    return x ** alpha


def stage_block(K: int, s_up: float, s_dn: float, vt: float, x_lin: float, p: float = 1.0, pre: str = "STG") -> str:
    lines = [f"* --- current-limited command chain {pre}: {K} identical stages ---"]
    for k in range(1, K + 1):
        u = "V(CHIN)" if k == 1 else f"V({pre}{k - 1})"
        v = f"V({pre}{k})"
        hu = f"pow(max(min(({u} - {vt:.6g}) / {1 - vt:.6g}, 1), 0), {p:g})"
        hd = f"pow(max(min((1 - {u} - {vt:.6g}) / {1 - vt:.6g}, 1), 0), {p:g})"
        ru = f"min(1, (1 - {v}) / {x_lin:.6g})"
        rd = f"min(1, {v} / {x_lin * XLIN_DN_RATIO:.6g})"
        lines.append(f"B{pre}{k} {pre}{k} 0 I = -{{gate_c}} * 1e9 * ({s_up:.6g} * {hu} * {ru} - {s_dn:.6g} * {hd} * {rd})")
        lines.append(f"C{pre}{k} {pre}{k} 0 {{gate_c}} ic=0")
        lines.append(f"R{pre}{k} {pre}{k} 0 1e12")
    if pre == "STG":
        lines.append(f"BGUP GUP 0 V = min(max(V(STG{K}), 0), 1)")
    else:
        lines.append(f"BGDN GDN 0 V = 1.0 - min(max(V({pre}{K}), 0), 1)")
    return "\n".join(lines)


def patch_shared_gate(sub: str) -> str:
    """GDN = 1 - GUP, GDNTARGET = 1 - GUPTARGET (single-inverter output stage)."""
    s = re.sub(r"^BGDN GDN 0 I = .*$", "BGDN GDN 0 V = 1.0 - V(GUP)", sub, count=1, flags=re.M)
    for pat in (r"^CGDN GDN 0 .*\n", r"^BGDNBASE GDNBASE 0 .*\n", r"^RGDN GDN GDNBASE .*\n"):
        s = re.sub(pat, "", s, count=1, flags=re.M)
    s = re.sub(r"^BGDNTARGET GDNTARGET 0 V = .*$", "BGDNTARGET GDNTARGET 0 V = 1.0 - V(GUPTARGET)", s, count=1, flags=re.M)
    return s


def patch_chain(sub: str, K: int, prm, sup: float, gdn=None) -> str:
    """Replace the T-line command and the RC gate by the chain. prm = (s_up, s_dn, vt, x_lin, p).
    gdn = (K_d, prm_d) builds a second chain for the pull-down (two predriver paths)."""
    s_up, s_dn, vt, x_lin, p = prm
    chin = f"BCHIN CHIN 0 V = (V(IN,VSS) > {0.5 * sup:.4g}) ? 1.0 : 0.0\n"
    s = re.sub(r"^BGUP GUP 0 I = .*$", chin + stage_block(K, s_up, s_dn, vt, x_lin, p), sub, count=1, flags=re.M)
    s = re.sub(r"^CGUP GUP 0 .*\n", "", s, count=1, flags=re.M)
    s = re.sub(r"^RGUP GUP 0 .*\n", "", s, count=1, flags=re.M)
    tgt = "V(CHIN)" if K == 1 else f"V(STG{K - 1})"
    s = re.sub(r"^BGUPTARGET GUPTARGET 0 V = .*$", f"BGUPTARGET GUPTARGET 0 V = min(max({tgt}, 0), 1)", s, count=1, flags=re.M)
    if gdn is None:
        s = patch_shared_gate(s)
    else:
        Kd, pd = gdn
        s = re.sub(r"^BGDN GDN 0 I = .*$", stage_block(Kd, pd[0], pd[1], pd[2], pd[3], pd[4], pre="STGD"), s, count=1, flags=re.M)
        for pat in (r"^CGDN GDN 0 .*\n", r"^BGDNBASE GDNBASE 0 .*\n", r"^RGDN GDN GDNBASE .*\n"):
            s = re.sub(pat, "", s, count=1, flags=re.M)
        tgd = "V(CHIN)" if Kd == 1 else f"V(STGD{Kd - 1})"
        s = re.sub(r"^BGDNTARGET GDNTARGET 0 V = .*$", f"BGDNTARGET GDNTARGET 0 V = 1.0 - min(max({tgd}, 0), 1)", s, count=1, flags=re.M)
    s = re.sub(r"^BKUGATE_BASE KUGATE_BASE 0 V = .*$",
               f"BKUGATE_BASE KUGATE_BASE 0 V = (V(GUPTARGET) >= V(GUP) - {DEADBAND}) ? V(KUGATE_ON) : V(KUGATE_OFF)", s, count=1, flags=re.M)
    s = re.sub(r"^BKDGATE_BASE KDGATE_BASE 0 V = .*$",
               f"BKDGATE_BASE KDGATE_BASE 0 V = (V(GDNTARGET) >= V(GDN) - {DEADBAND}) ? V(KDGATE_ON) : V(KDGATE_OFF)", s, count=1, flags=re.M)
    if "BSTG1" not in s or "BGUP GUP 0 V" not in s:
        raise RuntimeError("chain_command.patch_chain: gate-state subcircuit structure not found")
    return s


def _pwl(prefix: str, node: str, xs, ys) -> str:
    pairs = ", ".join(f"{x:.6g}, {y:.6g}" for x, y in zip(xs, ys))
    return f"{prefix} pwl(min(max(V({node}), 0), 1), {pairs})"


def patch_prior_maps(sub: str, k_rest: float, k_on: float, d_on: float, d_off: float, prior_fn) -> str:
    """Ku/Kd maps on the last stage from the prior, scaled to the model's own rest/on levels."""
    grid = np.linspace(0.0, 1.0, 200)
    ku = k_rest + (k_on - k_rest) * prior_fn(grid)
    kd = d_off + (d_on - d_off) * prior_fn(grid)
    s = re.sub(r"^BKUGATE_ON KUGATE_ON 0 V = .*$", _pwl("BKUGATE_ON KUGATE_ON 0 V =", "GUP", grid, ku), sub, count=1, flags=re.M)
    s = re.sub(r"^BKUGATE_OFF KUGATE_OFF 0 V = .*$", _pwl("BKUGATE_OFF KUGATE_OFF 0 V =", "GUP", grid, ku), s, count=1, flags=re.M)
    s = re.sub(r"^BKDGATE_ON KDGATE_ON 0 V = .*$", _pwl("BKDGATE_ON KDGATE_ON 0 V =", "GDN", grid, kd), s, count=1, flags=re.M)
    s = re.sub(r"^BKDGATE_OFF KDGATE_OFF 0 V = .*$", _pwl("BKDGATE_OFF KDGATE_OFF 0 V =", "GDN", grid, kd), s, count=1, flags=re.M)
    return s
