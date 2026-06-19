"""World-map helpers: highlight a country on a world map, with optional zoom.

Uses a bundled Natural Earth (110m) admin-0 layer so it works fully offline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import geopandas as gpd

from . import decorations as deco
from .core import _apply_extent, _new_ax
from .matching import match_one
from .themes import Theme, get_theme

_WORLD_FILE = Path(__file__).resolve().parent / "data" / "samples" / "world_adm0.geojson"


def load_world() -> gpd.GeoDataFrame:
    """Load bundled world country boundaries (Natural Earth 110m, EPSG:4326).

    Columns: ``NAME_0`` (country), ``GID_0`` (ISO-A3), ``CONTINENT``.
    """
    gdf = gpd.read_file(_WORLD_FILE)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf


def _resolve_country(world, country):
    matched, score = match_one(country, world["NAME_0"].tolist())
    if matched is None:
        raise ValueError(
            f"Country {country!r} not found on the world map. "
            f"Examples: {sorted(world['NAME_0'].tolist())[:8]} ..."
        )
    return matched


def highlight_country(
    country: str,
    *,
    world: Optional[gpd.GeoDataFrame] = None,
    color: Optional[str] = None,
    context_color: Optional[str] = None,
    ocean_color: str = "#eef4fb",
    theme: Union[str, Theme] = "academic",
    ax=None,
    title: Optional[str] = None,
    label: bool = True,
    graticule: bool = True,
    figsize=(13, 7),
):
    """Plot a world map with ``country`` filled in a highlight colour.

    Returns the matplotlib Axes.
    """
    th = get_theme(theme)
    color = color or th.highlight_color
    context_color = context_color or th.context_color

    world = load_world() if world is None else world
    matched = _resolve_country(world, country)

    if ax is None:
        _fig, ax = _new_ax(figsize, th)
    ax.set_facecolor(ocean_color)

    # all countries as muted context
    world.plot(ax=ax, color=context_color, edgecolor=th.edge_color,
               linewidth=0.3, zorder=2)
    # the chosen country highlighted
    target = world[world["NAME_0"] == matched]
    target.plot(ax=ax, color=color, edgecolor=th.highlight_edge,
                linewidth=0.8, zorder=3)

    # whole-world extent
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)
    ax.set_aspect(1.0)

    if graticule:
        deco.graticule(ax, color=th.grid_color, lw=th.grid_width,
                       alpha=th.grid_alpha, fontsize=th.label_size - 1,
                       label_color=th.label_color, n_lines=7)
    else:
        ax.set_xticks([])
        ax.set_yticks([])

    if label:
        c = target.geometry.representative_point().values[0]
        ax.annotate(matched, (c.x, c.y), xytext=(c.x + 12, c.y + 14),
                    textcoords="data", fontsize=th.label_size + 1,
                    fontweight="bold", color=th.highlight_edge,
                    arrowprops=dict(arrowstyle="->", color=th.highlight_edge,
                                    lw=1.2), zorder=10)

    ax.set_title(title or f"{matched} — location on the world map",
                 fontsize=th.title_size, fontweight=th.title_weight, pad=10)
    return ax


def world_locator(
    country: str,
    *,
    theme: Union[str, Theme] = "academic",
    color: Optional[str] = None,
    figsize=(15, 7),
    suptitle: Optional[str] = None,
    zoom_pad: float = 1.2,
):
    """Two-panel figure: world map (country marked) -> zoomed country.

    Returns the matplotlib Figure.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import ConnectionPatch

    th = get_theme(theme)
    color = color or th.highlight_color
    world = load_world()
    matched = _resolve_country(world, country)
    target = world[world["NAME_0"] == matched]

    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor(th.background)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.6, 1], wspace=0.12)

    ax_world = fig.add_subplot(gs[0, 0])
    highlight_country(matched, world=world, ax=ax_world, color=color,
                      theme=th, title="World", label=True)

    # zoom panel: the country + a little context
    ax_zoom = fig.add_subplot(gs[0, 1])
    ax_zoom.set_facecolor("#eef4fb")
    world.plot(ax=ax_zoom, color=th.context_color, edgecolor=th.edge_color,
               linewidth=0.3, zorder=2)
    target.plot(ax=ax_zoom, color=color, edgecolor=th.highlight_edge,
                linewidth=1.0, zorder=3)
    _apply_extent(ax_zoom, target, pad=zoom_pad)
    deco.graticule(ax_zoom, color=th.grid_color, lw=th.grid_width,
                   alpha=th.grid_alpha, fontsize=th.label_size - 1,
                   label_color=th.label_color, n_lines=4)
    deco.north_arrow(ax_zoom, color=th.decoration_color)
    ax_zoom.set_title(matched, fontsize=th.title_size - 1,
                      fontweight=th.title_weight, pad=8)

    # connecting arrow from country on the world map to the zoom panel
    c = target.geometry.representative_point().values[0]
    con = ConnectionPatch(
        xyA=(c.x, c.y), coordsA=ax_world.transData,
        xyB=(0, 0.5), coordsB=ax_zoom.transAxes,
        arrowstyle="-|>", color="#333333", lw=1.4, zorder=40,
    )
    fig.add_artist(con)

    if suptitle:
        fig.suptitle(suptitle, fontsize=th.title_size + 2,
                     fontweight="bold", y=0.99)
    return fig
