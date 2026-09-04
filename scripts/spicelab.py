#!/usr/bin/env python3
"""Shared SPICE plumbing: run a simulator, build a stimulus, read a waveform.

Item 5 of `0902_plan.md` -- the reusable core. Across scripts/ the same few
operations are hand-rolled again and again: 156 scripts shell out to a
simulator, 119 parse a waveform, 59 build a `.tran` deck, 35 write a PWL
stimulus. Four scripts written in this session alone each carry their own
near-identical `run()` and `pwl()`. This module is the one place those live.

It deliberately does not wrap the deck *content* -- every buffer study needs its
own topology, and a template that tried to cover all of them would be worse than
writing the deck. It wraps the mechanics around the deck: finding the simulator,
running it with a timeout and a captured log, building the input source, and
pulling a named trace out of the result regardless of how the simulator spelled
the node.

    from spicelab import run_spice, hspice, ngspice, pwl, parse_hspice_tr0, trace

Every helper here is copied behaviour, not new behaviour: `run_spice` is the
campaign's proven `run_process`, `signal`/`trace` are its `signal` lookup, the
parsers and paths are re-exported from the existing shared modules so one import
covers the common case.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

# Re-export the existing shared helpers so callers need one import, not four.
from spice_tool_paths import default_hspice, default_ngspice, first_existing  # noqa: E402,F401
from eye_diagram import parse_hspice_tr0, parse_ngspice_raw  # noqa: E402,F401

__all__ = [
    "default_hspice", "default_ngspice", "first_existing",
    "parse_hspice_tr0", "parse_ngspice_raw",
    "run_spice", "hspice", "ngspice",
    "pwl", "pulse", "clock",
    "signal", "trace", "time_ns", "load_waveform",
    "vt_fixtures",
]


# --------------------------------------------------------------------------- #
# Running a simulator
# --------------------------------------------------------------------------- #

def _no_window_flags() -> int:
    """Suppress the console window HSPICE/ngspice pop on Windows."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_spice(command: list[str], cwd: Path, log_path: Path, timeout_s: int) -> int:
    """Run a command in `cwd`, capture stdout+stderr to `log_path`, return the code.

    A timeout returns 124 and still writes the partial log, so a hung simulator
    is distinguishable from a failed one. This is the campaign's `run_process`,
    which every recent study has copied.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        done = subprocess.run(
            [str(c) for c in command], cwd=str(cwd),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=timeout_s, check=False, creationflags=_no_window_flags(),
        )
    except subprocess.TimeoutExpired as exc:
        captured = exc.stdout or ""
        if isinstance(captured, bytes):
            captured = captured.decode("utf-8", errors="replace")
        log_path.write_text(
            "COMMAND: " + " ".join(map(str, command))
            + f"\n\nTIMEOUT after {timeout_s} seconds\n\n{captured}",
            encoding="utf-8", errors="replace")
        return 124
    log_path.write_text(
        "COMMAND: " + " ".join(map(str, command)) + "\n\n" + (done.stdout or ""),
        encoding="utf-8", errors="replace")
    return int(done.returncode)


def hspice(run_dir: Path, deck: str = "run.sp", stem: str = "run",
           timeout_s: int = 600, hspice_path: Path | None = None) -> Path | None:
    """Run HSPICE on `run_dir/deck` and return the .tr0 path, or None on failure.

    The deck must already be written into `run_dir`; HSPICE runs there so bare
    `.include` filenames resolve. Reads back nothing -- the caller parses the
    returned path when it wants data.
    """
    exe = Path(hspice_path) if hspice_path else default_hspice()
    code = run_spice([str(exe), "-i", deck, "-o", stem], Path(run_dir),
                     Path(run_dir) / f"{stem}.hspice.log", timeout_s)
    tr0 = Path(run_dir) / f"{stem}.tr0"
    return tr0 if (code == 0 and tr0.exists()) else None


def ngspice(run_dir: Path, deck: str = "run.sp", raw: str = "run.raw",
            timeout_s: int = 600, ngspice_path: Path | None = None) -> Path | None:
    """Run ngspice in batch on `run_dir/deck` and return the .raw path, or None."""
    exe = Path(ngspice_path) if ngspice_path else default_ngspice(console=True)
    code = run_spice([str(exe), "-b", "-r", raw, deck], Path(run_dir),
                     Path(run_dir) / "ngspice.log", timeout_s)
    raw_path = Path(run_dir) / raw
    return raw_path if (code == 0 and raw_path.exists()) else None


# --------------------------------------------------------------------------- #
# Building a stimulus
# --------------------------------------------------------------------------- #

def _fmt_ns(t_s: float) -> str:
    return f"{t_s * 1e9:.6g}n"


def pwl(points: list[tuple[float, float]]) -> str:
    """A PWL(...) source string from (time_seconds, volts) pairs.

        pwl([(0, 0), (5e-9, 0), (5.001e-9, 3.3), (15e-9, 3.3)])
    """
    body = "  ".join(f"{_fmt_ns(t)} {v:g}" for t, v in points)
    return f"PWL({body})"


def pulse(low: float, high: float, edges_ns: list[float], *, start_high: bool = False,
          edge_ps: float = 1.0, stop_ns: float | None = None) -> str:
    """A PWL that toggles between `low` and `high` at each time in `edges_ns`.

    Each edge is a near-step of `edge_ps`. `start_high` sets the level before the
    first edge. This is the single/short-pulse stimulus every buffer bench uses;
    `edges_ns=[5, 15]` with the defaults gives a low-start pulse high 5->15 ns.
    """
    level = high if start_high else low
    points: list[tuple[float, float]] = [(0.0, level)]
    for t_ns in edges_ns:
        t = t_ns * 1e-9
        points.append((t, level))
        level = low if level == high else high
        points.append((t + edge_ps * 1e-12, level))
    if stop_ns is not None:
        points.append((stop_ns * 1e-9, level))
    return pwl(points)


def clock(period_ns: float, count: int, low: float, high: float, *,
          start_ns: float = 0.0, duty: float = 0.5, edge_ps: float = 1.0) -> str:
    """A periodic clock PWL: `count` cycles of `period_ns`, `duty` high fraction."""
    edges: list[float] = []
    for i in range(count):
        t0 = start_ns + i * period_ns
        edges.append(t0)
        edges.append(t0 + duty * period_ns)
    return pulse(low, high, edges, start_high=False, edge_ps=edge_ps,
                 stop_ns=start_ns + count * period_ns)


# --------------------------------------------------------------------------- #
# Reading a waveform
# --------------------------------------------------------------------------- #

def _normalized(raw: dict) -> dict[str, str]:
    return {key.lower().replace(":", "."): key for key in raw}


def signal(raw: dict, *names: str) -> np.ndarray:
    """A trace by exact node name, case- and colon/dot-insensitive.

        signal(raw, "v(pad)", "v(pad_sp)")   # first that matches
    """
    lookup = _normalized(raw)
    for name in names:
        key = lookup.get(name.lower().replace(":", "."))
        if key is not None:
            return np.asarray(raw[key], dtype=float)
    raise KeyError(f"none of {names} in {sorted(raw)[:12]}...")


def trace(raw: dict, substring: str) -> np.ndarray:
    """The first trace whose node name contains `substring` (case-insensitive).

    For when the exact node name varies -- `v(pad)`, `v(pad_sp)`, `v(pad_ibis)`
    all match `trace(raw, "pad")`. Ambiguity picks the first, so pass a
    substring specific enough to be unique.
    """
    for key in raw:
        if substring.lower() in key.lower():
            return np.asarray(raw[key], dtype=float)
    raise KeyError(f"no node containing {substring!r} in {sorted(raw)[:12]}...")


def time_ns(raw: dict) -> np.ndarray:
    """The time axis in nanoseconds, however the simulator spelled 'time'."""
    for key in raw:
        if key.lower() == "time":
            return np.asarray(raw[key], dtype=float) * 1e9
    raise KeyError("no 'time' column")


def load_waveform(path: Path, node: str) -> tuple[np.ndarray, np.ndarray]:
    """(time_ns, trace) from a .tr0 or .raw file, picking the parser by suffix."""
    path = Path(path)
    raw = parse_hspice_tr0(path) if path.suffix.lower() == ".tr0" else parse_ngspice_raw(path)
    return time_ns(raw), trace(raw, node)


if __name__ == "__main__":
    # Smoke test the pure-Python helpers without touching a simulator.
    print("pulse low-start 5..15ns:", pulse(0.0, 3.3, [5, 15], stop_ns=22))
    print("clock 2ns x3:          ", clock(2.0, 3, 0.0, 1.8))
    print("default_hspice:        ", default_hspice())


# --------------------------------------------------------------------------- #
# Native IBIS V-T table selection
# --------------------------------------------------------------------------- #

def vt_fixtures(ibis: Path) -> dict[str, list[float | None]]:
    """[V_fixture] of each [Rising]/[Falling] Waveform table, in file order.

    Needed to interpret HSPICE's `ramp_rwf` / `ramp_fwf`, which choose how much
    V-T data the B-element uses -- **not** which table:

        0 = use [Ramp] data
        1 = use one waveform  (the first of that kind in the file)
        2 = use two waveforms (the first two)   -- the documented default

    So under `=1` the fixture of the *first* table is what the model is played
    back into, and that order is set by whoever wrote the .ibs:

        inv_chain   (1.8, 0.0)      io_buf   (0.0, 3.3)      ex2   (0.0, 3.3)

    Every bench here loads the pad with 50 ohm to ground, so a `=1` run is
    load-matched on io_buf and ex2 but not on inv_chain. Worth checking before
    reading across buffers, because the two-waveform default silently produces a
    dead output on ex2 while `=1` tracks the transistor.
    """
    kinds: dict[str, list[float | None]] = {"rising": [], "falling": []}
    cur: str | None = None
    for line in Path(ibis).read_text(errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("["):
            m = re.match(r"\[(Rising|Falling) Waveform\]", s, re.I)
            cur = m.group(1).lower() if m else None
            if cur:
                kinds[cur].append(None)
            continue
        if cur is None:
            continue
        m = re.match(r"V_fixture\s*=\s*([-+0-9.eE]+)", s, re.I)
        if m and kinds[cur] and kinds[cur][-1] is None:
            kinds[cur][-1] = float(m.group(1))
    return kinds
