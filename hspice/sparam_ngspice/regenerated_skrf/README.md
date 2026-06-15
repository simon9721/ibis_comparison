# scikit-rf S-parameter regeneration check

Date: 2026-06-07

Input Touchstone:

- `../../sparam/Clarity_example.S2P`

Regeneration script:

- `../../../scripts/regenerate_sparam_ngspice_skrf.py`

## Summary

The checked-in `../Clarity_example.sp` is byte-for-byte identical to:

- `auto_default/Clarity_example_auto_default_unforced.sp`

That means the existing ngspice channel model was generated with the scikit-rf `VectorFitting.auto_fit()` default flow, followed by `write_spice_subcircuit_s()`.

The sampled S2P itself is passive:

- max sampled singular value: `0.9981438316324364`
- frequency of max sampled singular value: `50 MHz`

The auto-fit rational model is not passive:

- RMS fit error: `0.0008010083795988382`
- model order: `9`
- passivity: `False`
- violation bands: about `2.98 GHz` to `infinity`
- dense fitted max singular value to `400 GHz`: about `37.736` near `7.8 GHz`

The regenerated fixed-pole model is passive:

- model: `vector_3r3c/Clarity_example_vector_3r3c_unforced.sp`
- flow: `VectorFitting.vector_fit(n_poles_real=3, n_poles_cmplx=3)`
- RMS fit error: `0.0009750705218759722`
- model order: `9`
- passivity: `True`
- dense fitted max singular value to `400 GHz`: `0.9983643763329778`

## ngspice smoke tests

The passive `vector_3r3c` channel model passed the channel-only sweep:

- summary: `vector_3r3c/channel_sweep/summary.csv`
- all 18 cases returned `rc=0`
- all 18 cases reached `12 ns`
- all 18 cases were finite and within the simple reasonableness bounds
- this includes ideal-source and low-source-resistance cases that failed with the auto-fit model

The passive model also passed the pybis-driver plus channel bench:

- deck: `../tb_ibis_sparam_batch_vector_3r3c.sp`
- raw: `../tb_ibis_sparam_batch_vector_3r3c.raw`
- log: `../tb_ibis_sparam_batch_vector_3r3c.log`
- stop time: `12 ns`
- `v(pad)`: `-0.1204834590 V` to `1.5573086800 V`
- `v(ntst)`: `-0.0528812109 V` to `1.5579765488 V`

## Rerun commands

Install scikit-rf into a temporary target, if needed:

```powershell
$target = Join-Path $env:TEMP 'ibis_skrf_target'
py -3.14 -m pip install --target $target scikit-rf
```

Regenerate and check passivity:

```powershell
$env:PYTHONPATH = Join-Path $env:TEMP 'ibis_skrf_target'
py -3.14 -B scripts\regenerate_sparam_ngspice_skrf.py
```

Run the passive-model channel sweep:

```powershell
py -3.14 -B scripts\sweep_sparam_ngspice_channel.py `
  --case-dir hspice\sparam_ngspice\regenerated_skrf\vector_3r3c\channel_sweep `
  --model-spice hspice\sparam_ngspice\regenerated_skrf\vector_3r3c\Clarity_example_vector_3r3c_unforced.sp
```
