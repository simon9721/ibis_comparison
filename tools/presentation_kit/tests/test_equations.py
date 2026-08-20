from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest

from tools.presentation_kit.equations import EquationRenderer


def test_mathtext_render_is_cached(tmp_path: Path) -> None:
    renderer = EquationRenderer(tmp_path, backend="mathtext", dpi=180)
    first = renderer.render(r"\frac{dG}{dt}=\frac{G_t-G}{\tau}")
    second = renderer.render(r"\frac{dG}{dt}=\frac{G_t-G}{\tau}")
    assert first.path == second.path
    assert first.path.exists()
    assert first.metadata_path.exists()
    with Image.open(first.path) as image:
        assert image.width > 10
        assert image.height > 10


def test_display_delimiters_do_not_change_cache_key(tmp_path: Path) -> None:
    renderer = EquationRenderer(tmp_path, backend="mathtext", dpi=180)
    plain = renderer.render(r"x^2+y^2")
    wrapped = renderer.render(r"\[x^2+y^2\]")
    assert plain.path == wrapped.path


def test_mathjax_renders_ams_aligned_expression(tmp_path: Path) -> None:
    renderer = EquationRenderer(tmp_path, backend="auto", dpi=180)
    if not renderer.mathjax_available():
        pytest.skip("optional MathJax backend is not installed")
    asset = EquationRenderer(tmp_path, backend="mathjax", dpi=180).render(
        r"\begin{aligned} y_1 &= ax+b \\ y_2 &= \int_0^T x(t)\,dt \end{aligned}"
    )
    with Image.open(asset.path) as image:
        assert image.width > 20
        assert image.height > 20
