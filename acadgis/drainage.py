"""Drainage networks derived from a DEM (flow accumulation → stream lines).

This reproduces the "stream order" hydrology look (e.g. the Ethiopia DEM with
its branching drainage). Streams are extracted with :mod:`pysheds` and returned
as a GeoDataFrame whose line widths can be weighted by flow accumulation.

Requires the optional extra: ``pip install "acadgis[drainage]"`` (pysheds).
"""
from __future__ import annotations

from typing import Optional

import numpy as np


def drainage(dem, *, threshold: int = 500):
    """Extract a stream network from a :class:`acadgis.DEM`.

    ``threshold`` is the minimum number of upstream cells for a pixel to count
    as a channel (smaller → denser network). Returns a GeoDataFrame of
    LineStrings (EPSG:4326) with an ``acc`` column (flow accumulation, a proxy
    for stream size/order).
    """
    try:
        import geopandas as gpd
        from pysheds.grid import Grid
        from pysheds.view import Raster, ViewFinder
        from rasterio.transform import from_bounds
        from shapely.geometry import LineString
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Drainage extraction needs pysheds. Install with:\n"
            '    pip install "acadgis[drainage]"'
        ) from exc

    rows, cols = dem.data.shape
    minx, miny, maxx, maxy = dem.bounds
    affine = from_bounds(minx, miny, maxx, maxy, cols, rows)

    z = np.where(np.isnan(dem.data), np.nanmin(dem.data) - 100, dem.data
                 ).astype("float64")
    vf = ViewFinder(affine=affine, shape=z.shape, crs="EPSG:4326", nodata=-1e9)
    raster = Raster(z, viewfinder=vf)
    grid = Grid.from_raster(raster)

    filled = grid.fill_depressions(raster)
    inflated = grid.resolve_flats(filled)
    fdir = grid.flowdir(inflated)
    acc = grid.accumulation(fdir)

    network = grid.extract_river_network(fdir, acc > threshold)

    geoms, accs = [], []
    for feat in network["features"]:
        coords = feat["geometry"]["coordinates"]
        if len(coords) < 2:
            continue
        line = LineString(coords)
        geoms.append(line)
        # sample accumulation near the line's downstream point
        x, y = coords[-1]
        c = int((x - minx) / (maxx - minx) * (cols - 1))
        r = int((maxy - y) / (maxy - miny) * (rows - 1))
        c = min(max(c, 0), cols - 1)
        r = min(max(r, 0), rows - 1)
        accs.append(float(np.asarray(acc)[r, c]))

    gdf = gpd.GeoDataFrame({"acc": accs}, geometry=geoms, crs="EPSG:4326")
    return gdf


def add_streams(ax, streams, *, by_order: bool = True, color="#2b7bba",
                width=0.4, max_width=2.4, alpha=0.9, zorder=7):
    """Plot a drainage network on ``ax``, optionally weighting line width by
    flow accumulation (``by_order``)."""
    import geopandas as gpd

    if len(streams) == 0:
        return ax
    if by_order and "acc" in streams.columns:
        a = streams["acc"].clip(lower=1)
        la = np.log10(a)
        lo, hi = la.min(), la.max()
        rng = (hi - lo) or 1
        lw = width + (max_width - width) * (la - lo) / rng
        for w, (_, row) in zip(lw, streams.iterrows()):
            gpd.GeoSeries([row.geometry], crs=streams.crs).plot(
                ax=ax, color=color, linewidth=float(w), alpha=alpha,
                zorder=zorder)
    else:
        streams.plot(ax=ax, color=color, linewidth=width, alpha=alpha,
                     zorder=zorder)
    return ax
