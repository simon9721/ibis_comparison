# Two-State Directional-Residual Presentation

Presentation files:

- `0714_two_state_directional_residual_presentation.pptx`
- `0714_two_state_directional_residual_presentation.pdf`

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

The generator reads the template from:

`\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\0710_Simon_IBIS.pptx`
