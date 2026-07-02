"""acadgis.thematic — the remaining standard thematic map types.

Completes the catalogue (choropleth and graduated symbols live in ``core``):

    interpolate_field  sparse (lon, lat, value) points → a smooth grid
    add_isopleth       filled interpolated surface (filled contours)
    add_contours       isolines — contour lines + inline labels
    add_heatmap        point-density surface (KDE or hexbin)
    dot_density        N dots per region, proportional to a count
    bivariate          two variables at once — 3×3 blended palette + 2-D legend
    cartogram          regions resized by value (``dorling`` / ``noncontig``)

``interpolate_field`` is the shared engine: isopleth, isoline and (KDE) heatmap
are different renderings of a points→grid step. Everything follows the layer
z-order ladder from :mod:`acadgis.layers` and needs only the core install
(SciPy is used for the KDE heatmap when available; hexbin works without it).
"""
from __future__ import annotations

from typing import Optional, Sequence, Union

import geopandas as gpd
import numpy as np

from .layers import Z_RASTER, Z_VECTOR, Z_POINT

# Classic Joshua-Stevens 3×3 bivariate palette (rows = y variable, cols = x).
BIVARIATE_PALETTE = [["#e8e8e8", "#ace4e4", "#5ac8c8"],
                     ["#dfb0d6", "#a5add3", "#5698b9"],
                     ["#be64ac", "#8c62aa", "#3b4994"]]


# --------------------------------------------------------------------------- #
#  shared engine: points -> grid
# --------------------------------------------------------------------------- #
def interpolate_field(lon, lat, values, *, bbox=None, res: int = 320,
                      bw: Optional[float] = None, clip=None):
    """Interpolate sparse ``(lon, lat, values)`` samples to a smooth grid.

    Uses a numpy Gaussian-kernel (no SciPy needed). Returns ``(Z, extent)``
    where ``Z`` is a ``(res, res)`` array (row 0 = north) and ``extent`` is
    ``(minx, maxx, miny, maxy)`` — ready for :func:`add_isopleth`,
    :func:`add_contours` or ``ax.imshow(Z, extent=extent)``.

    Parameters
    ----------
    bbox:
        ``(minx, miny, maxx, maxy)`` grid window. Defaults to the data bounds
        padded 5 %.
    bw:
        Kernel bandwidth in degrees — bigger = smoother. Defaults to 10 % of
        the window size.
    clip:
        GeoDataFrame/GeoSeries/shapely geometry — cells outside become NaN
        (e.g. keep the field on land only).
    """
    lon, lat, values = (np.asarray(a, dtype=float) for a in (lon, lat, values))
    if bbox is None:
        px = (lon.max() - lon.min()) * 0.05 or 0.5
        py = (lat.max() - lat.min()) * 0.05 or 0.5
        bbox = (lon.min() - px, lat.min() - py, lon.max() + px, lat.max() + py)
    minx, miny, maxx, maxy = map(float, bbox)
    gx, gy = np.meshgrid(np.linspace(minx, maxx, res),
                         np.linspace(maxy, miny, res))          # row 0 = north
    if bw is None:
        bw = 0.10 * max(maxx - minx, maxy - miny)
    dx = gx[..., None] - lon
    dy = gy[..., None] - lat
    w = np.exp(-(dx * dx + dy * dy) / (2.0 * bw * bw))
    Z = (w * values).sum(-1) / (w.sum(-1) + 1e-12)
    if clip is not None:
        geom = clip.geometry.union_all() if hasattr(clip, "geometry") else clip
        pts = gpd.GeoSeries(gpd.points_from_xy(gx.ravel(), gy.ravel()), crs="EPSG:4326")
        inside = pts.within(geom).values
        Z = Z.ravel()
        Z[~inside] = np.nan
        Z = Z.reshape(gx.shape)
    return Z, (minx, maxx, miny, maxy)


def _grid_from(data, extent):
    """Normalize input for isopleth/contours -> (Z, (minx, maxx, miny, maxy)).

    Accepts: 2-D array + explicit extent · a DEM (``.data``/``.bounds``) · a
    GeoTIFF path or rioxarray DataArray · the ``(Z, extent)`` tuple returned by
    :func:`interpolate_field`.
    """
    if isinstance(data, tuple) and len(data) == 2:              # (Z, extent)
        return np.asarray(data[0], dtype=float), tuple(data[1])
    if hasattr(data, "bounds") and hasattr(data, "data"):       # DEM
        minx, miny, maxx, maxy = data.bounds
        return np.asarray(data.data, dtype=float), (minx, maxx, miny, maxy)
    if isinstance(data, str) or hasattr(data, "rio"):           # path / DataArray
        import rioxarray
        da = data if hasattr(data, "rio") else rioxarray.open_rasterio(data, masked=True)
        if da.rio.crs is not None and da.rio.crs.to_epsg() != 4326:
            da = da.rio.reproject("EPSG:4326")
        arr = da.values
        Z = np.asarray(arr if arr.ndim == 2 else arr[0], dtype=float)
        xs, ys = da["x"].values, da["y"].values
        if ys[0] < ys[-1]:                                      # ensure row 0 = north
            Z = Z[::-1]
        return Z, (float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max()))
    if extent is None:
        raise ValueError("A bare 2-D array needs extent=(minx, maxx, miny, maxy).")
    return np.asarray(data, dtype=float), tuple(extent)


def _grid_xy(Z, ext):
    minx, maxx, miny, maxy = ext
    ny, nx = Z.shape
    return np.linspace(minx, maxx, nx), np.linspace(maxy, miny, ny)


# --------------------------------------------------------------------------- #
#  isopleth (filled) & isolines
# --------------------------------------------------------------------------- #
def add_isopleth(ax, data, *, extent=None, cmap: str = "RdYlBu_r",
                 levels: Union[int, Sequence[float]] = 12, alpha: float = 1.0,
                 colorbar: bool = False, colorbar_label: Optional[str] = None,
                 zorder: int = Z_RASTER):
    """Filled interpolated surface (filled contours) — the *isopleth* map.

    ``data``: the ``(Z, extent)`` from :func:`interpolate_field`, a 2-D array
    (with ``extent=``), a DEM, or a GeoTIFF path/DataArray. Returns the
    ``QuadContourSet``.
    """
    Z, ext = _grid_from(data, extent)
    X, Y = _grid_xy(Z, ext)
    cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap, alpha=alpha, zorder=zorder)
    if colorbar:
        ax.figure.colorbar(cf, ax=ax, shrink=0.6, label=colorbar_label or "")
    return cf


def add_contours(ax, data, *, extent=None, levels: Union[int, Sequence[float]] = 10,
                 colors: str = "#333333", linewidths: float = 0.8,
                 linestyles: str = "-", labels: bool = True, fmt: str = "%g",
                 fontsize: float = 6, zorder: int = Z_VECTOR):
    """Isolines — contour lines with optional inline labels (isotherms, isobars,
    elevation contours). Same ``data`` forms as :func:`add_isopleth`. Returns the
    ``QuadContourSet``."""
    Z, ext = _grid_from(data, extent)
    X, Y = _grid_xy(Z, ext)
    cs = ax.contour(X, Y, Z, levels=levels, colors=colors, linewidths=linewidths,
                    linestyles=linestyles, zorder=zorder)
    if labels:
        ax.clabel(cs, inline=True, fontsize=fontsize, fmt=fmt)
    return cs


# --------------------------------------------------------------------------- #
#  heat map (density)
# --------------------------------------------------------------------------- #
def add_heatmap(ax, lon, lat, *, kind: str = "auto", weights=None,
                gridsize: int = 90, res: int = 220, bw: Optional[float] = None,
                cmap: str = "inferno", bins="log", mincnt: int = 1,
                alpha: float = 1.0, colorbar: bool = False,
                colorbar_label: str = "Density", zorder: int = Z_RASTER + 1):
    """Point-density heat map.

    ``kind``: ``"kde"`` (smooth surface — best for sparse features like cities;
    supports ``weights=``, needs SciPy), ``"hexbin"`` (binned — best for dense
    event data), or ``"auto"`` (KDE when SciPy is available and there are fewer
    than ~5 000 points, else hexbin). Returns the created artist.
    """
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    if kind == "auto":
        try:
            import scipy  # noqa: F401
            kind = "kde" if len(lon) < 5000 else "hexbin"
        except Exception:
            kind = "hexbin"

    if kind == "kde":
        try:
            from scipy.stats import gaussian_kde
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "add_heatmap(kind='kde') needs SciPy — pip install scipy, "
                "or use kind='hexbin'.") from exc
        k = gaussian_kde(np.vstack([lon, lat]), weights=weights, bw_method=bw)
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        gx, gy = np.mgrid[x0:x1:complex(res), y0:y1:complex(res)]
        z = k(np.vstack([gx.ravel(), gy.ravel()])).reshape(gx.shape)
        art = ax.imshow(z.T, extent=(x0, x1, y0, y1), origin="lower", cmap=cmap,
                        alpha=alpha, aspect="auto", zorder=zorder)
    else:
        art = ax.hexbin(lon, lat, C=weights, gridsize=gridsize, cmap=cmap,
                        bins=bins, mincnt=mincnt, alpha=alpha, zorder=zorder)
    if colorbar:
        ax.figure.colorbar(art, ax=ax, shrink=0.6, label=colorbar_label)
    return art


# --------------------------------------------------------------------------- #
#  dot-density
# --------------------------------------------------------------------------- #
def dot_density(ax, gdf, value: str, *, per: float = 100000, color: str = "#1d3557",
                size: float = 1.6, alpha: float = 0.65, seed: int = 0,
                max_dots: int = 200000, zorder: int = Z_VECTOR):
    """Classic dot-density map: scatter ``value / per`` random dots inside each
    region (1 dot = ``per`` units). Deterministic for a given ``seed``.
    ``max_dots`` guards against an accidental million-dot figure. Returns ``ax``.
    """
    rng = np.random.default_rng(seed)
    total = float(np.nansum(gdf[value].values)) / per
    if total > max_dots:
        raise ValueError(
            f"~{int(total):,} dots requested (> max_dots={max_dots:,}). "
            f"Raise `per` (currently {per:g}) or `max_dots`.")
    xs_all, ys_all = [], []
    for geom, v in zip(gdf.geometry, gdf[value]):
        if geom is None or geom.is_empty or not np.isfinite(v):
            continue
        n = int(round(float(v) / per))
        if n <= 0:
            continue
        minx, miny, maxx, maxy = geom.bounds
        got_x: list = []
        got_y: list = []
        tries = 0
        while len(got_x) < n and tries < 50:      # rejection-sample inside the polygon
            k = max((n - len(got_x)) * 3, 30)
            bx = rng.uniform(minx, maxx, k)
            by = rng.uniform(miny, maxy, k)
            cand = gpd.GeoSeries(gpd.points_from_xy(bx, by), crs=gdf.crs)
            inside = cand.within(geom).values
            got_x.extend(bx[inside].tolist())
            got_y.extend(by[inside].tolist())
            tries += 1
        xs_all.extend(got_x[:n])
        ys_all.extend(got_y[:n])
    ax.scatter(xs_all, ys_all, s=size, c=color, alpha=alpha, linewidths=0,
               zorder=zorder)
    return ax


# --------------------------------------------------------------------------- #
#  bivariate choropleth
# --------------------------------------------------------------------------- #
def _tercile_codes(v):
    """Robust 0/1/2 classification by terciles (handles ties)."""
    v = np.asarray(v, dtype=float)
    q1, q2 = np.nanquantile(v, [1 / 3, 2 / 3])
    return np.clip(np.digitize(v, [q1, q2]), 0, 2)


def bivariate(gdf, x: str, y: str, *, ax=None, palette=None,
              edgecolor: str = "white", linewidth: float = 0.4,
              xlabel: Optional[str] = None, ylabel: Optional[str] = None,
              legend: bool = True, legend_loc=(0.02, 0.02, 0.20, 0.20),
              title: Optional[str] = None, figsize=(10, 7), zorder: int = 5):
    """Bivariate choropleth — show **two variables at once**.

    Each region's ``x`` and ``y`` values are classified into terciles and
    coloured from a 3×3 blended ``palette`` (default: the classic
    purple/teal scheme). A small 2-D legend is drawn inside the axes.
    Returns the matplotlib Axes.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    pal = palette or BIVARIATE_PALETTE
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    g = gdf.copy()
    xc = _tercile_codes(g[x])
    yc = _tercile_codes(g[y])
    g["_c"] = [pal[yi][xi] for xi, yi in zip(xc, yc)]
    g.plot(ax=ax, color=g["_c"], edgecolor=edgecolor, linewidth=linewidth,
           zorder=zorder)
    if legend:
        lax = ax.inset_axes(list(legend_loc))
        for yi in range(3):
            for xi in range(3):
                lax.add_patch(Rectangle((xi, yi), 1, 1, color=pal[yi][xi]))
        lax.set_xlim(0, 3)
        lax.set_ylim(0, 3)
        lax.set_xticks([])
        lax.set_yticks([])
        lax.set_xlabel(f"{xlabel or x} →", fontsize=7)
        lax.set_ylabel(f"{ylabel or y} →", fontsize=7)
        lax.set_facecolor("none")
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    return ax


# --------------------------------------------------------------------------- #
#  cartograms
# --------------------------------------------------------------------------- #
def cartogram(gdf, value: str, *, kind: str = "dorling", ax=None,
              cmap: str = "YlOrRd", edgecolor: str = "#333333",
              linewidth: float = 0.5, ghost: bool = True,
              ghost_color: str = "#cfd6dc",
              # dorling options
              max_radius: Optional[float] = None, iterations: int = 140,
              labels: Optional[str] = None, label_size: float = 6,
              # noncontig options
              clip_scale=(0.4, 1.7),
              colorbar: bool = False, colorbar_label: Optional[str] = None,
              title: Optional[str] = None, figsize=(10, 8), zorder: int = 5):
    """Cartogram — regions resized by ``value`` instead of land area.

    ``kind="dorling"``: regions become circles at their centroids, radius ∝
    ``sqrt(value)``, pushed apart so they don't overlap. ``kind="noncontig"``:
    each region is scaled **in place**; scale factors are normalized by the
    *median* value density and clipped to ``clip_scale`` so shapes never
    collapse. ``ghost=True`` draws the original outlines underneath. Returns
    the matplotlib Axes.
    """
    import matplotlib.pyplot as plt
    from matplotlib import colormaps
    from matplotlib.colors import Normalize
    from matplotlib.patches import Circle

    if kind not in ("dorling", "noncontig"):
        raise ValueError(f"Unknown kind {kind!r}. Options: 'dorling', 'noncontig'. "
                         "(true contiguous cartograms are planned)")
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    g = gdf.copy()
    vals = np.asarray(g[value].values, dtype=float)
    norm = Normalize(np.nanmin(vals), np.nanmax(vals))
    cmap_o = colormaps[cmap]
    face = [cmap_o(norm(v)) for v in vals]

    if ghost:
        g.boundary.plot(ax=ax, color=ghost_color, linewidth=0.45, zorder=zorder - 1)

    if kind == "noncontig":
        from shapely.affinity import scale as _scale
        area = g.to_crs(6933).area.values                       # equal-area m²
        dens = vals / np.where(area > 0, area, np.nan)
        f = np.sqrt(dens / np.nanmedian(dens))
        f = np.clip(np.nan_to_num(f, nan=1.0), *clip_scale)
        geoms = [_scale(geom, xfact=fi, yfact=fi, origin=geom.representative_point())
                 for geom, fi in zip(g.geometry, f)]
        out = gpd.GeoDataFrame({value: vals}, geometry=geoms, crs=g.crs)
        out.plot(ax=ax, color=face, edgecolor=edgecolor, linewidth=linewidth,
                 zorder=zorder)
    else:
        c = g.geometry.representative_point()
        x = c.x.values.astype(float)
        y = c.y.values.astype(float)
        if max_radius is None:
            minx, miny, maxx, maxy = g.total_bounds
            max_radius = 0.06 * max(maxx - minx, maxy - miny)
        r = np.sqrt(np.nan_to_num(vals, nan=0.0) / np.nanmax(vals)) * max_radius
        for _ in range(iterations):                             # pairwise repulsion
            for i in range(len(x)):
                for j in range(i + 1, len(x)):
                    dx, dy = x[j] - x[i], y[j] - y[i]
                    d = float(np.hypot(dx, dy)) or 1e-9
                    overlap = (r[i] + r[j]) - d
                    if overlap > 0:
                        ux, uy = dx / d, dy / d
                        x[i] -= ux * overlap / 2
                        y[i] -= uy * overlap / 2
                        x[j] += ux * overlap / 2
                        y[j] += uy * overlap / 2
        for xi, yi, ri, fc in zip(x, y, r, face):
            if ri > 0:
                ax.add_patch(Circle((xi, yi), ri, facecolor=fc, edgecolor=edgecolor,
                                    linewidth=linewidth, zorder=zorder))
        if labels and labels in g.columns:
            for xi, yi, ri, t in zip(x, y, r, g[labels]):
                if ri > max_radius * 0.33:
                    ax.annotate(str(t), (xi, yi), ha="center", va="center",
                                fontsize=label_size, zorder=zorder + 1)
        ax.set_aspect("equal")
        minx, miny, maxx, maxy = g.total_bounds
        pad = max_radius * 1.5
        ax.set_xlim(min(minx, x.min() - pad), max(maxx, x.max() + pad))
        ax.set_ylim(min(miny, y.min() - pad), max(maxy, y.max() + pad))

    if colorbar:
        import matplotlib.cm as mcm
        sm = mcm.ScalarMappable(norm=norm, cmap=cmap_o)
        sm.set_array([])
        ax.figure.colorbar(sm, ax=ax, shrink=0.6, label=colorbar_label or value)
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    return ax
