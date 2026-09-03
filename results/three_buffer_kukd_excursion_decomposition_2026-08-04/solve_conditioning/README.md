# Ku/Kd Solve Conditioning Audit

This is an offline audit of the exact two-waveform 2x2 current solve used by pybis2spice. No simulation was run.

At each time sample pybis solves:

`[[Ipu1, Ipd1], [Ipu2, Ipd2]] * [Ku, Kd] = [Irequired1, Irequired2]`

The right-hand side includes fixture, clamp, C_comp, and fixture-capacitance currents.

## Result

- Largest extracted excursion: `1.193` for `io_buf/fast_5ps/falling`.
- The solve matrices are not close to singular: median/p95 condition numbers remain roughly 2.3-5.4 across the study, and log-condition/excursion correlation is weak for the worst fast io_buf falling case.
- At the worst fast io_buf falling sample (6 ps), Ku is 2.193, matrix condition is 2.919, capacitive current is 45.7 mA, fixture current is 23.3 mA, and their ratio is 1.96.
- This points to the dynamic right-hand side, especially C_comp*dV/dt from the very sharp waveform, rather than an ill-conditioned 2x2 matrix. The solver needs coefficients outside [0,1] to balance a required current that is not reproduced by a convex combination of the static pullup/pulldown currents.
- inv_chain has tiny p95 capacitive/fixture ratios and only small excursions. ex2 has larger dynamic-current ratios and moderate excursions. The relationship is model and direction dependent, so the CSV retains every sample.

## Files

- `conditioning_samples.csv`
- `conditioning_summary.csv`
- `solve_conditioning_vs_excursion.png`
