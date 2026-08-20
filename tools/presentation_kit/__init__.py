"""Reusable PowerPoint authoring helpers for the lab presentation style."""

from .deck import GreenDeck
from .equations import EquationAsset, EquationRenderer
from .theme import DEFAULT_TEMPLATE, LAB_GREEN_THEME, PresentationTheme

__all__ = [
    "DEFAULT_TEMPLATE",
    "EquationAsset",
    "EquationRenderer",
    "GreenDeck",
    "LAB_GREEN_THEME",
    "PresentationTheme",
]
