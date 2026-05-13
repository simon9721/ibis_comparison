from __future__ import annotations

import math
from pathlib import Path

import run_edge_family_stress_crossflow as base

base.configure_suite(["--suite", "coarse10_context"])
case = base.CASES[0]

pairs = [
    (
        "baseline_pre_kukd",
        Path(
            r"C:\Users\simom\Desktop\IBIS_Comparison\results\ngspice_kukd_ab_context38_2026-05-11\runs\baseline_pre_kukd\ui2_len30cm_loss5_coarse10_ngspice_pybis_baseline_pre_kukd.raw"
        ),
    ),
    (
        "current_kukd",
        Path(
            r"C:\Users\simom\Desktop\IBIS_Comparison\results\ngspice_kukd_ab_context38_2026-05-11\runs\current_kukd\ui2_len30cm_loss5_coarse10_ngspice_pybis_current_kukd.raw"
        ),
    ),
]

for key, raw in pairs:
    flow = base.Flow("ngspice_pybis", "ngspice", key, "ngspice", "#ff7f0e")
    events, summary, _ = base.analyze_output(case, flow, raw)
    rise_summary = [s for s in summary if s["direction"] == "rise"][0]
    r1011 = [
        e
        for e in events
        if e["direction"] == "rise"
        and e["context"] == "10->11"
        and math.isfinite(float(e["output_50_delay_ps"]))
    ]
    delays = [float(e["output_50_delay_ps"]) for e in r1011]
    print(
        key,
        "t_end_ns=", rise_summary["t_end_ns"],
        "completed=", rise_summary["completed"],
        "rise_10to11=", delays,
    )
