"""Styling presets for acadgis figures.

A :class:`Theme` bundles the colours, line weights and font choices that
give a figure its look. Pick a built-in preset by name with :func:`get_theme`
or build your own.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict


@dataclass
class Theme:
    """Visual styling for a study-area figure."""

    # palette name (see acadgis.palettes)
    palette: str = "spectral"
    # geometry styling
    edge_color: str = "#333333"
    edge_width: float = 0.6
    fill_alpha: float = 1.0
    highlight_color: str = "#1d4ed8"   # selected region fill
    highlight_edge: str = "#0b2a8a"
    highlight_width: float = 1.4
    context_color: str = "#e5e7eb"     # un-highlighted background regions
    # figure styling
    background: str = "white"
    title_size: int = 14
    title_weight: str = "bold"
    label_size: int = 8
    label_color: str = "#222222"
    # graticule
    grid_color: str = "#9aa0a6"
    grid_alpha: float = 0.55
    grid_width: float = 0.5
    # decorations
    decoration_color: str = "#222222"

    def with_(self, **kwargs) -> "Theme":
        """Return a copy with the given fields overridden."""
        return replace(self, **kwargs)


_PRESETS: Dict[str, Theme] = {
    # Clean journal look (the default).
    "academic": Theme(),
    # The warm spectral, thin-border style of the reference Iraq figure.
    "atlas": Theme(
        palette="spectral", edge_color="#2b2b2b", edge_width=0.5,
        grid_color="#777777", grid_alpha=0.5,
    ),
    # Minimal greyscale for B&W print.
    "mono": Theme(
        palette="slate", edge_color="#000000", edge_width=0.7,
        highlight_color="#000000", highlight_edge="#000000",
        context_color="#f2f2f2", grid_color="#bbbbbb",
    ),
    # Environmental / green.
    "nature": Theme(
        palette="earth", edge_color="#274e13", highlight_color="#bf360c",
        highlight_edge="#7f0000", grid_color="#9aa79a",
    ),
    # Coastal / water studies.
    "ocean": Theme(
        palette="ocean", edge_color="#0b3954", highlight_color="#d7263d",
        highlight_edge="#7a0010", grid_color="#9bb3c4",
    ),
    # Scientific perceptual colourmap.
    "viridis": Theme(palette="viridis", edge_color="#222222"),
}


def list_themes():
    """Names of the built-in themes."""
    return sorted(_PRESETS.keys())


def get_theme(theme="academic") -> Theme:
    """Resolve a theme name (or pass a Theme through unchanged)."""
    if isinstance(theme, Theme):
        return theme
    key = (theme or "academic").lower()
    if key not in _PRESETS:
        raise ValueError(
            f"Unknown theme {theme!r}. Available: {list_themes()}"
        )
    return _PRESETS[key]
