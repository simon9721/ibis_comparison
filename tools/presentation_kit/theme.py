from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pptx.dml.color import RGBColor


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = REPO_ROOT / "assets" / "presentation_templates" / "mst_green_16x9.pptx"


@dataclass(frozen=True)
class PresentationTheme:
    """Visual tokens used by the reusable presentation helpers."""

    green: RGBColor = RGBColor(43, 122, 67)
    light_green: RGBColor = RGBColor(226, 240, 229)
    pale_green: RGBColor = RGBColor(241, 248, 242)
    dark: RGBColor = RGBColor(25, 31, 28)
    gray: RGBColor = RGBColor(102, 108, 104)
    light_gray: RGBColor = RGBColor(242, 243, 242)
    mid_gray: RGBColor = RGBColor(203, 208, 204)
    red: RGBColor = RGBColor(202, 48, 48)
    light_red: RGBColor = RGBColor(252, 235, 235)
    orange: RGBColor = RGBColor(218, 132, 38)
    blue: RGBColor = RGBColor(36, 103, 173)
    white: RGBColor = RGBColor(255, 255, 255)
    black: RGBColor = RGBColor(0, 0, 0)
    title_font: str = "Times New Roman"
    body_font: str = "Aptos"
    code_font: str = "Consolas"
    title_size_pt: float = 27.0
    body_size_pt: float = 17.0
    content_layout_index: int = 4


LAB_GREEN_THEME = PresentationTheme()
