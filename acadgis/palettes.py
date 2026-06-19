"""Color palettes for acadgis.

Mirrors the palette set of the AcadGIS web app so figures share the same
visual identity. Each palette is available either as a discrete list of
colors (for categorical / per-region fills) or as a matplotlib colormap
(for sequential choropleths).
"""
from __future__ import annotations

from typing import List

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_hex

# --- Categorical / qualitative palettes (per-region distinct fills) ---------
CATEGORICAL = {
    # Soft ColorBrewer-inspired default.
    "classic": [
        "#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99",
        "#e31a1c", "#fdbf6f", "#ff7f00", "#cab2d6", "#6a3d9a",
        "#ffff99", "#b15928", "#8dd3c7", "#bebada", "#fb8072",
        "#80b1d3", "#fdb462", "#b3de69", "#fccde5", "#bc80bd",
    ],
    # Bold, high-contrast.
    "vibrant": [
        "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
        "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4",
        "#469990", "#dcbeff", "#9a6324", "#fffac8", "#800000",
        "#aaffc3", "#808000", "#ffd8b1", "#000075", "#a9a9a9",
    ],
    # Light & approachable.
    "pastel": [
        "#fbb4ae", "#b3cde3", "#ccebc5", "#decbe4", "#fed9a6",
        "#ffffcc", "#e5d8bd", "#fddaec", "#f2f2f2", "#cfe2f3",
        "#d9ead3", "#fff2cc", "#fce5cd", "#ead1dc", "#d0e0e3",
        "#c9daf8", "#d9d2e9", "#f4cccc", "#fce8b2", "#b6d7a8",
    ],
    # Earth / nature greens & browns.
    "earth": [
        "#005824", "#238b45", "#41ab5d", "#74c476", "#a1d99b",
        "#c7e9c0", "#e5f5e0", "#8c6d31", "#bf812d", "#dfc27d",
        "#f6e8c3", "#543005", "#806000", "#b3a000", "#5c4033",
        "#8b5a2b", "#cd853f", "#deb887", "#f5deb3", "#6b8e23",
    ],
    # Deep ocean blues.
    "ocean": [
        "#08306b", "#08519c", "#2171b5", "#4292c6", "#6baed6",
        "#9ecae1", "#c6dbef", "#deebf7", "#023858", "#045a8d",
        "#0570b0", "#3690c0", "#74a9cf", "#a6bddb", "#d0d1e6",
        "#016c59", "#02818a", "#3690c0", "#67a9cf", "#a6bddb",
    ],
    # Professional grayscale.
    "slate": [
        "#252525", "#404040", "#525252", "#636363", "#737373",
        "#969696", "#bdbdbd", "#d9d9d9", "#f0f0f0", "#2d3436",
        "#636e72", "#b2bec3", "#dfe6e9", "#454f54", "#5d6d7e",
        "#85929e", "#aab7b8", "#ccd1d1", "#e5e8e8", "#1c2833",
    ],
    # Warm->cool spectral, like the reference Iraq/Babylon figure.
    "spectral": [
        "#9e0142", "#d53e4f", "#f46d43", "#fdae61", "#fee08b",
        "#ffffbf", "#e6f598", "#abdda4", "#66c2a5", "#3288bd",
        "#5e4fa2", "#d73027", "#fc8d59", "#fee090", "#e0f3f8",
        "#91bfdb", "#4575b4", "#f46d43", "#74add1", "#a50026",
    ],
}

# --- Sequential colormaps (for continuous choropleths) ----------------------
# Map our palette names to matplotlib colormap names where one fits well, and
# build custom ones for the rest so every palette works in both modes.
_CUSTOM_SEQ = {
    "classic": ["#f7fbff", "#6baed6", "#08306b"],
    "vibrant": ["#fff5f0", "#fb6a4a", "#67000d"],
    "pastel": ["#ffffe5", "#fed98e", "#cc4c02"],
    "spectral": ["#3288bd", "#fee08b", "#9e0142"],
}
_MPL_SEQ = {
    "earth": "YlGn",
    "ocean": "Blues",
    "slate": "Greys",
    "magma": "magma",
    "viridis": "viridis",
    "inferno": "inferno",
    "plasma": "plasma",
    "cividis": "cividis",
}

ALL_PALETTES = sorted(set(CATEGORICAL) | set(_MPL_SEQ) | set(_CUSTOM_SEQ))


def get_colors(palette: str = "spectral", n: int = 10) -> List[str]:
    """Return ``n`` discrete hex colors for a categorical palette.

    Colors cycle if ``n`` exceeds the palette length. For sequential-only
    names (e.g. ``"magma"``) the colormap is sampled evenly instead.
    """
    palette = (palette or "spectral").lower()
    if palette in CATEGORICAL:
        base = CATEGORICAL[palette]
        return [base[i % len(base)] for i in range(n)]
    # sample a colormap
    cmap = get_cmap(palette)
    if n == 1:
        return [to_hex(cmap(0.5))]
    return [to_hex(cmap(i / (n - 1))) for i in range(n)]


def get_cmap(palette: str = "viridis"):
    """Return a matplotlib colormap for a palette name (sequential use)."""
    import matplotlib.pyplot as plt

    palette = (palette or "viridis").lower()
    if palette in _MPL_SEQ:
        return plt.get_cmap(_MPL_SEQ[palette])
    if palette in _CUSTOM_SEQ:
        return LinearSegmentedColormap.from_list(f"acadgis_{palette}", _CUSTOM_SEQ[palette])
    if palette in CATEGORICAL:
        # build a smooth ramp from the categorical colors
        return LinearSegmentedColormap.from_list(
            f"acadgis_{palette}", CATEGORICAL[palette][:6]
        )
    # last resort: matplotlib's own registry
    return plt.get_cmap(palette)


def preview(palette: str = "spectral", n: int = 10):
    """Quick visual check of a palette; returns a matplotlib Figure."""
    import matplotlib.pyplot as plt

    colors = get_colors(palette, n)
    fig, ax = plt.subplots(figsize=(n * 0.5, 1))
    for i, c in enumerate(colors):
        ax.add_patch(plt.Rectangle((i, 0), 1, 1, color=c))
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.set_title(palette)
    ax.axis("off")
    return fig
