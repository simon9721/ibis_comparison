#!/usr/bin/env python3
"""Would indexing the coefficient by pad voltage instead of time actually help?

`native_waveform_count_2026-09-04` found the stress pedestal: our Ku(t) is one
recorded curve played out against a **clock** (time since the input edge), where
native with two V-T tables tracks the transistor's Ku to +13 ps under stress and
ours is +80 ps late. Forcing native onto one table gives it the same +75 ps, so
the defect is the single time-indexed trajectory.

Before building a SPICE model, this asks the cheap question offline: if the same
Ku curve were looked up by **pad voltage** instead of by elapsed time, would it
land closer to the transistor's Ku on a stressed pulse?

How:

1. Take pybis's own `solve_k_params_output` for the rising and falling
   transitions -- Ku(t), Kd(t), exactly what the model ships with.
2. Take the V-T waveform those were solved from, giving V(t) over the same
   time base. Eliminating t between them gives **Ku(V)** and **Kd(V)** -- the
   same coefficients, re-indexed.
3. On a stressed case, evaluate Ku(V) at the pad voltage the model actually
   reaches, choosing the rising or falling branch by which transition is in
   progress.
4. Compare that against the transistor's own Ku, and against what the shipped
   time-indexed model produces.

If the V-indexed version is not closer, there is nothing to build.

    py -3.14 scripts/v_indexed_coefficient_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice",
           ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pybis2spice import pybis2spice as pb  # noqa: E402
from pedestal_localization import best_lag, outward_window, read  # noqa: E402

R = ROOT / "results"
IBIS = R / "io_buf_fast_edge_regen_2026-08-19" / "source" / "io_buf_fast_50ps.ibs"
CASE = (R / "stress_method_matrix_2026-08-20" / "delay_cmd" / "waveforms"
        / "io_buf_short_high_w1792ps.csv")
FIGS = R / "meeting_deck_2026-09-04" / "figures"

MODEL, COMPONENT = "driver", "MCM Driver 1"
RISE_NS, REV_NS = 5.0, 6.792
CORNER = 1


def branch(ibis_data, kind: str):
    """(pad voltage, Ku, Kd) for one transition, sorted by voltage.

    The coefficients come back on the solve's own time base; the V-T waveform
    the solve used supplies the pad voltage on that same base. Pairing them and
    dropping time is the whole re-indexing step.
    """
    k = pb.solve_k_params_output(ibis_data, corner=CORNER, waveform_type=kind)
    t = k[:, 0]
    wave = (ibis_data.vt_rising if kind == "Rising" else ibis_data.vt_falling)[0]
    v = np.interp(t, wave.data[:, 0], wave.data[:, CORNER])
    # A lookup table needs a monotonic index. The recorded transition is
    # monotonic in V apart from overshoot at the very end, so sorting and
    # de-duplicating is enough; ties are averaged rather than dropped.
    order = np.argsort(v)
    v, ku, kd = v[order], k[order, 1], k[order, 2]
    uniq, idx = np.unique(v, return_inverse=True)
    return (uniq,
            np.bincount(idx, ku) / np.bincount(idx),
            np.bincount(idx, kd) / np.bincount(idx))


def replay(data, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pure table replay: the solved Ku(t)/Kd(t) restarted on each input edge.

    This is the other candidate for what native does -- no gate state, no lag, no
    reconstruction, just the solved coefficient played from t=0 at every edge.
    If this lands where native lands, the defect is our gate-state stage rather
    than the time index.
    """
    kr = pb.solve_k_params_output(data, corner=CORNER, waveform_type="Rising")
    kf = pb.solve_k_params_output(data, corner=CORNER, waveform_type="Falling")
    # solve_k_params_output returns its time column in SECONDS while every
    # waveform in this study is in ns. Interpolating ns against seconds runs
    # straight off the end of the table and returns a saturated square wave.
    since = np.where(t < REV_NS, t - RISE_NS, t - REV_NS) * 1e-9
    ku = np.where(t < REV_NS,
                  np.interp(since, kr[:, 0], kr[:, 1]),
                  np.interp(since, kf[:, 0], kf[:, 1]))
    kd = np.where(t < REV_NS,
                  np.interp(since, kr[:, 0], kr[:, 2]),
                  np.interp(since, kf[:, 0], kf[:, 2]))
    return ku, kd


def entry_matched(data, t: np.ndarray, pad: np.ndarray):
    """Enter the trajectory where the pad already is, instead of at its start.

    This is what the PrimeSim manual describes for two V-T waveforms: the pair is
    chosen "according to the initial voltages of VT waveforms and V(out) before a
    buffer's transition". It is an **entry condition**, evaluated once per edge --
    not a continuous re-index, which is why looking Ku up by the instantaneous pad
    voltage destroys the trajectory shape instead of fixing it.

    So: at the reversal, find the point in the recorded transition whose pad
    voltage matches the pad's actual voltage, and play the trajectory from there.
    """
    kr = pb.solve_k_params_output(data, corner=CORNER, waveform_type="Rising")
    kf = pb.solve_k_params_output(data, corner=CORNER, waveform_type="Falling")
    wf = data.vt_falling[0]
    tf, vf = kf[:, 0], np.interp(kf[:, 0], wf.data[:, 0], wf.data[:, CORNER])
    v_rev = float(np.interp(REV_NS, t, pad))
    # vf falls, so invert it on reversed arrays to get "how far in" that voltage is.
    t_star = float(np.interp(v_rev, vf[::-1], tf[::-1]))
    since = np.where(t < REV_NS, (t - RISE_NS) * 1e-9,
                     (t - REV_NS) * 1e-9 + t_star)
    ku = np.where(t < REV_NS, np.interp(since, kr[:, 0], kr[:, 1]),
                  np.interp(since, kf[:, 0], kf[:, 1]))
    kd = np.where(t < REV_NS, np.interp(since, kr[:, 0], kr[:, 2]),
                  np.interp(since, kf[:, 0], kf[:, 2]))
    print(f"  entry: pad is {v_rev:.3f} V at the reversal, which is "
          f"{t_star * 1e9:.3f} ns into the recorded falling transition")
    return ku, kd


def state_matched(data, t: np.ndarray, ku_now: np.ndarray):
    """Enter the reverse trajectory at the point matching our own coefficient.

    The pad-voltage version of this (`entry_matched`) over-advances, because the
    recorded waveform's pad is the pad into the *characterisation fixture* and our
    bench has a different load -- so the same internal state shows up at a
    different voltage. Matching on the coefficient instead is load-independent: at
    the reversal the model has some Ku, and the falling trajectory passes through
    that same Ku at a definite point. Enter there.
    """
    kr = pb.solve_k_params_output(data, corner=CORNER, waveform_type="Rising")
    kf = pb.solve_k_params_output(data, corner=CORNER, waveform_type="Falling")
    ku_rev = float(np.interp(REV_NS, t, ku_now))
    # Ku decays monotonically along the falling trajectory, so invert on the
    # reversed arrays.
    tf, kfu = kf[:, 0], kf[:, 1]
    m = np.argmax(kfu)                      # skip the leading settle transient
    t_star = float(np.interp(ku_rev, kfu[::-1][:len(kfu) - m], tf[::-1][:len(kfu) - m]))
    since = np.where(t < REV_NS, (t - RISE_NS) * 1e-9,
                     (t - REV_NS) * 1e-9 + t_star)
    ku = np.where(t < REV_NS, np.interp(since, kr[:, 0], kr[:, 1]),
                  np.interp(since, kf[:, 0], kf[:, 1]))
    kd = np.where(t < REV_NS, np.interp(since, kr[:, 0], kr[:, 2]),
                  np.interp(since, kf[:, 0], kf[:, 2]))
    print(f"  state entry: Ku is {ku_rev:.3f} at the reversal, matching "
          f"{t_star * 1e9:.3f} ns into the falling trajectory")
    return ku, kd


def main() -> int:
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    v_r, ku_r, kd_r = branch(data, "Rising")
    v_f, ku_f, kd_f = branch(data, "Falling")
    print(f"  rising branch:  V {v_r.min():.3f}..{v_r.max():.3f} V, "
          f"Ku {ku_r.min():+.3f}..{ku_r.max():+.3f}")
    print(f"  falling branch: V {v_f.min():.3f}..{v_f.max():.3f} V, "
          f"Ku {ku_f.min():+.3f}..{ku_f.max():+.3f}")

    d = read(CASE)
    t = d["time_ns"]
    pad = d["pybis_pad"]
    # Rising branch until the input reverses, falling branch after.
    rising = t < REV_NS
    ku_v = np.where(rising, np.interp(pad, v_r, ku_r), np.interp(pad, v_f, ku_f))
    kd_v = np.where(rising, np.interp(pad, v_r, kd_r), np.interp(pad, v_f, kd_f))

    lo, hi = outward_window(t, d["silicon_pad"], RISE_NS)
    grid = np.arange(lo, hi, 0.002)
    truth_ku = np.interp(grid, t, d["silicon_ku"])
    truth_kd = np.interp(grid, t, d["silicon_kd"])

    print("\n  io_buf short high 1792 ps, outward leg, against the "
          "transistor's own coefficients:")
    print(f"    {'build':<34}{'Ku lag':>9}{'Ku rms':>9}"
          f"{'Kd lag':>9}{'Kd rms':>9}")
    for label, ku, kd in (("shipped, indexed by time", d["pybis_ku"], d["pybis_kd"]),
                          ("native, two V-T tables", d["hspice_ku"], d["hspice_kd"]),
                          ("re-indexed by pad voltage", ku_v, kd_v),
                          ("pure table replay, no gate state", *replay(data, t)),
                          ("replay entered at the pad's voltage",
                           *entry_matched(data, t, d["pybis_pad"])),
                          ("replay entered at the matching state",
                           *state_matched(data, t, d["pybis_ku"]))):
        a, ra = best_lag(grid, truth_ku, np.interp(grid, t, ku), lo, hi)
        b, rb = best_lag(grid, truth_kd, np.interp(grid, t, kd), lo, hi)
        print(f"    {label:<34}{a:>9.0f}{ra:>9.2f}{b:>9.0f}{rb:>9.2f}")

    fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.6))
    w = (t > RISE_NS - 0.2) & (t < REV_NS + 1.5)
    for a, key, name in ((ax[0], "ku", "Ku"), (ax[1], "kd", "Kd")):
        a.plot(t[w], d[f"silicon_{key}"][w], color="#111", lw=3.0,
               label="transistor (truth)")
        a.plot(t[w], d[f"hspice_{key}"][w], color="#2B6CA3", lw=2.0,
               label="native, two tables")
        a.plot(t[w], d[f"pybis_{key}"][w], color="#C05621", lw=2.0,
               label="shipped, time-indexed")
        a.plot(t[w], (ku_v if key == "ku" else kd_v)[w], color="#2E8B57",
               lw=2.0, ls="--", label="re-indexed by pad voltage")
        rk, rd = replay(data, t)
        a.plot(t[w], (rk if key == "ku" else rd)[w], color="#7B2CBF",
               lw=2.0, ls=":", label="pure table replay")
        a.axvline(REV_NS, color="#8A8A8A", ls="--", lw=1.4)
        a.set_title(name, loc="left", fontweight="bold")
        a.set_xlabel("Time (ns)")
        a.grid(alpha=0.3)
    ax[0].set_ylabel("coefficient")
    ax[0].legend(fontsize=10)
    fig.suptitle("io_buf | short high | 1792 ps | reading the coefficient off "
                 "the pad instead of the clock", fontsize=15, fontweight="bold")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "v_indexed_coefficient.png", dpi=200)
    plt.close(fig)
    print("\n  v_indexed_coefficient.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
