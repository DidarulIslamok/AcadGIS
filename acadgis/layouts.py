"""Multi-panel study-area layout presets (templates), fully customizable.

One entry point, :func:`study_area`, builds a figure from a preset ``template``
(single, two, cascade, series, grid). Customizable: panel sizes
(``width_ratios``/``height_ratios``/``wspace``/``hspace``), uniform panel boxes
(``uniform_panels``), per-panel graticule on/off + interval, highlight style
(overlay / rect / circle) and colour, and the connectors (colour/width/style/box).
"""
from __future__ import annotations

import warnings
from typing import List, Optional, Sequence, Tuple, Union

# uniform_panels (adjustable='datalim') triggers a benign matplotlib notice
warnings.filterwarnings("ignore", message="Ignoring fixed .* limits to fulfill")

TEMPLATES = {"single": 1, "two": 2, "cascade": 3, "series": 3, "grid": 4}

_GEOMETRY = {
    "single": dict(width_ratios=None, height_ratios=None, wspace=0.10, hspace=0.10),
    "two":    dict(width_ratios=[1.0, 1.6], height_ratios=None, wspace=0.14, hspace=0.10),
    "series": dict(width_ratios=[1, 1, 1], height_ratios=None, wspace=0.16, hspace=0.10),
    "cascade": dict(width_ratios=[1.0, 1.7], height_ratios=[1, 1], wspace=0.16, hspace=0.20),
    "grid":   dict(width_ratios=[1, 1], height_ratios=[1, 1], wspace=0.16, hspace=0.18),
}

_LINKS = {
    "two": [(0, 1, ["tr", "br"], [(0, 1), (0, 0)])],
    "series": [(0, 1, ["tr", "br"], [(0, 1), (0, 0)]),
               (1, 2, ["tr", "br"], [(0, 1), (0, 0)])],
    "cascade": [(0, 1, ["bl", "br"], [(0, 1), (1, 1)]),
                (1, 2, ["tr", "br"], [(0, 1), (0, 0)])],
    "grid": [(0, 1, ["tr", "br"], [(0, 1), (0, 0)]),
             (0, 2, ["bl", "br"], [(0, 1), (1, 1)]),
             (1, 3, ["bl", "br"], [(0, 1), (1, 1)])],
}


def _per_panel(val, n, default):
    """Resolve a value that may be a scalar or a per-panel list."""
    if val is None:
        return [default] * n
    if isinstance(val, (list, tuple)):
        out = list(val)
        return (out + [default] * n)[:n]
    return [val] * n


def _apply_highlight(ax, region_gdf, *, style, color, edge, alpha, lw, pad=0.12):
    """Highlight a region with style 'overlay' (border+fill), 'rect' or 'circle'.
    Returns the region geometry (for connectors)."""
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Circle, Rectangle

    if region_gdf is None or len(region_gdf) == 0:
        return None
    geom = region_gdf.geometry.union_all()
    fc = to_rgba(color, alpha)
    minx, miny, maxx, maxy = geom.bounds
    if style == "circle":
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        r = max(maxx - minx, maxy - miny) / 2 * (1 + pad)
        ax.add_patch(Circle((cx, cy), r, facecolor=fc, edgecolor=edge,
                            linewidth=lw, zorder=8))
    elif style == "rect":
        dx, dy = (maxx - minx) * pad, (maxy - miny) * pad
        ax.add_patch(Rectangle((minx - dx, miny - dy), (maxx - minx) + 2 * dx,
                               (maxy - miny) + 2 * dy, facecolor=fc,
                               edgecolor=edge, linewidth=lw, zorder=8))
    else:  # overlay: translucent region fill + solid region border
        region_gdf.plot(ax=ax, color=color, alpha=alpha, edgecolor="none", zorder=7)
        region_gdf.plot(ax=ax, facecolor="none", edgecolor=edge, linewidth=lw, zorder=8)
    return geom


def _box_link(fig, src_ax, geom, dst_ax, *, color, lw, linestyle, box,
              src_pick, dst_corners, pad=0.18):
    from matplotlib.patches import ConnectionPatch, Rectangle

    minx, miny, maxx, maxy = geom.bounds
    dx, dy = (maxx - minx) * pad, (maxy - miny) * pad
    x0, y0 = minx - dx, miny - dy
    w, h = (maxx - minx) + 2 * dx, (maxy - miny) + 2 * dy
    if box:
        src_ax.add_patch(Rectangle((x0, y0), w, h, fill=False, edgecolor=color,
                                   linewidth=lw, linestyle=linestyle, zorder=50))
    corners = {"tl": (x0, y0 + h), "tr": (x0 + w, y0 + h),
               "bl": (x0, y0), "br": (x0 + w, y0)}
    for s, d in zip(src_pick, dst_corners):
        fig.add_artist(ConnectionPatch(xyA=corners[s], coordsA=src_ax.transData,
                                       xyB=d, coordsB=dst_ax.transAxes,
                                       color=color, lw=lw, linestyle=linestyle,
                                       zorder=50, clip_on=False))


def _axes_for(fig, template, geom):
    wr, hr = geom["width_ratios"], geom["height_ratios"]
    ws, hs = geom["wspace"], geom["hspace"]
    if template == "single":
        return [fig.add_subplot(1, 1, 1)]
    if template == "two":
        gs = fig.add_gridspec(1, 2, width_ratios=wr, wspace=ws)
        return [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    if template == "series":
        gs = fig.add_gridspec(1, 3, width_ratios=wr, wspace=ws)
        return [fig.add_subplot(gs[0, i]) for i in range(3)]
    if template == "cascade":
        gs = fig.add_gridspec(2, 2, width_ratios=wr, height_ratios=hr,
                              wspace=ws, hspace=hs)
        return [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0]),
                fig.add_subplot(gs[:, 1])]
    gs = fig.add_gridspec(2, 2, width_ratios=wr, height_ratios=hr,
                          wspace=ws, hspace=hs)
    return [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]),
            fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]


def study_area(country: str, steps: Optional[Sequence[Tuple[str, str]]] = None, *,
               template: str = "cascade", terrain: bool = False,
               # highlight
               highlight_style: str = "overlay", highlight_color: str = "#d6263b",
               highlight_edge: Optional[str] = None, highlight_alpha: float = 0.30,
               highlight_width: float = 2.0,
               # connectors
               links: bool = True, link_color: Optional[str] = None,
               link_width: float = 1.6, link_style: str = "-", box: bool = True,
               # graticule (per-panel: scalar or list)
               graticule=True, graticule_interval=None,
               north_arrow=True, scale_bar=True,
               # sizing
               uniform_panels: bool = True, width_ratios=None, height_ratios=None,
               wspace=None, hspace=None, figsize=None,
               # colours
               palette: str = "spectral", detail_palette: str = "pastel",
               cmap: str = "terrain", suptitle: Optional[str] = None,
               download: bool = True):
    """Build a multi-panel study-area figure from a preset ``template``.

    Highlight ``highlight_style`` ∈ {overlay, rect, circle}. ``graticule`` and
    ``graticule_interval`` (and ``north_arrow``/``scale_bar``) accept a scalar
    (all panels) or a per-panel list. ``uniform_panels=True`` keeps panel boxes
    the same size (no shrink-to-aspect). See module docstring for the rest.
    """
    import matplotlib.pyplot as plt

    from . import decorations as deco
    from . import relief
    from .core import plot as _plot
    from .data import load_boundaries, name_column
    from .matching import match_one

    steps = [tuple(s) for s in (steps or [])]
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template {template!r}. Options: {list(TEMPLATES)}")
    link_color = link_color or highlight_color
    highlight_edge = highlight_edge or highlight_color

    geom = dict(_GEOMETRY[template])
    for k, v in (("width_ratios", width_ratios), ("height_ratios", height_ratios),
                 ("wspace", wspace), ("hspace", hspace)):
        if v is not None:
            geom[k] = v

    # context panels + deepest-region detail
    context = []
    for i, (lvl, name) in enumerate(steps):
        parent = None if i == 0 else steps[i - 1][1]
        gdf = load_boundaries(country, lvl, within=parent, download=download)
        col = name_column(gdf)
        m, _ = match_one(name, gdf[col].tolist())
        title = country if i == 0 else steps[i - 1][1]
        context.append((gdf, m, title))

    detail_gdf = detail_title = None
    if steps:
        lvl, name = steps[-1]
        within = steps[-2][1] if len(steps) > 1 else None
        deep = load_boundaries(country, lvl, within=within, download=download)
        col = name_column(deep)
        m, _ = match_one(name, deep[col].tolist())
        detail_gdf = deep[deep[col] == m]
        detail_title = m

    if template == "single":
        order = [("detail",)]
    elif template == "grid" and len(steps) == 2 and terrain:
        order = [("ctx", 0), ("ctx", 1), ("detail_poly",), ("detail",)]
    else:
        order = [("ctx", i) for i in range(len(context))] + [("detail",)]

    need = TEMPLATES[template]
    if len(order) != need:
        raise ValueError(
            f"template {template!r} needs {need} panels but the chain produced "
            f"{len(order)}.")

    n = len(order)
    g_list = _per_panel(graticule, n, True)
    gi_list = _per_panel(graticule_interval, n, None)
    na_list = _per_panel(north_arrow, n, True)
    sb_list = _per_panel(scale_bar, n, True)

    figsize = figsize or {"single": (8, 8), "two": (15, 7), "series": (18, 6.5),
                          "cascade": (16, 9), "grid": (14, 12)}[template]
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor("white")
    axes = _axes_for(fig, template, geom)

    def finish(ax, i, context_panel):
        if g_list[i]:
            deco.graticule(ax, interval=gi_list[i], color="#9aa0a6", lw=0.5,
                           alpha=0.55, fontsize=8, label_color="#333333")
        else:
            ax.set_xticks([]); ax.set_yticks([])
        if context_panel and uniform_panels:
            ax.set_adjustable("datalim")   # keep panel box full-size (no shrink)

    panel_geom = {}
    for i, (ax, spec) in enumerate(zip(axes, order)):
        if spec[0] == "ctx":
            gdf, hl_name, title = context[spec[1]]
            _plot(gdf, ax=ax, palette=palette, labels=False, title=title.upper(),
                  graticule=False, north_arrow=na_list[i], scale_bar=sb_list[i])
            panel_geom[i] = _apply_highlight(
                ax, gdf[gdf[name_column(gdf)] == hl_name], style=highlight_style,
                color=highlight_color, edge=highlight_edge, alpha=highlight_alpha,
                lw=highlight_width)
            finish(ax, i, True)
        elif spec[0] == "detail_poly":
            _plot(detail_gdf, ax=ax, palette=detail_palette, labels=False,
                  title=detail_title.upper(), graticule=False,
                  north_arrow=na_list[i], scale_bar=sb_list[i])
            finish(ax, i, True)
        else:
            if terrain:
                from . import load_dem
                dem = load_dem(detail_gdf, max_size=1000, download=download)
                relief(dem, ax=ax, cmap=cmap, hillshade=True,
                       title=detail_title.upper(), legend_label="Elevation (m)",
                       graticule=False, north_arrow=na_list[i], scale_bar=sb_list[i])
            else:
                _plot(detail_gdf, ax=ax, palette=detail_palette, labels=False,
                      title=detail_title.upper(), graticule=False,
                      north_arrow=na_list[i], scale_bar=sb_list[i])
            finish(ax, i, False)

    if links and template in _LINKS:
        for (a, b, src_pick, dst_corners) in _LINKS[template]:
            if a < len(axes) and b < len(axes) and panel_geom.get(a) is not None:
                _box_link(fig, axes[a], panel_geom[a], axes[b], color=link_color,
                          lw=link_width, linestyle=link_style, box=box,
                          src_pick=src_pick, dst_corners=dst_corners)

    if suptitle:
        fig.suptitle(suptitle, fontsize=15, fontweight="bold", y=0.98)
    fig.panels = list(axes)
    return fig
