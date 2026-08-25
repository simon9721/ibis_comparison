#!/usr/bin/env python3
"""Pull slide-ready stills out of the rendered Ku/Kd animation.

There is no external ffmpeg on this machine -- manim brings its own PyAV -- so
frames come out through av rather than a subprocess.

Times are named rather than computed. The scene's act boundaries depend on a
dozen run_times, and a still that lands half way through a fade is worse than
one placed by hand against the finished render.

    py -3.13 scripts/grab_kukd_stills.py
    py -3.13 scripts/grab_kukd_stills.py --video path/to/other.mp4
"""
from __future__ import annotations

import argparse
from pathlib import Path

import av

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "kukd_animation" / "stills"
DEFAULT = ROOT / "media" / "videos" / "animate_kukd_extraction" / "1080p60" / "KuKdExtraction.mp4"

MOMENTS = {
    "01_schematic": 6.5,
    "02_equation": 10.5,
    "03_one_fixture": 18.5,
    "04_two_fixtures": 24.5,
    "05_iv_lookup": 33.0,
    "06_known_current": 37.5,
    "07_second_fixture": 42.3,
    "08_solve": 49.5,
    "09_sweep": 62.0,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=DEFAULT)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if not args.video.exists():
        print("no render at %s -- render the scene first" % args.video)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)

    container = av.open(str(args.video))
    stream = container.streams.video[0]
    duration = float(stream.duration * stream.time_base)
    wanted = {name: t for name, t in MOMENTS.items() if t < duration}
    for name, t in MOMENTS.items():
        if name not in wanted:
            print("  skipped %s: %.1f s is past the end (%.1f s)" % (name, t, duration))

    pending = dict(wanted)
    for frame in container.decode(stream):
        if not pending:
            break
        now = float(frame.pts * stream.time_base)
        for name, t in list(pending.items()):
            if now >= t:
                frame.to_image().save(args.out / (name + ".png"))
                del pending[name]
    for old in args.out.glob("*.png"):
        if old.stem not in MOMENTS:
            old.unlink()
    print("wrote %d stills to %s" % (len(wanted), args.out.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
