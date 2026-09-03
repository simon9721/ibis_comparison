# Two-State Directional-Residual Presentation

Presentation files:

- `0714_two_state_directional_residual_presentation.pptx`
- `0714_two_state_directional_residual_presentation.pdf`
- `0717_gate_state_short_pulse_meeting_deck.pptx`
- `0717_gate_state_short_pulse_meeting_deck.pdf`
- `0717_gate_state_short_pulse_meeting_deck_contact_sheet.png`

## Concise Meeting Deck

The 15-slide `0717_gate_state_short_pulse_meeting_deck` is the concise meeting version. Its 13-slide main path covers:

1. The interrupted short-pulse problem.
2. Original Ku/Kd meaning and legacy table replay.
3. The two-state GUP/GDN gate-state innovation.
4. Derivation from the four complete-edge coefficient traces.
5. Onset-delay and tau extraction with actual io_buf values.
6. Command-capacitor versus gate-capacitor memory.
7. Direction-specific GUP/GDN-to-Ku/Kd mapping.
8. The complete generated ngspice signal path and syntax.
9. A timestamped 1 ns short-high worked example.
10. Offline reconstruction-gate evidence.
11. Short-low success versus the open short-high Kd case.
12. Current conclusion and focused next step.

Two appendix slides cover the Kd rate residual and HSPICE/native-IBIS/transistor reference hierarchy. Every slide has detailed presenter notes. No simulation was rerun; all evidence figures use cached study data.

The 31-slide deck extends `0710_Simon_IBIS.pptx` and preserves its EMC-lab theme. Slides 1-8 retain the original approved story and layout, with the pulldown timing labels cross-checked against the generated model. It covers:

1. Beginner introduction to the output buffer and Ku/Kd.
2. Legacy short-pulse replay failure and value-matched failure.
3. Controlled HSPICE/ngspice validation setup.
4. Two-state directional-residual architecture and physical interpretation.
5. A beginner-oriented derivation of transition progress, delay, tau, hidden `GUP/GDN` state, direction-specific PWL maps, `dGDN/dt`, and the Kd residual.
6. Detailed Python fitting and generated ngspice implementation, including delayed command events and capacitor-backed state equations.
7. Offline reconstruction gate and cached waveform evidence.
8. Current measured status, limitations, and next steps.

Every slide includes presenter notes. The technical slides describe both the simplified interpretation and the exact implementation nuance that the Kd correction contains an elapsed-edge-time residual table plus the fitted rate term.

No HSPICE or ngspice simulations were rerun. All waveform figures use cached study data.

Regenerate the PPTX with:

```powershell
$env:PYTHONPATH = "$env:TEMP\ibis_pptx_target"
py -3.14 scripts/build_io_buf_two_state_gate_presentation.py
```

Regenerate the concise meeting deck with:

```powershell
$env:PYTHONPATH = "$env:TEMP\ibis_pptx_target"
py -3.14 scripts/build_io_buf_gate_state_meeting_deck.py
```

The generator reads the template from:

`\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\0710_Simon_IBIS.pptx`
