# ngspice pybis variant provenance

codex_history.md and ngspice_pybis/driver_diff.txt show that another agent changed the canonical ngspice pybis B24-B29 block.

Observed change:

- OLD/canonical: mixed NI/N2 selector, matching the Xyce edge50 selector structure.
- Current ngspice_pybis/driver_OutputInput_Typical.sub: polarity-only N2 selector, with comments saying it removes NI/N2 mixed gating.

That current polarity-only variant may improve one ngspice convergence case, but it is not equivalent to the Xyce edge50 pybis model and therefore should not be used for simulator-to-simulator pybis overlays.

This corrected run uses a syntax translation of Xyce driver_OutputInput_Typical_xyce_relaxed92_edge50_tailflat4p2.sub:

- B-source outer braces adjusted for ngspice syntax.
- Xyce table(...) functions converted to ngspice pwl(...).
- Selector equations and edge50/tailflat4p2 behavior preserved.

Main result: ngspice corrected pybis vs Xyce pybis edge50 RMSE is about 11.7 mV after 20 ns startup; current polarity-only ngspice pybis was about 859 mV RMSE in the prior audit.