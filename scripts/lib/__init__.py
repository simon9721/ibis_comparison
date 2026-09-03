"""Shared library for the ibis_comparison scripts.

Everything importable here is plumbing rather than a study: locating the repo,
running a simulator, building a stimulus, reading a waveform. Studies live in
`scripts/` and import from here.

The flat `scripts/` tree is 238 files deep and 172 of them compute their repo
root as `Path(__file__).resolve().parents[1]`, which silently breaks the moment a
file moves a directory deeper. `repo_root()` below finds the root by marker
instead, so anything importing it can be relocated freely.
"""
from .paths import repo_root

__all__ = ["repo_root"]
