# archive/

Directories and one-off inputs no longer referenced by any active script or
current document. Kept rather than deleted, because several are original inputs
(vendor IBIS models, channel data) that would be hard to reconstruct.

Classification was measured, not guessed: a directory is here if **zero** of the
44 active scripts and none of the root docs reference it as a path. Most are
still referenced by `scripts/archive/`, which is dead code — so those scripts'
paths are broken by this move, and that is accepted.

| directory | why archived |
|---|---|
| `PIC18F1xQ20_LV_IBIS_Models` | vendor IBIS set, used only by archived conversion scripts |
| `SimIbis_FreeSpice_From_SPISim` | reference implementation consulted once |
| `assets`, `examples` | unreferenced anywhere, active or archived |
| `channels`, `new 50ohm channel` | channel/S-parameter data for the retired PRBS work |
| `hspice_smoke` | unreferenced smoke-test outputs |
| `pcbauto` | unreferenced |
| `run_vector_fit_*.cmd` | overnight drivers for the retired vector-fit study |

**If something here turns out to be live**, move it back to the root and it will
work again — nothing about the contents changed.
