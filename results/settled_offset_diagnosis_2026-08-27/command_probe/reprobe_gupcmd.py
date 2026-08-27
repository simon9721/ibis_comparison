"""Re-run the five io_buf short-high hybrid cases with GUPCMD probed.

The shipped decks save only GUPTARGET, which is min(max(GUPCMD,0),1). That
clamp is exactly what the open question is about: whether the two clean cases
land on zero because the command really is zero, or because it went negative
and the clamp hid it. GUPCMD is the unclamped node, so probing it settles it.

The decks are self-contained -- run.sp plus the generated .sub -- so this
copies each case, extends the .save line, and re-runs ngspice directly rather
than going through the campaign runner.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\sh3qm\code\ibis_comparison")
SCRATCH = Path(__file__).resolve().parent / "gupcmd_probe"
NGSPICE = ROOT / ".codex_deps" / "ngspice-46_64" / "Spice64" / "bin" / "ngspice_con.exe"
MATRIX = ROOT / "results" / "stress_method_matrix_2026-08-20"

# target -> pulse width, from run_stress_method_matrix.stress_cases()
CASES = {90: 2484, 80: 2226, 70: 1989, 60: 1792, 50: 1634}
EXTRA = ["V(xdrv.gupcmd)", "V(xdrv.gdncmd)", "V(xdrv.cmdsettled)", "V(xdrv.hnx)"]


def source_dir(width_ps: int) -> Path:
    hits = list(MATRIX.glob(f"hybrid/ngspice_runs/io_buf/*/*/cases/"
                            f"short_high_w{width_ps}ps_*/ngspice_gate_state"))
    if not hits:
        raise SystemExit(f"no hybrid run for {width_ps} ps")
    return hits[0]


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for target, width in CASES.items():
        src = source_dir(width)
        dst = SCRATCH / f"swing_{target}_w{width}ps"
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        for name in ("run.sp", "driver_OutputInput_Typical.sub"):
            shutil.copy2(src / name, dst / name)

        deck = (dst / "run.sp").read_text(encoding="utf-8")
        lines = []
        for line in deck.splitlines():
            if line.lower().startswith(".save"):
                have = line.split()
                line = " ".join(have + [e for e in EXTRA if e not in have])
            lines.append(line)
        (dst / "run.sp").write_text("\n".join(lines) + "\n", encoding="utf-8")

        print(f"[{target}%  {width} ps] running", flush=True)
        with (dst / "ngspice_stdout.log").open("w", encoding="utf-8") as log:
            rc = subprocess.run([str(NGSPICE), "-b", "-r", "run.raw", "run.sp"],
                                cwd=dst, stdout=log, stderr=subprocess.STDOUT,
                                timeout=600).returncode
        print(f"    rc={rc}  raw={'yes' if (dst / 'run.raw').exists() else 'NO'}", flush=True)
    print(SCRATCH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
