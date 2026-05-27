# Good vs Bad PTC Std Comparison

- Package: `PIC18F1xQ20_vqfn20_LV`
- Good case: `ptc_i2c_std`
- Bad case: `ptc_i3c_std`
- Fixture: direct `50 ohm` to ground
- IBIS waveform target: nearest `R_fixture=50`, `V_fixture=0` rising/falling pair

## Why this pair

- `ptc_i2c_std` is a strong same-family good case.
- `ptc_i3c_std` is the repeated severe outlier.
- Both are PTC `std` models from the same package file, so the comparison stays focused on model behavior.

## Model facts

- `ptc_i2c_std`: `C_comp = 1.988 pF`, enable `Active-High`
- `ptc_i3c_std`: `C_comp = 13.619 pF`, enable `Active-High`

## Overlay metrics

| Model | Rise RMS (V) | Fall RMS (V) | Rise Max Abs (V) | Fall Max Abs (V) | Rise dT (ns) | Fall dT (ns) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `ptc_i2c_std` | 0.005098 | 0.009257 | 0.014020 | 0.019221 | 0.016 | 0.011 |
| `ptc_i3c_std` | 0.207928 | 0.169676 | 0.428825 | 0.438755 | 7.304 | -5.876 |
