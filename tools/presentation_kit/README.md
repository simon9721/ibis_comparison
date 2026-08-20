# Presentation Kit

This package turns the lab's green PowerPoint style into a reusable scripted
presentation workflow. It preserves the masters and layouts from the checked-in
template rather than approximating the design in Python.

## Setup

Run once from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_presentation_toolkit.ps1
```

The setup installs Python dependencies under `.codex_deps/presentation/python`
and, unless `-SkipMathJax` is used, a portable Node runtime plus MathJax 4 and
Sharp. No administrator installation is required.

## Build A Deck

```powershell
$env:PYTHONPATH = ".codex_deps/presentation/python;."
py -3.14 examples/presentation_toolkit/build_demo_deck.py
```

Core usage:

```python
from tools.presentation_kit import GreenDeck

deck = GreenDeck()
deck.set_title_slide("Project title", "Presenter\nDate")

slide = deck.add_slide("A technical result", section="Results")
deck.add_bullets(slide, ["First result", "Second result"], 0.7, 1.3, 5.0, 2.0)
deck.add_equation(slide, r"\frac{dG}{dt}=\frac{G_{target}-G}{\tau}", 6.2, 1.4, 5.6, 1.0)
deck.add_takeaway(slide, "One sentence the audience should remember.")
deck.add_notes(slide, "Presenter notes are written into the PPTX.")
deck.save("results/my_project/my_deck.pptx")
```

## Equation Rendering

`EquationRenderer(backend="auto")` uses:

1. **MathJax 4** when the optional local Node dependencies are installed. It
   accepts broad TeX/AMS syntax and first produces a self-contained SVG. Sharp
   then rasterizes that SVG to a tightly cropped transparent, high-DPI PNG that
   `python-pptx` can insert reliably.
2. **Matplotlib MathText** as a zero-setup fallback. It handles common symbols,
   fractions, roots, sums, integrals, superscripts, and subscripts, but it is a
   TeX subset and does not support every LaTeX environment.

Every rendered expression is content-addressed and cached under
`.codex_deps/presentation/equation_cache`. Rebuilding a deck does not re-render
unchanged equations. Each inserted equation also receives PowerPoint alt text
containing the original TeX source.

Force a backend when debugging:

```python
from tools.presentation_kit import EquationRenderer, GreenDeck

renderer = EquationRenderer(backend="mathjax")
deck = GreenDeck(equation_renderer=renderer)
```

## Included Building Blocks

- Template-based title and content slides
- Presenter notes
- Text and bullet regions
- Process boxes and arrows
- Code boxes
- Contained image placement
- Takeaway and source bands
- Cached equations through one API

The template is stored at `assets/presentation_templates/mst_green_16x9.pptx`.
Project-specific deck scripts should import this package instead of importing
another project's presentation generator.
