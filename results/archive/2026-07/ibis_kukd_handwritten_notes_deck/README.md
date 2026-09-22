# IBIS Ku/Kd Handwritten Notes Deck

This package converts `IBIS kukd .pdf` into a scripted PowerPoint explanation
of the continuous two-state gate model.

## Main Deliverable

- `IBIS_KuKd_continuous_gate_state_from_notes_revised.pptx`
- `IBIS_KuKd_handwritten_notes_strict_Vc.pptx`
- `IBIS_KuKd_handwritten_notes_strict_Vc_corrected.pptx`

The strict-Vc version follows the handwritten vocabulary and order. It uses
`Vc`, `Vc_PU`, and `Vc_PD` throughout and does not introduce the internal
terminology used by the implementation-focused deck.

The revised deck contains 17 slides and follows the reusable green lab template. Every
slide has presenter notes. All 27 mathematical expressions were rendered by the
presentation toolkit's MathJax backend rather than PowerPoint's equation editor.

## Story

1. Why elapsed-time Ku/Kd replay is discontinuous at an interrupted edge.
2. How an RC capacitor voltage stores continuous transition state.
3. The first-order state equation and closed-form response.
4. The 63.2% interpretation of tau.
5. Four direction-specific tau paths.
6. Offline conversion from `K(t)` to `K=f(G)`.
7. Separation of offline model generation from runtime integration.
8. Normal rising-edge behavior.
9. Mid-transition reversal without a state reset.
10. Real cached `GUP/GDN` waveforms through a 1 ns interrupted pulse.
11. Real `Ku(GUP)/Kd(GDN)` waveforms, including measured directional-map jumps.
12. The generated ngspice capacitor/behavioral-source implementation.
13. Mapping `GUP/GDN` back to `Ku/Kd` and IBIS V-I currents.
14. Scope, strengths, and remaining validation requirements.
15. The next-step list recorded on page three of the handwritten notes.

The final appendix includes presentation-sized copies of all three handwritten
source pages.

## Rebuild

From the repository root:

```powershell
$env:PYTHONPATH = ".codex_deps/presentation/python;."
py -3.14 scripts\build_ibis_kukd_handwritten_notes_deck.py
```

## Supporting Files

- `equation_manifest.csv`: TeX source and cached rendered asset for every equation.
- `real_short_pulse_1ns_high_waveforms.csv`: numeric cached waveform data used by
  the real-example slides.
- `strict_vc_real_example_waveforms.csv`: the same cached example exported with
  the handwritten `Vc` terminology.
- `strict_vc_equation_manifest.csv`: TeX source for the strict-Vc deck.
- `generated_assets/`: conceptual plots and compressed source-page copies.
- `strict_vc_assets/`: strict-notation plots and source-page copies.
- `source_pages/`: full-resolution renderings of the supplied PDF.
- `slides_revised_final/`: PowerPoint-rendered PNG review exports of the revised deck.
- `slides_strict_vc/`: PowerPoint-rendered PNG review exports of the strict-Vc deck.
- `slides_strict_vc_corrected_review/`: review exports of the corrected strict-Vc deck.
- `hspice_slow_fast_transistor_comparison/`: cached-data HSPICE figures comparing
  the old slow-characterized IBIS, regenerated 5 ps IBIS, and source transistor
  under the same `50 ohm || 2 pF` direct-load bench. Its
  `short_pulse_cases/` subfolder covers the matched interrupted-pulse cases.

Source PDF:

`\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\IBIS kukd .pdf`
