#!/usr/bin/env python3
"""Prepare the method film's background music from a public-domain recording.

The first attempt was a synthetic pad - five sines through a moving average - and it sounded
like exactly that. This replaces it with a real recording, chosen for its licence as much as
its mood, and records the provenance here so it lives with the file.

Source (primary)
    Erik Satie, Gymnopedie No. 1, performed and uploaded by Wikimedia Commons user Teknopazzo.
    https://commons.wikimedia.org/wiki/File:Gymnopedie_No._1..ogg
    Direct: https://upload.wikimedia.org/wikipedia/commons/b/b7/Gymnopedie_No._1..ogg
    Licence: CC0 1.0 (Creative Commons Zero, public domain dedication). No attribution required.
    Composition: Satie, 1888 - public domain.

Source (fallback)
    Same piece, performed by Robin Alciatore.
    https://commons.wikimedia.org/wiki/File:Erik_Satie_-_gymnopedies_-_la_1_ere._lent_et_douloureux.ogg
    Licence: public domain. No attribution required. 183.6 s - shorter than the film.

Both licence fields were read from the Commons API (extmetadata LicenseShortName /
AttributionRequired), not from a search summary.

What this does: decode with the bundled ffmpeg, trim to just under the film's run time, fade
in briefly and out over the last seconds, scale to a modest peak, write a 44.1 kHz stereo wav
that Scene.add_sound mixes in.

THE LENGTH MATTERS. manim sets the output length to the LONGER of the animations and the
audio, so audio longer than the film appends a frozen final frame. Keep `--seconds` below the
film's run time (3:17.93 at the time of writing) and regenerate if the film grows past it.

    py -3.14 scripts/make_film_bgm.py [--seconds 196] [--peak 0.35] [--source PATH]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "method_animations_2026-09-17"
OUT = RES / "bgm.wav"
SOURCE = RES / "bgm_source" / "satie_gymnopedie1_teknopazzo_CC0.ogg"
SR = 44100


def find_ffmpeg() -> str:
    """The scratchpad's bundled ffmpeg first, then whatever is on PATH."""
    for p in (Path(r"C:\Users\sh3qm\AppData\Local\Temp\claude\c--Users-sh3qm-code-ibis-comparison"
                   r"\4830c25e-e99f-44a8-8aaf-2a359f268df1\scratchpad\bin\ffmpeg.exe"),):
        if p.is_file():
            return str(p)
    return "ffmpeg"


def decode(src: Path, tmp: Path) -> np.ndarray:
    subprocess.run([find_ffmpeg(), "-y", "-v", "error", "-i", str(src),
                    "-ar", str(SR), "-ac", "2", "-f", "wav", str(tmp)], check=True)
    with wave.open(str(tmp), "rb") as fh:
        n = fh.getnframes()
        raw = fh.readframes(n)
    pcm = np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).astype(np.float64) / 32768.0
    return pcm


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=196.0)
    ap.add_argument("--peak", type=float, default=0.35)
    ap.add_argument("--fade-in", type=float, default=1.5)
    ap.add_argument("--fade-out", type=float, default=7.0)
    ap.add_argument("--source", type=Path, default=SOURCE)
    a = ap.parse_args()
    if not a.source.is_file():
        sys.exit("source not found: %s  (see the docstring for where it comes from)" % a.source)

    tmp = RES / "_bgm_decode.wav"
    y = decode(a.source, tmp)
    tmp.unlink(missing_ok=True)
    total = len(y) / SR
    n = min(len(y), int(SR * a.seconds))
    y = y[:n].copy()

    fi, fo = int(SR * a.fade_in), int(SR * a.fade_out)
    env = np.ones(n)
    env[:fi] = np.linspace(0.0, 1.0, fi)
    env[-fo:] = np.linspace(1.0, 0.0, fo)
    y *= env[:, None]
    pk = float(np.abs(y).max())
    y *= a.peak / pk

    pcm = (np.clip(y, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(OUT), "wb") as fh:
        fh.setnchannels(2)
        fh.setsampwidth(2)
        fh.setframerate(SR)
        fh.writeframes(pcm.tobytes())
    print("source  : %s  (%.1f s in the file)" % (a.source.name, total))
    print("wrote   : %s  (%.1f s, %.2f MB, peak %.2f, fade out over the last %.0f s)"
          % (OUT, n / SR, OUT.stat().st_size / 1e6, a.peak, a.fade_out))


if __name__ == "__main__":
    main()
