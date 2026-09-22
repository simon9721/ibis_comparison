# Overnight Vector-Fit Campaign Analysis

Study folder: `results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18`

## Scope

- Inventory: 227 Touchstone records discovered.
- Focused overnight channels: 9 requested channels.
- Candidate grid: 15 vector-fit settings x 6 preprocessing modes, plus near-pass passivity-enforced variants.
- Candidate metric rows: 5970.
- Ranked channels: 9.
- Selected vector models: 6.
- ngspice smoke rows: 72.
- HSPICE audit rows: 54.
- RX/TX side overlay PNGs after audit path fix: 108.
- Share-pack files after audit path fix: 738.
- Edge-bandwidth summary plots:
  - `plots/edge_bandwidth/edge_bandwidth_vs_hspice.png`
  - `plots/edge_bandwidth/selected_edge_bandwidth_ratios.png`

## Main Result

The vector-fit path made real progress on some 2-port examples, but it is not ready to be trusted as a general full-model flow yet.

The strongest positive result is `ntwk2` / `ntwk3`: selected or top vector-fit models match HSPICE very well for 50 ps and 500 ps edges, with RX RMSE around 0.14 mV to 0.37 mV for `ntwk3` and around 0.31 mV to 0.36 mV for `ntwk2`. Their 5 ps edges are still timing WARN, not clean PASS.

The strongest negative result is Clarity: vector-fit still fails the 5 ps and 50 ps HSPICE RX shape audit. It only passes at 500 ps. This confirms that a good frequency fit and passivity check are not sufficient for fast-edge transient trust.

The `.s4p` Cisco full vector-fit path did not produce any selected full model in this run. The reduced RX baseline remains useful for RX voltage shape on two Cisco channels, but full vector fit failed the fit gates.

## New Independent Predictor: Edge Bandwidth

A new HSPICE-independent edge-bandwidth rule was added after this run:

`required bandwidth = 0.35 / edge_time`

With the default thresholds, a channel is edge-bandwidth `PASS` when `Touchstone fmax / required bandwidth >= 1`, `WARN` when the ratio is between `0.25` and `1`, and `FAIL` below `0.25`.

This predictor explains the current HSPICE pattern very clearly:

- 5 ps needs about 70 GHz. All audited 5 ps rows are bandwidth FAIL and HSPICE produced 0 PASS, 12 WARN, 6 FAIL.
- 50 ps needs about 7 GHz. The 10 GHz `ntwk2` / `ntwk3` cases are bandwidth PASS and HSPICE PASS; the 2 GHz Clarity cases are bandwidth WARN and HSPICE FAIL.
- 500 ps needs about 0.7 GHz. All audited rows are bandwidth PASS and HSPICE PASS.

This is not a per-channel tuning rule. It is a general signal-integrity sanity check that says whether the source Touchstone has enough measured bandwidth for the edge rate we are trying to claim.

After applying this edge-bandwidth gate to the independent classification, the adjusted independent PASS rows correlate cleanly in this dataset:

- All adjusted independent PASS rows: HSPICE P/W/F/E = 20/0/0/0, false-pass rate 0.0.
- 50 ps adjusted independent PASS rows: HSPICE P/W/F/E = 8/0/0/0, false-pass rate 0.0.
- 500 ps adjusted independent PASS rows: HSPICE P/W/F/E = 12/0/0/0, false-pass rate 0.0.

This does not prove production readiness yet because the dataset is still small, but it is a strong next-step result: the new independent gate explains the observed HSPICE failures and removes the false clean-PASS cases in the current audit.

## Selected Models

| Channel | Selected candidate | Final view class | HSPICE selected audit |
|---|---|---:|---:|
| `Clarity_example_acf20e4a` | `raw_vector_3r3c_lin` | WARN | 1 PASS, 2 FAIL |
| `Clarity_example_Fitted_55b55a71` | `raw_auto_fit_default` | WARN | 1 PASS, 2 FAIL |
| `ntwk2_e1c16499` | `raw_vector_12r12c_lin_enforced_s2000_original_pdc1` | WARN | 2 PASS, 1 WARN |
| `ntwk2_24638a5f` | `raw_vector_12r12c_lin_enforced_s2000_original_pdc1` | WARN | 2 PASS, 1 WARN |
| `ntwk3_ad74ab42` | `raw_auto_fit_high_order` | FAIL | 2 PASS, 1 WARN |
| `ntwk3_8f8a2430` | `raw_auto_fit_high_order` | FAIL | 2 PASS, 1 WARN |
| `Ch10_35_5F3N_f4_fc94db99` | none | FAIL | not audited, no selected vector model |
| `Ch10_35_5F3N_t_d3c7dddc` | none | FAIL | not audited, no selected vector model |
| `Ch3_17_5F3N_f3_c08ef229` | none | FAIL | not audited, no selected vector model |

## HSPICE Correlation Patterns

Selected model audit rows only:

- 5 ps edge: 4 WARN, 2 FAIL.
- 50 ps edge: 4 PASS, 2 FAIL.
- 500 ps edge: 6 PASS.

Selected model representative RX RMSE:

- Clarity original:
  - 5 ps: 23.282 mV, FAIL.
  - 50 ps: 12.044 mV, FAIL.
  - 500 ps: 4.734 mV, PASS.
- Clarity fitted:
  - 5 ps: 17.785 mV, FAIL.
  - 50 ps: 21.376 mV, FAIL.
  - 500 ps: 2.205 mV, PASS.
- `ntwk2`:
  - 5 ps: 1.353 mV, WARN because timing confidence is low.
  - 50 ps: 0.359 mV, PASS.
  - 500 ps: 0.310 mV, PASS.
- `ntwk3`:
  - 5 ps: 0.993 mV, WARN because timing confidence is low.
  - 50 ps: 0.368 mV, PASS.
  - 500 ps: 0.140 mV, PASS.

## Independent Metric Calibration

The selected models were deliberately conservative: no selected model reached clean full/RX/reflection PASS after ngspice smoke. They are WARN or FAIL.

However, top-K audited candidates included independent PASS rows. After fixing the ngspice audit include path issue, independent PASS correlated as:

- PASS by HSPICE: 20 rows.
- WARN by HSPICE: 8 rows.
- FAIL by HSPICE: 8 rows.
- ERROR by HSPICE/ngspice correlation: 0 rows.
- Effective false-pass-to-clean-PASS risk: 16 / 36 = 44.4% if WARN/FAIL are considered not good enough.

This means the independent PASS threshold is still too loose for promotion. The main missing behavior is fast-edge timing/shape trust, especially at 5 ps.

## Candidate And Preprocessing Findings

- Raw preprocessing dominates selected models.
- `dc_hold`, frequency trimming, `hf_hold`, and `hf_rolloff_20db_dec` did not produce selected models in this run.
- Best observed selected candidate families:
  - `vector_12r12c` raw linear with passivity enforcement for `ntwk2`.
  - `auto_fit_high_order` raw for `ntwk3`.
  - `vector_3r3c` raw linear for Clarity original.
  - `auto_fit_default` raw for Clarity fitted.
- Complex-dominant `vector_2r6c` produced no PASS/WARN rows in this run.
- Passivity enforcement helped some `ntwk2` selections, but also created long candidate paths and audit include failures for some Clarity variants.

## Tooling Issue Fixed

The first audit pass had some rows marked `ERROR`, but the root issue was not HSPICE. HSPICE ran and produced `.tr0`/`.lis`; the paired ngspice audit deck failed to include generated `.sp` files whose paths exceeded common Windows path limits.

Example path length: 266 characters.

Fix applied: the vector-fit audit now copies the candidate `.sp` file into the local ngspice audit directory as `model.sp` before generating the ngspice deck. The audit was rerun and now has 54/54 rows with `correlation_status=ok` and zero `ERROR` rows.

## Practical Conclusion

Vector fitting is promising for some 2-port, slower/cleaner transient cases, especially `ntwk2` and `ntwk3`. It is not yet production-ready as a general full-model S-parameter-to-ngspice flow.

The reduced RX-through method is still better for Cisco RX-shape work today. Full vector-fit `.s4p` conversion needs more work before it can replace that reduced RX path.

The next campaign should focus on:

1. Tightening independent PASS rules so fast-edge WARN/FAIL cannot be called clean PASS.
2. Adding an independent fast-edge transient score that catches the Clarity false-pass candidates.
3. Expanding `.s4p` vector-fit experiments with shorter model IDs and possibly staged fits.
4. Comparing selected vector-fit models against the reduced RX baseline channel by channel.
5. Promoting only settings that keep holdout false PASS below the target threshold.
