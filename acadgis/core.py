"""Core single-panel plotting: :func:`plot` and :func:`choropleth`.

These turn a GeoDataFrame into a styled, decorated study-area map that shares
the look of the AcadGIS web app.
"""
from __future__ import annotations

from typing import Optional, Sequence, Union

import geopandas as gpd
import numpy as np
import pandas as pd

from . import decorations as deco
from . import palettes as pal
from .data import name_column
from .matching import match_one, normalize
from .themes import Theme, get_theme


# --------------------------------------------------------------------------- #
# shared axes setup
# --------------------------------------------------------------------------- #
def _new_ax(figsize, theme: Theme):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(theme.background)
    ax.set_facecolor(theme.background)
    return fig, ax


def _apply_extent(ax, gdf, pad=0.05):
    minx, miny, maxx, maxy = gdf.total_bounds
    dx = (maxx - minx) or 1.0
    dy = (maxy - miny) or 1.0
    ax.set_xlim(minx - dx * pad, maxx + dx * pad)
    ax.set_ylim(miny - dy * pad, maxy + dy * pad)
    # geographic aspect at mean latitude
    mean_lat = (miny + maxy) / 2.0
    ax.set_aspect(1.0 / max(np.cos(np.radians(mean_lat)), 1e-6))


def _opts(val):
    """Normalize a decoration arg (bool | str-style | dict) to kwargs or None.

    ``False``/``None`` -> disabled; ``True`` -> defaults; ``"rose"`` ->
    ``{'style': 'rose'}``; a dict passes through.
    """
    if val is False or val is None:
        return None
    if val is True:
        return {}
    if isinstance(val, str):
        return {"style": val}
    if isinstance(val, dict):
        return dict(val)
    return {}


def _decorate(ax, gdf, theme, *, title, north_arrow, scale_bar, graticule,
              border="solid"):
    if graticule:
        gkw = dict(color=theme.grid_color, lw=theme.grid_width,
                   alpha=theme.grid_alpha, fontsize=theme.label_size,
                   label_color=theme.label_color)
        if isinstance(graticule, dict):   # plot(graticule={...}) -> full control
            gkw.update(graticule)
        deco.graticule(ax, **gkw)
    else:
        ax.set_xticks([])
        ax.set_yticks([])

    na = _opts(north_arrow)
    if na is not None:
        na.setdefault("color", theme.decoration_color)
        deco.north_arrow(ax, **na)

    sb = _opts(scale_bar)
    if sb is not None:
        sb.setdefault("color", theme.decoration_color)
        sb.setdefault("fontsize", theme.label_size)
        deco.scale_bar(ax, **sb)

    bd = _opts(border if border is not None else "solid")
    if bd is not None:
        bd.setdefault("color", theme.edge_color)
        deco.map_border(ax, **bd)

    if title:
        ax.set_title(title, fontsize=theme.title_size,
                     fontweight=theme.title_weight, pad=12)


def _label_regions(ax, gdf, col, *, fontsize=7, color="#222222"):
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        pt = geom.representative_point()
        ax.annotate(str(row[col]), (pt.x, pt.y), ha="center", va="center",
                    fontsize=fontsize, color=color, zorder=15,
                    path_effects=_halo())


def _halo(width=2, color="white"):
    import matplotlib.patheffects as pe

    return [pe.withStroke(linewidth=width, foreground=color)]


def points(
    ax,
    data,
    *,
    lon="lon",
    lat="lat",
    label=None,
    value=None,
    color="#222222",
    cmap="viridis",
    size=25,
    size_by=None,
    size_range=(15, 220),
    marker="o",
    edgecolor="white",
    linewidth=0.6,
    fontsize=7,
    text_color=None,
    dx=0.0,
    dy=0.0,
    halo=True,
    legend=False,
    legend_label=None,
    zorder=12,
):
    """Overlay point markers (study sites, sampling locations, capitals).

    ``data`` may be a DataFrame (``lon``/``lat`` columns, optional ``label``),
    a ``{name: (lon, lat)}`` dict, or a list of ``(lon, lat)`` tuples.

    For *collected data*, pass ``value=`` (a column name or array) to colour
    markers by value (graduated symbols, with an optional ``legend`` colorbar),
    and/or ``size_by=`` to scale marker area by value (proportional symbols).
    Returns the Axes.
    """
    import numpy as np

    xs, ys, labels = [], [], []
    vals = None
    if isinstance(data, dict):
        for name, (x, y) in data.items():
            xs.append(x); ys.append(y); labels.append(str(name))
    elif hasattr(data, "columns"):  # DataFrame
        xs = list(data[lon]); ys = list(data[lat])
        if label and label in data.columns:
            labels = [str(v) for v in data[label]]
        if value is not None and value in data.columns:
            vals = np.asarray(data[value], dtype=float)
    else:  # iterable of (lon, lat)
        for x, y in data:
            xs.append(x); ys.append(y); labels.append("")

    if value is not None and not isinstance(value, str):
        vals = np.asarray(value, dtype=float)

    # marker sizes (proportional symbols)
    sizes = size
    if size_by is not None:
        sb = (np.asarray(data[size_by], dtype=float)
              if (hasattr(data, "columns") and isinstance(size_by, str))
              else np.asarray(size_by, dtype=float))
        lo, hi = np.nanmin(sb), np.nanmax(sb)
        rng = (hi - lo) or 1
        sizes = size_range[0] + (size_range[1] - size_range[0]) * (sb - lo) / rng

    if vals is not None:  # colour by value
        sc = ax.scatter(xs, ys, s=sizes, c=vals, cmap=cmap, marker=marker,
                        edgecolor=edgecolor, linewidth=linewidth,
                        zorder=zorder, clip_on=True)
        if legend:
            cb = ax.figure.colorbar(sc, ax=ax, shrink=0.55, pad=0.02)
            cb.set_label(legend_label or (value if isinstance(value, str)
                                          else "value"))
    else:
        ax.scatter(xs, ys, s=sizes, c=color, marker=marker,
                   edgecolor=edgecolor, linewidth=linewidth, zorder=zorder,
                   clip_on=True)

    if labels and any(labels):
        tc = text_color or color
        pe = _halo() if halo else None
        for x, y, lab in zip(xs, ys, labels):
            if not lab:
                continue
            ax.annotate(lab, (x + dx, y + dy), fontsize=fontsize, color=tc,
                        ha="center", va="bottom", zorder=zorder + 2,
                        path_effects=pe, clip_on=True)
    return ax


# --------------------------------------------------------------------------- #
# plot: categorical / per-region styled map
# --------------------------------------------------------------------------- #
def plot(
    gdf: gpd.GeoDataFrame,
    *,
    column: Optional[str] = None,
    palette: Optional[str] = None,
    theme: Union[str, Theme] = "academic",
    ax=None,
    title: Optional[str] = None,
    highlight: Optional[Union[str, Sequence[str]]] = None,
    labels: bool = False,
    legend: bool = False,
    north_arrow=True,
    scale_bar=True,
    graticule: bool = True,
    border="solid",
    figsize=(8, 8),
    pad: float = 0.05,
):
    """Plot a styled administrative map.

    Without ``column`` each region gets its own palette colour (the qualitative
    'atlas' look of the reference figure). With a categorical ``column`` regions
    are coloured by category. Use :func:`choropleth` for numeric data.

    Decoration arguments (``north_arrow``, ``scale_bar``, ``border``) accept:
    ``True``/``False`` (on/off with defaults), a style string (e.g.
    ``north_arrow="rose"``), or a dict of options for full control, e.g.::

        north_arrow={"style": "rose", "size": 0.15, "color": "#1b4332",
                     "loc": (0.9, 0.85)}
        scale_bar={"style": "stepped", "length_km": 100, "loc": (0.07, 0.05)}
        border={"style": "checker", "checker_size": 0.04, "color": "#2a2a2a"}
    """
    th = get_theme(theme)
    if palette:
        th = th.with_(palette=palette)

    if ax is None:
        fig, ax = _new_ax(figsize, th)
    else:
        fig = ax.figure

    name_col = name_column(gdf)

    # decide colors
    if column and column in gdf.columns:
        cats = gdf[column].astype("category")
        codes = cats.cat.codes
        colors_list = pal.get_colors(th.palette, len(cats.cat.categories))
        face = [colors_list[c % len(colors_list)] for c in codes]
        legend_labels = list(cats.cat.categories)
        legend_colors = colors_list
    else:
        n = len(gdf)
        colors_list = pal.get_colors(th.palette, n)
        face = colors_list
        legend_labels = gdf[name_col].tolist()
        legend_colors = colors_list

    gdf = gdf.copy()
    gdf["_face"] = face
    gdf.plot(ax=ax, color=gdf["_face"], edgecolor=th.edge_color,
             linewidth=th.edge_width, alpha=th.fill_alpha, zorder=5)

    # highlight selected regions
    if highlight is not None:
        names = [highlight] if isinstance(highlight, str) else list(highlight)
        avail = gdf[name_col].tolist()
        sel = []
        for nm in names:
            m, _ = match_one(nm, avail)
            if m is not None:
                sel.append(m)
        if sel:
            sub = gdf[gdf[name_col].isin(sel)]
            sub.plot(ax=ax, color=th.highlight_color,
                     edgecolor=th.highlight_edge, linewidth=th.highlight_width,
                     zorder=6)

    _apply_extent(ax, gdf, pad=pad)
    _decorate(ax, gdf, th, title=title, north_arrow=north_arrow,
              scale_bar=scale_bar, graticule=graticule, border=border)

    if labels:
        _label_regions(ax, gdf, name_col, fontsize=th.label_size - 1,
                       color=th.label_color)
    if legend:
        deco.categorical_legend(ax, legend_labels, legend_colors,
                                fontsize=th.label_size)
    return ax


# --------------------------------------------------------------------------- #
# choropleth: numeric data join + color ramp
# --------------------------------------------------------------------------- #
def choropleth(
    gdf: gpd.GeoDataFrame,
    data: Union[pd.DataFrame, dict],
    *,
    on: Optional[str] = None,
    value: Optional[str] = None,
    key: Optional[str] = None,
    palette: str = "viridis",
    theme: Union[str, Theme] = "academic",
    ax=None,
    title: Optional[str] = None,
    scheme: Optional[str] = None,
    k: int = 5,
    legend: bool = True,
    legend_label: Optional[str] = None,
    labels: bool = False,
    north_arrow=True,
    scale_bar=True,
    graticule: bool = True,
    border="solid",
    figsize=(8, 8),
    pad: float = 0.05,
    missing_color: str = "#dddddd",
    match_threshold: float = 80.0,
):
    """Join a data table to boundaries by name and draw a choropleth.

    Parameters
    ----------
    data:
        A DataFrame or ``{name: value}`` dict of values to map.
    on:
        Boundary name column to join on (defaults to the deepest NAME_*).
    value:
        Column in ``data`` holding the numeric value (required for DataFrame).
    key:
        Column in ``data`` holding region names (defaults to first column).
    scheme:
        Optional mapclassify scheme name ('quantiles', 'equal_interval',
        'natural_breaks', 'fisher_jenks' …). If None, a continuous ramp.
    """
    th = get_theme(theme)
    name_col = on or name_column(gdf)

    # normalise the input data into a {region: value} dict
    if isinstance(data, dict):
        raw = dict(data)
    else:
        df = data.copy()
        if value is None:
            num_cols = df.select_dtypes("number").columns.tolist()
            if not num_cols:
                raise ValueError("No numeric column found in data; pass value=")
            value = num_cols[0]
        if key is None:
            key = df.columns[0]
        raw = dict(zip(df[key], df[value]))

    # fuzzy-match data names to boundary names
    avail = gdf[name_col].tolist()
    joined = {}
    unmatched = []
    for nm, val in raw.items():
        m, score = match_one(nm, avail, threshold=match_threshold)
        if m is None:
            unmatched.append(nm)
        else:
            joined[m] = val
    if unmatched:
        import warnings

        warnings.warn(
            f"{len(unmatched)} name(s) could not be matched to boundaries: "
            f"{unmatched[:8]}" + (" ..." if len(unmatched) > 8 else ""),
            stacklevel=2,
        )

    gdf = gdf.copy()
    gdf["_value"] = gdf[name_col].map(joined).astype(float)

    if ax is None:
        fig, ax = _new_ax(figsize, th)

    cmap = pal.get_cmap(palette)
    plot_kwargs = dict(
        ax=ax, column="_value", cmap=cmap, edgecolor=th.edge_color,
        linewidth=th.edge_width, legend=legend, zorder=5,
        missing_kwds={"color": missing_color, "edgecolor": th.edge_color,
                      "label": "No data", "linewidth": th.edge_width},
    )
    if scheme:
        plot_kwargs.update(scheme=scheme, k=k)
    if legend:
        plot_kwargs["legend_kwds"] = {
            "label": legend_label or value or "value",
            "shrink": 0.6,
        } if not scheme else {"title": legend_label or value or "value",
                              "fontsize": th.label_size, "loc": "lower right"}

    gdf.plot(**plot_kwargs)

    _apply_extent(ax, gdf, pad=pad)
    _decorate(ax, gdf, th, title=title, north_arrow=north_arrow,
              scale_bar=scale_bar, graticule=graticule, border=border)
    if labels:
        _label_regions(ax, gdf, name_col, fontsize=th.label_size - 1,
                       color=th.label_color)
    return ax
