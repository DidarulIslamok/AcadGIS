"""Per-map zoom and framed sub-region callouts (the Alaska/Hawaii pattern).

Both are exposed on the top-level namespace, so users never import matplotlib::

    agis.zoom_axes(ax, 1.5)                 # zoom a single map in 1.5x
    agis.callout(ax, alaska, loc=(0.01, 0.02, 0.26, 0.26), title="Alaska")
"""
from __future__ import annotations

__all__ = ["zoom_axes", "callout"]


def zoom_axes(ax, factor, center=None):
    """Zoom ``ax`` by ``factor`` about ``center``.

    ``factor`` > 1 zooms **in** (e.g. 1.1, 1.5, 2.0), < 1 zooms **out**
    (0.9, 0.5). ``center`` is an optional ``(lon, lat)``; defaults to the
    current view centre. Aspect is preserved (both axes scale equally).
    """
    factor = float(factor) or 1.0
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    cx, cy = center if center else ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
    hw = (x1 - x0) / 2.0 / factor
    hh = (y1 - y0) / 2.0 / factor
    ax.set_xlim(cx - hw, cx + hw)
    ax.set_ylim(cy - hh, cy + hh)
    return ax


def callout(ax, gdf, *, loc=(0.02, 0.02, 0.28, 0.28), title=None,
            palette=None, color=None, terrain=False, cmap="terrain",
            edge="#333333", lw=1.0, facecolor="white", pad=0.06,
            graticule=False, zoom=1.0, title_size=8, download=True):
    """Add a framed inset of ``gdf`` to ``ax`` — the Alaska/Hawaii pattern.

    Parameters
    ----------
    loc:
        ``(x0, y0, w, h)`` in axes fraction — where the callout box sits and how
        big it is. Place it anywhere on the parent map.
    color / palette / terrain:
        Fill: a single ``color``, an AcadGIS ``palette`` (per-region colours), or
        ``terrain=True`` for shaded relief (``cmap``).
    edge, lw, facecolor:
        The callout frame (box outline colour/width and its background).
    zoom:
        Optional extra zoom of the sub-region inside its box.

    Returns the inset Axes so you can keep drawing on it.
    """
    inset = ax.inset_axes(list(loc))
    inset.set_facecolor(facecolor)
    if terrain:
        from . import load_dem
        from .terrain import relief
        dem = load_dem(gdf, download=download)
        relief(dem, ax=inset, cmap=cmap, hillshade=True,
               graticule=False, north_arrow=False, scale_bar=False)
    elif color is not None:
        gdf.plot(ax=inset, color=color, edgecolor=edge, linewidth=0.5)
        inset.set_aspect("equal")
    else:
        from .core import plot
        plot(gdf, ax=inset, palette=palette, graticule=graticule,
             north_arrow=False, scale_bar=False, border="none", pad=pad)
    if zoom and zoom != 1.0:
        zoom_axes(inset, zoom)
    inset.set_xticks([])
    inset.set_yticks([])
    for s in inset.spines.values():
        s.set_visible(True)
        s.set_edgecolor(edge)
        s.set_linewidth(lw)
    if title:
        inset.set_title(title, fontsize=title_size, fontweight="bold", pad=2)
    return inset
