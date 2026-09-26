#!/usr/bin/env python3
"""Full-swing probe runs with a pulse only as long as each buffer needs to settle, so the
figure does not carry a long flat middle (ex2 3 ns, inv_chain 1 ns; io_buf keeps the 10 ns
run it already has). Every stage probed, same decks as predriver_stage_probe.py.

Written to results/predriver_stages_2026-09-09/<dev>/full_w<W>ps/. Normalisation still comes
from the original `full` run (its 0/1 levels are read at 4.5 and 14.5 ns).

    py -3.14 scripts/build_full_swing_probes.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import predriver_stage_probe as psp  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402

WIDTH_NS = {"ex2": 3.0, "inv_chain": 1.0}   # io_buf: the existing 10 ns run is right


def main() -> int:
    hspice = Path(default_hspice())
    for dev, w in WIDTH_NS.items():
        src = psp.OUT / dev / "full"
        d = psp.OUT / dev / f"full_w{int(w * 1000)}ps"
        d.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file() and not f.name.startswith("run."):
                shutil.copy2(f, d / f.name)
        deck = (src / "run.sp").read_text(encoding="utf-8", errors="replace")
        # the full run's PWL holds high from 5.05 ns to 15 ns; bring the falling edge in
        deck2 = re.sub(r"\+ 15n (\S+)\n\+ 15\.05n 0\n",
                       lambda m: f"+ {5 + w:g}n {m.group(1)}\n+ {5 + w + 0.05:g}n 0\n", deck, count=1)
        assert deck2 != deck, f"PWL edit failed for {dev}"
        (d / "run.sp").write_text(deck2, encoding="utf-8")
        if not (d / "run.tr0").exists():
            if base.run_process([str(hspice), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 1800) != 0:
                raise RuntimeError(f"hspice failed: {d}")
        print(f"  {dev}: {w:g} ns pulse -> {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
