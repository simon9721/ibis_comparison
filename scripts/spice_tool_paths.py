from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[-1]


def default_ngspice(console: bool = False) -> Path:
    """Return the preferred ngspice executable for this workspace.

    Resolution order:
    1. NGSPICE_EXE environment variable.
    2. Repo-local ignored copy under .codex_deps.
    3. User's downloaded network-share copy.
    4. PATH fallback.
    """
    env_value = os.environ.get("NGSPICE_EXE")
    if env_value:
        return Path(env_value)
    exe_name = "ngspice_con.exe" if console else "ngspice.exe"
    return first_existing(
        [
            ROOT / ".codex_deps" / "ngspice-46_64" / "Spice64" / "bin" / exe_name,
            Path(r"\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin") / exe_name,
            Path(exe_name),
        ]
    )


def default_hspice() -> Path:
    env_value = os.environ.get("HSPICE_EXE")
    if env_value:
        return Path(env_value)
    return first_existing(
        [
            Path(r"C:\synopsys\Hspice_T-2022.06\WIN64\hspice.com"),
            Path("hspice"),
        ]
    )

