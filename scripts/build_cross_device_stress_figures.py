#!/usr/bin/env python3
"""Cross-device stress trends, from `cross_device_stress_2026-09-08`.

Reads cases.csv / metrics.csv and draws the five relationships the analysis
rests on. Twelve buffers: nine variants at five depths, three base buffers from
the stress matrix. `delay_cmd` is ours; native is drawn only where it is alive.

    py -3.14 scripts/build_cross_device_stress_figures.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
OUT = ROOT / "results" / "cross_device_stress_2026-09-08"
FIGS = ROOT / "results" / "meeting_deck_2026-09-04" / "figures"

ORDER = ["inv_base8", "inv_stage4", "inv_skewp", "inv_weak", "inv_chain",
         "ex2_base", "ex2_slowpre", "ex2_skewp", "ex2_weak", "ex2_nomiller", "ex2",
         "io_buf"]
FAMILY = {"inv": "#2E8B57", "ex2": "#B03060", "io_": "#111111"}
MARK = {"inv_base8": "o", "inv_stage4": "s", "inv_skewp": "^", "inv_weak": "v", "inv_chain": "D",
        "ex2_base": "o", "ex2_slowpre": "s", "ex2_skewp": "^", "ex2_weak": "v", "ex2_nomiller": "P",
        "ex2": "D", "io_buf": "*"}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def colour(v):
    return FAMILY[v[:3]]


def main() -> int:
    cases = {(c["variant"], int(c["depth"])): c for c in csv.DictReader(open(OUT / "cases.csv"))}
    met = {}
    for r in csv.DictReader(open(OUT / "metrics.csv")):
        met.setdefault((r["variant"], int(r["depth"])), {})[r["model"]] = r

    def series(v, model, key, table="metrics", valid_only=True):
        ks = sorted([k for k in cases if k[0] == v], key=lambda k: k[1])
        xs, ys = [], []
        for k in ks:
            if table == "metrics":
                row = met[k].get(model)
                if row is None or (valid_only and int(row["valid"]) != 1):
                    continue
                ys.append(f(row[key]))
            else:
                ys.append(f(cases[k][key]))
            xs.append(k[1])
        return np.array(xs, float), np.array(ys, float)

    fig, axes = plt.subplots(2, 3, figsize=(19, 11))
    ax = axes.ravel()

    # 1. pad peak excess vs depth
    a = ax[0]
    for v in ORDER:
        x, y = series(v, "delay_cmd", "pad_peak_err_pct")
        lw = 3.2 if v == "io_buf" else 1.8
        a.plot(x, y, marker=MARK[v], color=colour(v), lw=lw, ms=7, label=v)
        xn, yn = series(v, "native", "pad_peak_err_pct")
        if len(xn) >= 3:
            a.plot(xn, yn, ls=":", color=colour(v), lw=1.2, alpha=0.8)
    a.axhline(0, color="#111", lw=0.8)
    a.set_xlabel("depth  (% of full-swing excursion the transistor reached)")
    a.set_ylabel("our pad peak  minus  transistor's  (%)")
    a.set_title("Stressed peak: ours grows too tall on every buffer but io_buf\n"
                "(dotted = native, where alive)", fontweight="bold")
    a.invert_xaxis()
    a.grid(alpha=0.3)
    a.legend(fontsize=8, ncol=2)

    # 2. entry excess vs peak excess
    a = ax[1]
    allx, ally = [], []
    for v in ORDER:
        _, y = series(v, "delay_cmd", "pad_peak_err_pct")
        _, x = series(v, "delay_cmd", "ku_entry_excess")
        a.scatter(x, y, marker=MARK[v], color=colour(v), s=70 if v != "io_buf" else 160,
                  label=v, edgecolor="white", lw=0.6)
        allx += list(x)
        ally += list(y)
    allx, ally = np.array(allx), np.array(ally)
    ok = ~np.isnan(allx) & ~np.isnan(ally)
    r = np.corrcoef(allx[ok], ally[ok])[0, 1]
    c = np.polyfit(allx[ok], ally[ok], 1)
    xx = np.linspace(-0.2, 1.1, 50)
    a.plot(xx, np.polyval(c, xx), color="#8A8A8A", lw=1.5, ls="--")
    a.axhline(0, color="#111", lw=0.8)
    a.axvline(0, color="#111", lw=0.8)
    a.set_xlabel("Ku entry excess:  our Ku at the transistor's pad peak  minus  transistor's Ku there")
    a.set_ylabel("pad peak excess (%)")
    a.set_title(f"The mechanism: entering the reversal too far on\n"
                f"r = {r:.3f} over {ok.sum()} cases; 0.86-0.98 within every buffer",
                fontweight="bold")
    a.grid(alpha=0.3)

    # 3. normalised turn-off lateness vs depth
    a = ax[2]
    for v in ORDER:
        ks = sorted([k for k in cases if k[0] == v], key=lambda k: k[1])
        x = np.array([k[1] for k in ks], float)
        y = np.array([100 * f(met[k]["delay_cmd"]["ku_off50_late_ps"]) / f(cases[k]["event_len_ps"])
                      for k in ks])
        a.plot(x, y, marker=MARK[v], color=colour(v), lw=3.2 if v == "io_buf" else 1.8, ms=7)
    a.axhline(0, color="#111", lw=0.8)
    a.set_xlabel("depth (%)")
    a.set_ylabel("pull-up turn-off lateness  /  event length  (%)")
    a.set_title("Pull-up turns off late, by a growing fraction of the event\n"
                "(same ordering as the peak excess: one defect, seen twice)", fontweight="bold")
    a.invert_xaxis()
    a.grid(alpha=0.3)

    # 4. transistor Kd residual vs depth, ours flat
    a = ax[3]
    for v in ORDER:
        x, y = series(v, None, "si_kd_min", table="cases")
        a.plot(x, y, marker=MARK[v], color=colour(v), lw=3.2 if v == "io_buf" else 1.8, ms=7)
        _, yo = series(v, "delay_cmd", "kd_min")
        a.plot(x, yo, ls="--", color=colour(v), lw=1.0, alpha=0.7)
    a.axhline(0, color="#111", lw=0.8)
    a.set_xlabel("depth (%)")
    a.set_ylabel("minimum Kd after the reversal  (the falling residual)")
    a.set_title("Transistor's residual shrinks toward zero with stress on 12/12\n"
                "(dashed = ours, calibrated on a complete transition, does not move)",
                fontweight="bold")
    a.invert_xaxis()
    a.grid(alpha=0.3)

    # 5. event geometry
    a = ax[4]
    for v in ORDER:
        ks = [k for k in cases if k[0] == v]
        x = np.mean([f(cases[k]["tau_rise"]) for k in ks])
        y = np.mean([f(cases[k]["tpk_after_rev_ps"]) for k in ks])
        a.scatter([x], [y], marker=MARK[v], color=colour(v), s=200 if v == "io_buf" else 90,
                  edgecolor="white", lw=0.6)
        a.annotate(v, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    a.set_xscale("log")
    a.set_xlabel("our gate rise time constant  tau_rise  (ps, log)")
    a.set_ylabel("transistor pad peak  after the input reversal  (ps)")
    a.set_title("Where each buffer's event sits\n"
                "io_buf: slow gate, peak at the reversal -- the only one in that corner",
                fontweight="bold")
    a.grid(alpha=0.3, which="both")

    # 6. Ku ratio in-event vs depth
    a = ax[5]
    for v in ORDER:
        x, y = series(v, "delay_cmd", "ku_ratio")
        a.plot(x, y, marker=MARK[v], color=colour(v), lw=3.2 if v == "io_buf" else 1.8, ms=7)
        xn, yn = series(v, "native", "ku_ratio")
        if len(xn) >= 3:
            a.plot(xn, yn, ls=":", color=colour(v), lw=1.2, alpha=0.8)
    a.axhline(1, color="#111", lw=0.8)
    a.set_xlabel("depth (%)")
    a.set_ylabel("our Ku / transistor's Ku, median over the event")
    a.set_title("Ku over the event: rises with stress on eleven, falls on io_buf\n"
                "(dotted = native)", fontweight="bold")
    a.invert_xaxis()
    a.grid(alpha=0.3)

    fig.suptitle("Twelve stressed buffers, one instrument: the io_buf findings tested for generality",
                 fontsize=17, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    for p in (OUT / "cross_device_stress.png", FIGS / "cross_device_stress.png"):
        fig.savefig(p, dpi=170)
    plt.close(fig)
    print(f"  {OUT / 'cross_device_stress.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
