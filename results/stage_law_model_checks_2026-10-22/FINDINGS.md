# Two checks on the stage-law model

*2026-10-22.* `scripts/stage_law_model_checks.py`; builds with the
track-1 recipe (`gate_chain_prototype`, step-8 arguments plus `--fix-xlin`), scored at the five widths.

## 1. One rule for x_lin: inv_chain and io_buf rebuilt with x_lin = 0.45

The paper's pad-level result fitted x_lin on these two (0.28 and 0.41) and fixed it at 0.45 elsewhere.
Here every candidate of the two buffers is rebuilt with x_lin = 0.45 and the procedure's selector
(waveform rms at the calibration width) picks one.

| buffer | K | K_d | shape | fit rms (26) | peak at calib. (%) | lag at calib. (ps) | pad rms at calib. (mV) | worst peak, five widths (%) |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| inv_chain | 6 |  | (0.4, 0.6) | 0.0088 | -2.2 | -45 | 108 | 7.4 |
| inv_chain | 6 |  | (0.4, 0.9) | 0.0094 | +2.3 | -27 | 82 | 4.9 |
| inv_chain | 6 |  | (0.5, 0.7) | 0.0087 | -2.9 | -24 | 70 | 6.7 |
| inv_chain | 7 |  | (0.4, 0.6) | 0.0080 | -5.4 | -9 | 20 | 5.8 **selected** |
| inv_chain | 7 |  | (0.4, 0.9) | 0.0081 | +4.1 | +11 | 28 | 6.8 |
| inv_chain | 7 |  | (0.5, 0.7) | 0.0081 | -1.6 | +13 | 39 | 8.4 |
| inv_chain | 8 |  | (0.4, 0.6) | 0.0079 | -1.4 | +26 | 85 | 11.0 |
| inv_chain | 8 |  | (0.4, 0.9) | 0.0076 | -21.1 | +32 | 100 | 21.1 |
| inv_chain | 8 |  | (0.5, 0.7) | 0.0079 | -23.1 | +34 | 105 | 23.1 |
| | | | | | | | **inv_chain: selected 5.8 % with x_lin = 0.45; the paper's result 5.1 % (x_lin fitted, 0.28)** | |
| io_buf | 1 | 3 | (0.4, 0.6) | 0.0245 | -1.1 | -57 | 73 | 1.9 |
| io_buf | 1 | 3 | (0.4, 0.9) | 0.0220 | +0.7 | -41 | 71 | 5.4 |
| io_buf | 1 | 3 | (0.5, 0.7) | 0.0192 | +1.8 | -47 | 63 | 5.6 **selected** |
| | | | | | | | **io_buf: selected 5.6 % with x_lin = 0.45; the paper's result 7.7 % (x_lin fitted, 0.41)** | |

## 2. Sensitivity to x_lin on the selected candidates

| buffer | K | shape | x_lin | peak at calib. (%) | lag at calib. (ps) | pad rms at calib. (mV) | worst peak, five widths (%) | peaks at the five widths (%) |
|---|---:|---|---:|---:|---:|---:|---:|---|
| ex2 | 3 | (0.5, 0.7) | 0.35 | +0.7 | +27 | 44 | 5.5 | -4.6 -5.5 -4.4 -2.5 +0.7 |
| ex2 | 3 | (0.5, 0.7) | 0.55 | -1.1 | -19 | 76 | 10.4 | -8.4 -10.4 -9.3 -6.5 -1.1 |
| inv_chain | 6 | (0.4, 0.9) | 0.35 | +2.3 | -15 | 52 | 2.3 | -1.4 +0.7 +2.3 -1.9 +2.3 |
| inv_chain | 6 | (0.4, 0.9) | 0.55 | +0.7 | -34 | 99 | 7.2 | -3.0 -3.1 -3.8 -7.2 +0.7 |

At x_lin = 0.45 the same candidates score 8.3 % (ex2) and 5.1 % (inv_chain, with x_lin fitted at 0.28)
in the paper's Table VIII; the inv_chain row at 0.45 of check 1 is the like-for-like comparison.
