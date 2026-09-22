# Does the timing shift grow under stress? Yes — on all nine variants

*2026-09-04* · `scripts/variant_stress_depth_sweep.py`

## The question

Full-swing work on the three base buffers found 75–95% of pybis's timing offset
was already present without any truncation, which suggested stress adds little.
That was measured on the base buffers and *assumed* for the variants. This sweep
tests it: nine buffer variants × four pulse widths each, against the HSPICE
transistor as ground truth.

The design, stated before the runs: *if the shift is roughly constant with depth,
what full swing already carries is the whole of it and stress adds nothing; if it
grows as depth falls, stress genuinely contributes.*

## The answer

**It grows, on 9 of 9 variants**, and the direction is the same everywhere: at
full swing pybis crosses *early*, and truncation pushes it *late*.

| variant | shallowest | full swing | change | mean \|shift\| gate_state | delay_cmd |
|---|---|---|---|---|---|
| inv_base8 | +12.9 ps | −0.1 ps | **+13.0** | 4.9 ps | 9.2 ps |
| inv_stage4 | +6.3 | −1.3 | +7.7 | 3.7 | 6.2 |
| inv_skewp | +5.4 | −1.1 | +6.4 | 2.5 | 3.1 |
| inv_weak | +1.1 | −11.5 | +12.6 | 6.9 | 3.3 |
| ex2_base | +16.0 | −21.8 | **+37.8** | 12.8 | 16.7 |
| ex2_slowpre | +22.1 | −24.6 | +46.7 | 20.8 | 18.1 |
| ex2_skewp | −7.3 | −50.3 | +43.0 | 38.3 | 25.4 |
| ex2_weak | −37.5 | −68.7 | +31.2 | 51.6 | 40.1 |
| ex2_nomiller | +2.9 | −26.6 | +29.5 | 19.6 | 18.3 |

Growth is **family-dependent and about 4× larger on ex2**: inv_chain averages
+9.9 ps (range 6.4–13.0), ex2 averages +37.6 ps (range 29.5–46.7). Within each
family it is tight, so this is a property of the buffer family, not of the
individual variant.

The full-swing offset and the stress-induced shift **have opposite signs and
partly cancel**. Quoting either alone overstates how well the model tracks.

### Method note — why depth < 30% is excluded

On the shallowest ex2 points the models make a transition several times larger
than the transistor's (ex2_base at 11%: transistor 0.160 V, gate_state 1.187 V).
No crossing-based metric separates timing from amplitude there, so those rows are
reported in the CSV but excluded from the summary above. Each trace is timed at
50% of *its own* excursion; a level fixed to the transistor's would report an
amplitude error as a timing one.

## delay_cmd is the more robust build, not the more accurate one

`delay_cmd` beats `gate_state` on 5 of 9 variants — and they are the five with the
largest shifts (ex2_skewp, ex2_weak, ex2_slowpre, ex2_nomiller, inv_weak). On the
four easy variants `gate_state` wins. Means: 15.4 ps vs 17.9 ps.

So the level-driven command does not simply improve timing; it **compresses the
spread**, giving up a little on well-behaved buffers to avoid the large errors on
badly-behaved ones. That is consistent with its known role of removing the
stranded charge rather than retuning the edge.

## Native IBIS: read the two columns together

`native_excursion_v` is HSPICE's default two-waveform mode; `native_rwf1_*` is
single-waveform. They disagree sharply — see
[docs/native_vt_waveform_modes.md](../../docs/native_vt_waveform_modes.md).

* **inv_chain** shows a clean depth crossover: single-waveform is more accurate
  below ~85% depth, two-waveform above it. Consistent across all four variants.
* **ex2** does not. Two-waveform is dead (~0.03 V) at *every* depth on base,
  slowpre and nomiller. Single-waveform rescues those three — but on ex2_skewp and
  ex2_weak **both modes collapse** below full swing, single-waveform to ~0.001 V.

Those two are exactly the variants with the highest coefficients the s2ibispy
selector reported: skewp max|Ku| 1.589–1.714, weak 1.779–1.829, against
1.283–1.343 for base/nomiller and a clean pass for slowpre. So `max|Ku|` predicts
whether the **single-waveform** mode survives truncation — it does not predict the
two-waveform failure, which hits all five ex2 variants regardless.

Ill-conditioning of the Ku/Kd solve was proposed as the common mechanism and has
been **measured and ruled out** (`scripts/two_fixture_conditioning.py`): ex2 is
conditioned better than inv_chain, which does not fail.

## Caveats

* The ex2 variants use models the selector formally rejected under the 1.25 cap.
  They are the only ex2 models available; treat ex2 absolute numbers as indicative
  and the inv_chain family as the clean comparison.
* Native is not a usable yardstick on ex2 in either mode. All conclusions above are
  against the transistor.
