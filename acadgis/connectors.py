"""Easy panel-to-panel connectors — wraps matplotlib's ConnectionPatch.

Custom connectors then need only ``import acadgis as agis`` (no matplotlib
imports, no transform objects)::

    fig = agis.study_area(..., links=False)
    p1, p2, p3 = fig.panels[:3]
    agis.connect(fig, p2, (1, 1), p1, (-4, 57), a_coords="axes", b_coords="data")
"""
from __future__ import annotations

__all__ = ["connect"]


def _trans(ax, fig, name):
    name = (name or "data").lower()
    if name in ("data", "lonlat", "map"):
        return ax.transData
    if name in ("axes", "panel", "ax"):
        return ax.transAxes
    if name in ("figure", "fig"):
        return fig.transFigure
    raise ValueError(f"unknown coords {name!r}; use 'data', 'axes' or 'figure'")


def connect(fig, a, xy_a, b, xy_b, *, a_coords="data", b_coords="data",
            color="#1b9aaa", width=1.6, style="-", arrow=False,
            alpha=1.0, zorder=50):
    """Draw a connector from ``xy_a`` on panel ``a`` to ``xy_b`` on panel ``b``.

    Parameters
    ----------
    fig:
        The figure (e.g. returned by :func:`study_area`).
    a, b:
        The two panels, e.g. ``fig.panels[0]`` and ``fig.panels[1]`` (may be the same).
    xy_a, xy_b:
        Endpoint coordinates, interpreted by ``a_coords`` / ``b_coords``.
    a_coords, b_coords:
        Coordinate system for each end — ``"data"`` = map ``(lon, lat)``,
        ``"axes"`` = panel fraction ``0–1`` (corner/edge), ``"figure"`` = whole
        figure ``0–1``.
    color, width, style, alpha:
        Line styling. ``style`` is any matplotlib line style (``'-'``, ``'--'``,
        ``':'``, ``'-.'`` or a dash tuple like ``(0, (6, 3))``).
    arrow:
        ``True`` adds an arrowhead at the ``b`` end.

    Returns the ConnectionPatch (already added to the figure).
    """
    from matplotlib.patches import ConnectionPatch
    cp = ConnectionPatch(
        xyA=xy_a, coordsA=_trans(a, fig, a_coords),
        xyB=xy_b, coordsB=_trans(b, fig, b_coords),
        color=color, lw=width, linestyle=style, alpha=alpha,
        zorder=zorder, clip_on=False,
        arrowstyle="-|>" if arrow else "-",
        mutation_scale=14 if arrow else 1)
    fig.add_artist(cp)
    return cp
