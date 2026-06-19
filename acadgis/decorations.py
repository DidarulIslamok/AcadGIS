"""Cartographic decorations: north arrow, scale bar, graticule, border, legend.

Drawn on a matplotlib Axes showing geographic data in EPSG:4326. The north
arrow and scale-bar styles mirror the AcadGIS web app, and every element is
customizable: ``style``, ``size``, ``color`` and ``loc`` (position in
axes-fraction coordinates, 0–1).
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle

# Web-app defaults
NORTH_ARROW_STYLES = ("classic", "minimal", "pointer", "rose")
SCALE_BAR_STYLES = ("simple", "bar", "stepped")
BORDER_STYLES = ("solid", "checker", "none")
_DEFAULT_ARROW_COLOR = "#1b4332"
_DEFAULT_SCALE_COLOR = "#444444"
_DEFAULT_BORDER_COLOR = "#2a2a2a"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _aspect_ratio(ax) -> float:
    """Display height/width ratio of the axes box, so shapes stay undistorted.

    Equals ``data_aspect * (yrange / xrange)`` for a box-adjusted geographic
    axes — independent of dpi and figure size.
    """
    asp = ax.get_aspect()
    try:
        asp = float(asp)
    except (TypeError, ValueError):
        asp = 1.0
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    dx = abs(x1 - x0) or 1.0
    dy = abs(y1 - y0) or 1.0
    return asp * (dy / dx)


def _nice_number(value: float) -> float:
    if value <= 0:
        return 1.0
    exp = math.floor(math.log10(value))
    base = value / (10 ** exp)
    nice = 5 if base >= 5 else 2 if base >= 2 else 1
    return nice * (10 ** exp)


def _km_per_degree_lon(lat_deg: float) -> float:
    return 111.320 * math.cos(math.radians(lat_deg))


# --------------------------------------------------------------------------- #
# North arrow — 4 styles ported from the web app (SVG y negated -> matplotlib)
# --------------------------------------------------------------------------- #
# Shapes are normalized (divided by ~40) so `size` ~= fraction of axes height.
_ARROW_SHAPES = {
    "classic": {
        "polys": [
            # (vertices, facecolor_key, alpha, edge)
            ([(0, 13), (5, -2), (0, 2), (-5, -2)], "color", 1.0, "white"),
            ([(0, 2), (5, -2), (0, -11), (-5, -2)], "color", 0.6, "white"),
        ],
        "n_xy": (0, -21), "n_size": 0.9,
    },
    "minimal": {
        "polys": [
            ([(0, 15), (6, -5), (0, 0), (-6, -5)], "color", 1.0, None),
        ],
        "n_xy": (0, -16), "n_size": 1.0,
    },
    "pointer": {
        "polys": [
            ([(0, 18), (4, 0), (0, -18), (-4, 0)], "color", 1.0, "white"),
            ([(0, 18), (0, -18), (4, 0)], "shadow", 0.2, None),
        ],
        "n_xy": (0, 22), "n_size": 0.8,
    },
    "rose": {
        "polys": [
            ([(0, 20), (4, 4), (20, 0), (4, -4), (0, -20),
              (-4, -4), (-20, 0), (-4, 4)], "color", 1.0, "white"),
            ([(0, 20), (0, 0), (4, 4)], "shadow", 0.2, None),
            ([(20, 0), (0, 0), (4, -4)], "shadow", 0.2, None),
            ([(0, -20), (0, 0), (-4, -4)], "shadow", 0.2, None),
            ([(-20, 0), (0, 0), (-4, 4)], "shadow", 0.2, None),
        ],
        "n_xy": (0, 24), "n_size": 0.9,
    },
}


def north_arrow(ax, *, loc=(0.92, 0.88), size=0.12, style="classic",
                color=_DEFAULT_ARROW_COLOR, label="N"):
    """Draw a north arrow centered at ``loc`` (axes fraction).

    ``size`` is roughly the arrow height as a fraction of the axes height.
    ``style`` ∈ {classic, minimal, pointer, rose}.
    """
    style = (style or "classic").lower()
    spec = _ARROW_SHAPES.get(style, _ARROW_SHAPES["classic"])
    fx, fy = loc
    r = _aspect_ratio(ax)
    s = size / 40.0  # shapes were defined in ~±20 units
    colors = {"color": color, "shadow": "black"}

    for verts, ckey, alpha, edge in spec["polys"]:
        pts = [(fx + vx * s * r, fy + vy * s) for vx, vy in verts]
        ax.add_patch(Polygon(
            pts, closed=True, transform=ax.transAxes, clip_on=False,
            facecolor=colors[ckey], alpha=alpha,
            edgecolor=(edge or "none"),
            linewidth=0.6 if edge else 0.0, zorder=21))

    nx, ny = spec["n_xy"]
    ax.text(fx + nx * s * r, fy + ny * s, label, transform=ax.transAxes,
            ha="center", va="center", color=color, clip_on=False,
            fontsize=max(6.0, 90 * size * spec["n_size"]),
            fontweight="bold", zorder=22)


# --------------------------------------------------------------------------- #
# Scale bar — 3 styles ported from the web app
# --------------------------------------------------------------------------- #
def scale_bar(ax, *, loc=(0.07, 0.07), length_km=None, style="bar",
              color=_DEFAULT_SCALE_COLOR, size=1.0, height=0.014,
              units="km", fontsize=None):
    """Draw a scale bar sized in real distance.

    ``style`` ∈ {simple, bar, stepped}; ``loc`` is the bar's left end in axes
    fraction; ``size`` scales bar length & label; ``units`` ∈ {km, mi}.
    """
    style = (style or "bar").lower()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    mid_lat = (y0 + y1) / 2.0
    span_km = (x1 - x0) * _km_per_degree_lon(mid_lat)

    if length_km is None:
        length_km = _nice_number(span_km * 0.25)
    bar_deg = (length_km / _km_per_degree_lon(mid_lat)) * size

    bx = x0 + loc[0] * (x1 - x0)
    by = y0 + loc[1] * (y1 - y0)
    bh = height * (y1 - y0) * size
    fs = fontsize or (8 * size)

    label_val = length_km if units == "km" else length_km / 1.609344
    label = f"{label_val:g} {units}"

    if style == "simple":
        # T-shape: horizontal line with up-ticks at both ends
        ax.add_line(Line2D([bx, bx + bar_deg], [by, by], color=color,
                           lw=1.2 * size, zorder=21, clip_on=False))
        for xx in (bx, bx + bar_deg):
            ax.add_line(Line2D([xx, xx], [by, by + bh], color=color,
                               lw=1.2 * size, zorder=21, clip_on=False))
        ax.text(bx + bar_deg / 2, by + bh * 1.4, label, ha="center",
                va="bottom", fontsize=fs, color=color, family="monospace",
                fontweight="bold", zorder=21, clip_on=False)
    elif style == "stepped":
        seg = bar_deg / 4.0
        for i in range(4):
            fc = color if i % 2 == 0 else "white"
            ax.add_patch(Rectangle((bx + i * seg, by), seg, bh, facecolor=fc,
                                   edgecolor=color, lw=0.5 * size, zorder=21,
                                   clip_on=False))
        ax.text(bx + bar_deg, by + bh * 1.4, label, ha="right", va="bottom",
                fontsize=fs, color=color, family="monospace",
                fontweight="bold", zorder=21, clip_on=False)
    else:  # 'bar' — outline + left half filled
        ax.add_patch(Rectangle((bx, by), bar_deg, bh, facecolor="white",
                               edgecolor=color, lw=1.0 * size, zorder=21,
                               clip_on=False))
        ax.add_patch(Rectangle((bx, by), bar_deg / 2, bh, facecolor=color,
                               edgecolor="none", zorder=21, clip_on=False))
        ax.text(bx + bar_deg, by + bh * 1.4, label, ha="right", va="bottom",
                fontsize=fs, color=color, family="monospace",
                fontweight="bold", zorder=21, clip_on=False)


# --------------------------------------------------------------------------- #
# Border / frame — solid, checker (zebra), none
# --------------------------------------------------------------------------- #
def map_border(ax, *, style="solid", color=_DEFAULT_BORDER_COLOR, width=1.2,
               checker_size=0.05, thickness=0.018):
    """Draw a map frame border.

    ``style`` ∈ {solid, checker, none}. For 'checker', ``checker_size`` is the
    block length and ``thickness`` the strip depth (both axes fractions).
    """
    style = (style or "solid").lower()
    if style == "none":
        for sp in ax.spines.values():
            sp.set_visible(False)
        return
    if style == "solid":
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_edgecolor(color)
            sp.set_linewidth(width)
        return

    # checker / zebra: alternating blocks hugging the 4 edges (outside)
    for sp in ax.spines.values():
        sp.set_edgecolor(color)
        sp.set_linewidth(0.6)
    r = _aspect_ratio(ax)
    t_y = thickness            # vertical strip depth (top/bottom), in y-fraction
    t_x = thickness * r        # horizontal strip depth (left/right), undistort
    bx = checker_size          # block length along x edges (top/bottom)
    by = checker_size * r      # block length along y edges (left/right)

    n_h = max(1, int(round(1.0 / bx)))
    n_v = max(1, int(round(1.0 / by)))
    sx, sy = 1.0 / n_h, 1.0 / n_v
    tr = ax.transAxes

    for i in range(n_h):
        fc = color if i % 2 == 0 else "white"
        ax.add_patch(Rectangle((i * sx, 1.0), sx, t_y, transform=tr,
                               facecolor=fc, edgecolor=color, lw=0.4,
                               clip_on=False, zorder=25))   # top
        ax.add_patch(Rectangle((i * sx, -t_y), sx, t_y, transform=tr,
                               facecolor=fc, edgecolor=color, lw=0.4,
                               clip_on=False, zorder=25))   # bottom
    for i in range(n_v):
        fc = color if i % 2 == 0 else "white"
        ax.add_patch(Rectangle((-t_x, i * sy), t_x, sy, transform=tr,
                               facecolor=fc, edgecolor=color, lw=0.4,
                               clip_on=False, zorder=25))   # left
        ax.add_patch(Rectangle((1.0, i * sy), t_x, sy, transform=tr,
                               facecolor=fc, edgecolor=color, lw=0.4,
                               clip_on=False, zorder=25))   # right


# --------------------------------------------------------------------------- #
# Graticule (lat/lon grid + degree labels)
# --------------------------------------------------------------------------- #
def _fmt_deg(value: float, axis: str) -> str:
    suffix = ("E" if value >= 0 else "W") if axis == "x" else (
        "N" if value >= 0 else "S")
    v = abs(value)
    return f"{int(v)}°{suffix}" if v == int(v) else f"{v:g}°{suffix}"


def _nice_interval(span: float, target_lines: int = 5) -> float:
    raw = span / max(target_lines, 1)
    return _nice_number(raw) if raw > 0 else 1.0


def graticule(ax, *, interval=None, color="#888888", lw=0.5, alpha=0.6,
              labels=True, fontsize=8, label_color="#333333", n_lines=5,
              rotate_x=0):
    """Draw a latitude/longitude graticule with degree labels."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    xi = interval or _nice_interval(x1 - x0, n_lines)
    yi = interval or _nice_interval(y1 - y0, n_lines)

    xticks = np.arange(math.ceil(x0 / xi) * xi, x1, xi)
    yticks = np.arange(math.ceil(y0 / yi) * yi, y1, yi)

    for xt in xticks:
        ax.axvline(xt, color=color, lw=lw, alpha=alpha, zorder=1)
    for yt in yticks:
        ax.axhline(yt, color=color, lw=lw, alpha=alpha, zorder=1)

    if labels:
        ax.set_xticks(xticks)
        ax.set_yticks(yticks)
        ax.set_xticklabels([_fmt_deg(t, "x") for t in xticks],
                           fontsize=fontsize, color=label_color,
                           rotation=rotate_x,
                           ha="right" if rotate_x else "center")
        ax.set_yticklabels([_fmt_deg(t, "y") for t in yticks],
                           fontsize=fontsize, color=label_color)
        ax.tick_params(length=3, color=color)
        for spine in ax.spines.values():
            spine.set_edgecolor("#333333")
            spine.set_linewidth(0.8)
    else:
        ax.set_xticks([])
        ax.set_yticks([])


# --------------------------------------------------------------------------- #
# Legend
# --------------------------------------------------------------------------- #
def categorical_legend(ax, labels: Sequence[str], colors: Sequence[str],
                       *, title=None, loc="lower right", fontsize=8,
                       ncol=1, max_items=20):
    """Add a categorical patch legend (region name -> color)."""
    labels = list(labels)[:max_items]
    colors = list(colors)[:max_items]
    handles = [Patch(facecolor=c, edgecolor="#444444", label=l)
               for l, c in zip(labels, colors)]
    leg = ax.legend(handles=handles, title=title, loc=loc, fontsize=fontsize,
                    ncol=ncol, framealpha=0.9, title_fontsize=fontsize + 1)
    leg.set_zorder(30)
    return leg
