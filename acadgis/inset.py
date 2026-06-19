"""Multi-panel study-area / locator figures — the signature AcadGIS layout.

Recreates the classic "country  ->  highlighted region  ->  zoomed detail"
figure (e.g. Iraq -> Babylon governorate -> Hilla) with connecting arrows
between panels.
"""
from __future__ import annotations

from typing import List, Optional, Union

import numpy as np
from matplotlib.patches import ConnectionPatch

from . import decorations as deco
from . import palettes as pal
from .core import _apply_extent
from .data import load_boundaries, name_column, resolve_level
from .matching import match_one
from .themes import Theme, get_theme


def _panel(ax, gdf, theme: Theme, *, colors=None, highlight_geom=None,
           graticule=True, title=None, na=False, sb=False, labels=False,
           name_col=None, pad=0.06, n_lines=5, rotate_x=0):
    """Plot one map panel into ``ax``."""
    if colors is None:
        colors = pal.get_colors(theme.palette, len(gdf))
    g = gdf.copy()
    g["_face"] = [colors[i % len(colors)] for i in range(len(g))]
    g.plot(ax=ax, color=g["_face"], edgecolor=theme.edge_color,
           linewidth=theme.edge_width, zorder=5)

    if highlight_geom is not None:
        from geopandas import GeoSeries

        GeoSeries([highlight_geom], crs=gdf.crs).plot(
            ax=ax, facecolor="none", edgecolor=theme.highlight_edge,
            linewidth=theme.highlight_width + 0.6, zorder=8)

    _apply_extent(ax, gdf, pad=pad)
    if graticule:
        deco.graticule(ax, color=theme.grid_color, lw=theme.grid_width,
                       alpha=theme.grid_alpha, fontsize=theme.label_size - 1,
                       label_color=theme.label_color, n_lines=n_lines,
                       rotate_x=rotate_x)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    if na:
        deco.north_arrow(ax, color=theme.decoration_color, style="classic")
    if sb:
        deco.scale_bar(ax, color=theme.decoration_color,
                       fontsize=theme.label_size - 1)
    if labels and name_col:
        for _, row in g.iterrows():
            if row.geometry is None or row.geometry.is_empty:
                continue
            p = row.geometry.representative_point()
            ax.annotate(str(row[name_col]), (p.x, p.y), ha="center",
                        va="center", fontsize=theme.label_size - 2,
                        zorder=15)
    if title:
        ax.set_title(title, fontsize=theme.title_size - 1,
                     fontweight=theme.title_weight, pad=6)
    return ax


class StudyArea:
    """Build a multi-panel study-area figure for a country.

    Example
    -------
    >>> sa = StudyArea("Iraq").zoom_into("Babil")
    >>> fig = sa.figure()
    >>> sa.save("study_area.png", dpi=300)
    """

    def __init__(self, country: str, *, theme: Union[str, Theme] = "atlas",
                 context_level: Union[str, int] = "state", download: bool = True):
        self.country = country
        self.theme = get_theme(theme)
        self.download = download
        self.context_level = resolve_level(context_level)

        self.country_gdf = load_boundaries(country, 0, download=download)
        self.context_gdf = load_boundaries(country, self.context_level,
                                           download=download)
        self._focus_name: Optional[str] = None
        self._focus_matched: Optional[str] = None
        self._detail_level: Optional[int] = None
        self._detail_gdf = None

    # ------------------------------------------------------------------ #
    def zoom_into(self, region: str, *, detail_level: Optional[Union[str, int]] = None):
        """Choose the region to highlight & zoom into.

        ``detail_level`` optionally adds a third panel showing that region's
        sub-divisions (e.g. districts within a division).
        """
        col = name_column(self.context_gdf, self.context_level)
        matched, score = match_one(region, self.context_gdf[col].tolist())
        if matched is None:
            raise ValueError(
                f"Region {region!r} not found among {self.country} "
                f"level-{self.context_level} regions. Options: "
                f"{sorted(self.context_gdf[col].tolist())[:12]} ..."
            )
        self._focus_name = region
        self._focus_matched = matched

        if detail_level is not None:
            lvl = resolve_level(detail_level)
            self._detail_level = lvl
            try:
                self._detail_gdf = load_boundaries(
                    self.country, lvl, within=matched, download=self.download)
            except Exception:
                self._detail_gdf = None
        return self

    # ------------------------------------------------------------------ #
    def _focus_geom(self):
        col = name_column(self.context_gdf, self.context_level)
        row = self.context_gdf[self.context_gdf[col] == self._focus_matched]
        return row.geometry.values[0], row

    def figure(self, *, figsize=(14, 8), suptitle: Optional[str] = None,
               arrows: bool = True):
        """Render the figure and return the matplotlib Figure."""
        import matplotlib.pyplot as plt

        th = self.theme
        ncol_ctx = len(self.context_gdf)
        ctx_colors = pal.get_colors(th.palette, ncol_ctx)
        ctx_col = name_column(self.context_gdf, self.context_level)

        has_detail = self._detail_gdf is not None and len(self._detail_gdf) > 0
        focus_geom = row = None
        if self._focus_matched is not None:
            focus_geom, row = self._focus_geom()

        fig = plt.figure(figsize=figsize)
        fig.patch.set_facecolor(th.background)

        if focus_geom is None:
            # just the country context
            ax = fig.add_subplot(111)
            _panel(ax, self.context_gdf, th, colors=ctx_colors,
                   graticule=True, na=True, sb=True, labels=True,
                   name_col=ctx_col, title=self.country)
            if suptitle:
                fig.suptitle(suptitle, fontsize=th.title_size + 2,
                             fontweight="bold")
            self._fig = fig
            return fig

        # layout: overview (left) + 1-2 detail panels (right)
        n_right = 2 if has_detail else 1
        gs = fig.add_gridspec(n_right, 2, width_ratios=[1.25, 1],
                              wspace=0.18, hspace=0.22)
        ax_main = fig.add_subplot(gs[:, 0])

        # overview panel: whole country context, focus outlined
        _panel(ax_main, self.context_gdf, th, colors=ctx_colors,
               highlight_geom=focus_geom, graticule=True, na=True, sb=True,
               name_col=ctx_col, title=f"{self.country}")

        # detail panel 1: the focus region itself
        ax_focus = fig.add_subplot(gs[0, 1])
        if has_detail:
            dcol = name_column(self._detail_gdf, self._detail_level)
            d_colors = pal.get_colors(th.palette, len(self._detail_gdf))
            _panel(ax_focus, self._detail_gdf, th, colors=d_colors,
                   graticule=True, sb=True, labels=True, name_col=dcol,
                   title=f"{self._focus_matched}", n_lines=3, rotate_x=45)
        else:
            _panel(ax_focus, row, th,
                   colors=[th.highlight_color], graticule=True, sb=True,
                   title=f"{self._focus_matched}", n_lines=3, rotate_x=45)

        # optional 2nd detail panel: just the focus shape (silhouette)
        ax_sil = None
        if has_detail:
            ax_sil = fig.add_subplot(gs[1, 1])
            _panel(ax_sil, row, th, colors=[th.highlight_color],
                   graticule=False, title=f"{self._focus_matched} (extent)")

        # connecting arrows between focus region and detail panel(s)
        if arrows and focus_geom is not None:
            cpt = focus_geom.representative_point()
            con = ConnectionPatch(
                xyA=(cpt.x, cpt.y), coordsA=ax_main.transData,
                xyB=(0, 0.5), coordsB=ax_focus.transAxes,
                arrowstyle="-|>", linewidth=1.4, color="#333333",
                shrinkA=2, shrinkB=2, zorder=40,
            )
            fig.add_artist(con)
            if ax_sil is not None:
                con2 = ConnectionPatch(
                    xyA=(0.5, 0), coordsA=ax_focus.transAxes,
                    xyB=(0.5, 1), coordsB=ax_sil.transAxes,
                    arrowstyle="-|>", linewidth=1.4, color="#333333",
                    zorder=40,
                )
                fig.add_artist(con2)

        if suptitle:
            fig.suptitle(suptitle, fontsize=th.title_size + 2,
                         fontweight="bold", y=0.98)
        self._fig = fig
        return fig

    # ------------------------------------------------------------------ #
    def save(self, path, *, dpi: int = 300, **kwargs):
        """Save the (already-built or freshly-built) figure to ``path``."""
        fig = getattr(self, "_fig", None) or self.figure()
        fig.savefig(path, dpi=dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), **kwargs)
        return path
