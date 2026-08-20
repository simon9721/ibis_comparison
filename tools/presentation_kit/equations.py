from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = REPO_ROOT / ".codex_deps" / "presentation" / "equation_cache"
DEFAULT_NODE = REPO_ROOT / ".codex_deps" / "presentation" / "node" / "node.exe"
MATHJAX_RUNNER = Path(__file__).resolve().parent / "mathjax" / "render_equation.mjs"
MATHJAX_PACKAGE = Path(__file__).resolve().parent / "mathjax" / "node_modules" / "@mathjax" / "src"
SHARP_PACKAGE = Path(__file__).resolve().parent / "mathjax" / "node_modules" / "sharp"


@dataclass(frozen=True)
class EquationAsset:
    """Rendered equation plus the backend and source used to make it."""

    path: Path
    backend: str
    tex: str
    metadata_path: Path


class EquationRenderer:
    """Render TeX equations to cached transparent PNG assets.

    ``backend='auto'`` prefers MathJax when its local Node dependencies are
    installed, then falls back to Matplotlib MathText. The caller does not need
    to change when the higher-fidelity backend becomes available.
    """

    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE,
        backend: str = "auto",
        dpi: int = 360,
    ) -> None:
        if backend not in {"auto", "mathjax", "mathtext"}:
            raise ValueError("backend must be one of: auto, mathjax, mathtext")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.requested_backend = backend
        self.dpi = dpi

    @property
    def node_executable(self) -> Path | None:
        configured = os.environ.get("PRESENTATION_NODE", "").strip()
        if configured and Path(configured).exists():
            return Path(configured)
        if DEFAULT_NODE.exists():
            return DEFAULT_NODE
        found = shutil.which("node")
        return Path(found) if found else None

    def mathjax_available(self) -> bool:
        return bool(
            self.node_executable
            and MATHJAX_RUNNER.exists()
            and MATHJAX_PACKAGE.exists()
            and SHARP_PACKAGE.exists()
        )

    def selected_backend(self) -> str:
        if self.requested_backend == "mathjax":
            if not self.mathjax_available():
                raise RuntimeError(
                    "MathJax backend is not installed. Run scripts/setup_presentation_toolkit.ps1 "
                    "or select backend='mathtext'."
                )
            return "mathjax"
        if self.requested_backend == "mathtext":
            return "mathtext"
        return "mathjax" if self.mathjax_available() else "mathtext"

    def render(
        self,
        tex: str,
        *,
        font_size_pt: float = 30,
        color: str = "#000000",
        display: bool = True,
        force: bool = False,
    ) -> EquationAsset:
        clean_tex = self._strip_display_delimiters(tex.strip())
        backend = self.selected_backend()
        settings = {
            "backend": backend,
            "tex": clean_tex,
            "font_size_pt": float(font_size_pt),
            "color": color,
            "display": bool(display),
            "dpi": int(self.dpi),
            "renderer_version": 1,
        }
        digest = hashlib.sha256(json.dumps(settings, sort_keys=True).encode("utf-8")).hexdigest()[:20]
        png_path = self.cache_dir / f"equation_{digest}.png"
        metadata_path = self.cache_dir / f"equation_{digest}.json"
        if force or not png_path.exists():
            if backend == "mathjax":
                self._render_mathjax(clean_tex, png_path, settings)
            else:
                self._render_mathtext(clean_tex, png_path, settings)
            self._trim_transparent_png(png_path)
            metadata_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        elif not metadata_path.exists():
            metadata_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        return EquationAsset(png_path, backend, clean_tex, metadata_path)

    @staticmethod
    def _strip_display_delimiters(tex: str) -> str:
        if tex.startswith("$$") and tex.endswith("$$"):
            return tex[2:-2].strip()
        if tex.startswith("$") and tex.endswith("$"):
            return tex[1:-1].strip()
        if tex.startswith(r"\[") and tex.endswith(r"\]"):
            return tex[2:-2].strip()
        return tex

    def _render_mathjax(self, tex: str, output: Path, settings: dict[str, object]) -> None:
        node = self.node_executable
        if node is None:
            raise RuntimeError("Node executable disappeared while rendering an equation")
        request = output.with_suffix(".request.json")
        svg_path = output.with_suffix(".svg")
        request.write_text(
            json.dumps(
                {
                    "tex": tex,
                    "output_png": str(output.resolve()),
                    "output_svg": str(svg_path.resolve()),
                    "font_size_pt": settings["font_size_pt"],
                    "color": settings["color"],
                    "display": settings["display"],
                    "dpi": settings["dpi"],
                }
            ),
            encoding="utf-8",
        )
        try:
            proc = subprocess.run(
                [str(node), str(MATHJAX_RUNNER), str(request)],
                cwd=MATHJAX_RUNNER.parent,
                text=True,
                capture_output=True,
                timeout=90,
                check=False,
            )
        finally:
            request.unlink(missing_ok=True)
        if proc.returncode != 0 or not output.exists():
            raise RuntimeError(
                "MathJax equation rendering failed.\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )

    @staticmethod
    def _render_mathtext(tex: str, output: Path, settings: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # MathText is intentionally the no-external-tool fallback. It supports
        # common TeX math but not full LaTeX environments such as aligned.
        expression = f"${tex}$"
        fig = plt.figure(figsize=(0.01, 0.01), dpi=int(settings["dpi"]))
        fig.patch.set_alpha(0.0)
        fig.text(
            0,
            0,
            expression,
            fontsize=float(settings["font_size_pt"]),
            color=str(settings["color"]),
            family="STIXGeneral",
        )
        try:
            fig.savefig(
                output,
                dpi=int(settings["dpi"]),
                transparent=True,
                bbox_inches="tight",
                pad_inches=0.035,
            )
        except Exception as exc:
            raise RuntimeError(
                "Matplotlib MathText could not render this expression. Install the MathJax backend "
                "for full TeX support by running scripts/setup_presentation_toolkit.ps1."
            ) from exc
        finally:
            plt.close(fig)

    @staticmethod
    def _trim_transparent_png(path: Path, padding_px: int = 8) -> None:
        from PIL import Image

        with Image.open(path).convert("RGBA") as image:
            bounds = image.getchannel("A").getbbox()
            if bounds is None:
                raise RuntimeError(f"Equation renderer produced a blank image: {path}")
            left, top, right, bottom = bounds
            left = max(0, left - padding_px)
            top = max(0, top - padding_px)
            right = min(image.width, right + padding_px)
            bottom = min(image.height, bottom + padding_px)
            image.crop((left, top, right, bottom)).save(path)
