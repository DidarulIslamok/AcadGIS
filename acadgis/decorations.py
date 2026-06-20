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
                color=_DEFAULT_ARROW_COLOR, label="N", coords="axes",
                edge=None, label_color=None, label_size=None, rotation=0):
    """Draw a north arrow centered at ``loc``.

    Parameters
    ----------
    loc, coords:
        Position. ``coords="axes"`` (default) → ``loc`` is an axes fraction
        ``(0–1, 0–1)``; ``coords="data"`` → ``loc`` is a map point ``(lon, lat)``.
    size:
        Arrow height as a fraction of the axes height.
    style:
        One of ``classic``, ``minimal``, ``pointer``, ``rose``.
    color, edge:
        Fill colour and an optional outline colour for the arrow shapes.
    label, label_color, label_size:
        The "N" label and its styling (defaults follow ``color``/``size``).
    rotation:
        Rotate the whole arrow by this many degrees (e.g. magnetic declination).
    """
    style = (style or "classic").lower()
    spec = _ARROW_SHAPES.get(style, _ARROW_SHAPES["classic"])
    fx, fy = loc
    if coords == "data":                          # convert (lon, lat) -> axes fraction
        fx, fy = ax.transAxes.inverted().transform(ax.transData.transform((fx, fy)))
    r = _aspect_ratio(ax)
    s = size / 40.0  # shapes were defined in ~±20 units
    colors = {"color": color, "shadow": "black"}
    lcolor = label_color or color
    th = math.radians(rotation)
    cos_t, sin_t = math.cos(th), math.sin(th)

    def place(vx, vy):
        if rotation:
            vx, vy = vx * cos_t - vy * sin_t, vx * sin_t + vy * cos_t
        return (fx + vx * s * r, fy + vy * s)

    for verts, ckey, alpha, edge_spec in spec["polys"]:
        pts = [place(vx, vy) for vx, vy in verts]
        ec = edge if edge is not None else (edge_spec or "none")
        ax.add_patch(Polygon(
            pts, closed=True, transform=ax.transAxes, clip_on=False,
            facecolor=colors[ckey], alpha=alpha, edgecolor=ec,
            linewidth=0.6 if (edge or edge_spec) else 0.0, zorder=21))

    nx, ny = spec["n_xy"]
    lx, ly = place(nx, ny)
    ax.text(lx, ly, label, transform=ax.transAxes,
            ha="center", va="center", color=lcolor, clip_on=False,
            fontsize=label_size or max(6.0, 90 * size * spec["n_size"]),
            fontweight="bold", zorder=22)


# --------------------------------------------------------------------------- #
# Scale bar — 3 styles ported from the web app
# --------------------------------------------------------------------------- #
def scale_bar(ax, *, loc=(0.07, 0.07), length_km=None, style="bar",
              color=_DEFAULT_SCALE_COLOR, size=1.0, height=0.014,
              units="km", fontsize=None, coords="axes", text_color=None,
              edge=None, divisions=4):
    """Draw a scale bar sized in real distance (QGIS-style).

    Parameters
    ----------
    style:
        ``bar`` (outline, left half filled), ``simple`` (line + end ticks),
        ``stepped`` (alternating boxes), ``double`` (two-row alternating boxes),
        ``ticks`` (line with division tick marks + 0…length labels).
    loc, coords:
        Position of the bar's left end. ``coords="axes"`` (default) → axes
        fraction; ``coords="data"`` → a map point ``(lon, lat)``.
    length_km, units, size:
        Real length (auto if ``None``), ``units`` ∈ {km, mi}, ``size`` scales it.
    color, edge, text_color:
        Fill, outline and label colours (``edge``/``text_color`` default to ``color``).
    divisions:
        Number of segments for ``stepped`` / ``double`` / ``ticks``.
    """
    style = (style or "bar").lower()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    mid_lat = (y0 + y1) / 2.0
    span_km = (x1 - x0) * _km_per_degree_lon(mid_lat)

    if length_km is None:
        length_km = _nice_number(span_km * 0.25)
    bar_deg = (length_km / _km_per_degree_lon(mid_lat)) * size

    if coords == "data":
        bx, by = loc
    else:
        bx = x0 + loc[0] * (x1 - x0)
        by = y0 + loc[1] * (y1 - y0)
    bh = height * (y1 - y0) * size
    fs = fontsize or (8 * size)
    tcol = text_color or color
    ecol = edge or color
    divisions = max(1, int(divisions))

    label_val = length_km if units == "km" else length_km / 1.609344
    label = f"{label_val:g} {units}"

    def txt(xx, yy, s, ha="center"):
        ax.text(xx, yy, s, ha=ha, va="bottom", fontsize=fs, color=tcol,
                family="monospace", fontweight="bold", zorder=22, clip_on=False)

    if style == "simple":
        ax.add_line(Line2D([bx, bx + bar_deg], [by, by], color=ecol,
                           lw=1.2 * size, zorder=21, clip_on=False))
        for xx in (bx, bx + bar_deg):
            ax.add_line(Line2D([xx, xx], [by, by + bh], color=ecol,
                               lw=1.2 * size, zorder=21, clip_on=False))
        txt(bx + bar_deg / 2, by + bh * 1.4, label)
    elif style in ("stepped", "double"):
        seg = bar_deg / divisions
        rows = 2 if style == "double" else 1
        for row in range(rows):
            for i in range(divisions):
                fc = color if (i + row) % 2 == 0 else "white"
                ax.add_patch(Rectangle((bx + i * seg, by + row * bh), seg, bh,
                                       facecolor=fc, edgecolor=ecol,
                                       lw=0.5 * size, zorder=21, clip_on=False))
        txt(bx, by + bh * rows + bh * 0.4, "0", ha="center")
        txt(bx + bar_deg, by + bh * rows + bh * 0.4, label, ha="center")
    elif style == "ticks":
        seg = bar_deg / divisions
        ax.add_line(Line2D([bx, bx + bar_deg], [by, by], color=ecol,
                           lw=1.4 * size, zorder=21, clip_on=False))
        for i in range(divisions + 1):
            xx = bx + i * seg
            ax.add_line(Line2D([xx, xx], [by, by + bh], color=ecol,
                               lw=1.2 * size, zorder=21, clip_on=False))
        txt(bx, by + bh * 1.4, "0")
        txt(bx + bar_deg, by + bh * 1.4, label)
    else:  # 'bar' — outline + left half filled
        ax.add_patch(Rectangle((bx, by), bar_deg, bh, facecolor="white",
                               edgecolor=ecol, lw=1.0 * size, zorder=21,
                               clip_on=False))
        ax.add_patch(Rectangle((bx, by), bar_deg / 2, bh, facecolor=color,
                               edgecolor="none", zorder=21, clip_on=False))
        txt(bx + bar_deg, by + bh * 1.4, label, ha="right")


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


def graticule(ax, *, interval=None, x_interval=None, y_interval=None,
              n=5, n_lines=None, square=True,
              grid=True, grid_color=None, grid_lw=None, grid_alpha=None, grid_style="-",
              color="#9aa0a6", lw=0.5, alpha=0.55,
              ticks=True, labels=True, tick_dir="out", tick_len=3.5, tick_width=0.8,
              tick_color="#333333", minor=False, minor_n=2,
              sides="lb", tick_sides=None,
              fontsize=8, label_color="#333333", bold=False, italic=False,
              font=None, rotate_x=0, rotate_y=0):
    """Latitude/longitude graticule with independent grid + tick control.

    Parameters
    ----------
    grid:
        Draw grid lines. Style them with ``grid_color`` / ``grid_lw`` /
        ``grid_alpha`` / ``grid_style`` (``"-"``, ``"--"``, ``":"``, ``"-."`` or a
        dash tuple). ``grid=False`` keeps the ticks/labels but drops the lines.
    ticks, labels:
        Tick marks and degree labels. ``tick_dir`` is ``"in"``/``"out"``/``"inout"``;
        ``tick_len`` / ``tick_width`` size them; ``minor=True`` adds ``minor_n``
        minor ticks between majors.
    sides, tick_sides:
        Which sides get labels / tick marks — a subset of ``"lrtb"`` or ``"all"``
        (default labels left+bottom).
    interval / x_interval / y_interval, n, square:
        Spacing in degrees. ``square=True`` (default) uses one interval on both
        axes (square cells); set per-axis intervals or ``square=False`` for
        independent spacing. ``n`` is the target divisions when auto.
    fontsize, label_color, bold, italic, font, rotate_x, rotate_y:
        Label styling (e.g. ``rotate_y=90`` for vertical latitude labels).
    """
    grid_color = grid_color if grid_color is not None else color
    grid_lw = grid_lw if grid_lw is not None else lw
    grid_alpha = grid_alpha if grid_alpha is not None else alpha
    if n_lines:
        n = n_lines

    x0, x1 = sorted(ax.get_xlim())
    y0, y1 = sorted(ax.get_ylim())
    xi = x_interval if x_interval is not None else interval
    yi = y_interval if y_interval is not None else interval
    if xi is None or yi is None:
        if square:
            base = _nice_interval(max(x1 - x0, y1 - y0), n)
            xi = base if xi is None else xi
            yi = base if yi is None else yi
        else:
            xi = _nice_interval(x1 - x0, n) if xi is None else xi
            yi = _nice_interval(y1 - y0, n) if yi is None else yi

    xticks = np.arange(math.ceil(x0 / xi) * xi, x1 + 1e-9, xi)
    yticks = np.arange(math.ceil(y0 / yi) * yi, y1 + 1e-9, yi)

    if grid:
        for xt in xticks:
            ax.axvline(xt, color=grid_color, lw=grid_lw, alpha=grid_alpha,
                       linestyle=grid_style, zorder=1)
        for yt in yticks:
            ax.axhline(yt, color=grid_color, lw=grid_lw, alpha=grid_alpha,
                       linestyle=grid_style, zorder=1)

    sset = "lrtb" if sides == "all" else (sides or "")
    tset = "lrtb" if tick_sides == "all" else (tick_sides if tick_sides is not None else sset)

    if not ticks:
        ax.set_xticks([]); ax.set_yticks([])
    else:
        ax.set_xticks(xticks); ax.set_yticks(yticks)
        lkw = dict(fontsize=fontsize, color=label_color,
                   fontweight="bold" if bold else "normal",
                   fontstyle="italic" if italic else "normal")
        if font:
            lkw["fontfamily"] = font
        if labels:
            ax.set_xticklabels([_fmt_deg(t, "x") for t in xticks],
                               rotation=rotate_x,
                               ha="right" if rotate_x else "center", **lkw)
            ax.set_yticklabels([_fmt_deg(t, "y") for t in yticks],
                               rotation=rotate_y, **lkw)
        else:
            ax.set_xticklabels([]); ax.set_yticklabels([])
        if minor:
            from matplotlib.ticker import AutoMinorLocator
            ax.xaxis.set_minor_locator(AutoMinorLocator(minor_n))
            ax.yaxis.set_minor_locator(AutoMinorLocator(minor_n))
        ax.tick_params(which="major", direction=tick_dir, length=tick_len,
                       width=tick_width, color=tick_color,
                       top="t" in tset, bottom="b" in tset,
                       left="l" in tset, right="r" in tset,
                       labeltop=labels and "t" in sset, labelbottom=labels and "b" in sset,
                       labelleft=labels and "l" in sset, labelright=labels and "r" in sset)
        if minor:
            ax.tick_params(which="minor", direction=tick_dir, length=tick_len * 0.55,
                           width=tick_width * 0.7, color=tick_color,
                           top="t" in tset, bottom="b" in tset,
                           left="l" in tset, right="r" in tset)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
        spine.set_linewidth(0.8)


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
