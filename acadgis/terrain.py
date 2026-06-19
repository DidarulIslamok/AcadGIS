"""Terrain visualization: DEM download, hillshade (shaded relief) and
hypsometric (elevation-tinted) maps.

DEM source: **Copernicus GLO-30** (30 m global), served as Cloud-Optimized
GeoTIFFs from the AWS Open Data registry — no API key required. Tiles are
1°×1°; :func:`load_dem` mosaics and (optionally) clips them to a study area.

Requires the optional extra: ``pip install "acadgis[terrain]"`` (rasterio).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple, Union

import numpy as np

_COP_BASE = ("https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
             "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
             "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif")


@dataclass
class DEM:
    """A small elevation raster: ``data`` (2-D float array, nan = no data),
    geographic ``bounds`` (minx, miny, maxx, maxy) and ``crs``."""
    data: np.ndarray
    bounds: Tuple[float, float, float, float]
    crs: str = "EPSG:4326"

    @property
    def extent(self):
        """matplotlib imshow extent (minx, maxx, miny, maxy)."""
        minx, miny, maxx, maxy = self.bounds
        return (minx, maxx, miny, maxy)

    @property
    def vmin(self):
        return float(np.nanmin(self.data))

    @property
    def vmax(self):
        return float(np.nanmax(self.data))


def _bbox_of(area, *, buffer=0.0, download=True):
    """Resolve ``area`` (name | bbox tuple | GeoDataFrame) to a bbox + geometry."""
    geom = None
    if isinstance(area, (tuple, list)) and len(area) == 4:
        bbox = tuple(map(float, area))
    elif hasattr(area, "total_bounds"):  # GeoDataFrame / GeoSeries
        bbox = tuple(area.total_bounds)
        geom = area.geometry.union_all() if hasattr(area, "geometry") else None
    elif isinstance(area, str):
        from .data import load_boundaries
        # try progressively deeper admin levels for a meaningful boundary
        gdf = None
        for lvl in (1, 0):
            try:
                gdf = load_boundaries(area, lvl, download=download)
                break
            except Exception:
                continue
        if gdf is None:
            raise ValueError(f"Could not resolve area {area!r} to a boundary.")
        bbox = tuple(gdf.total_bounds)
        geom = gdf.geometry.union_all()
    else:
        raise TypeError("area must be a name, a (minx,miny,maxx,maxy) bbox, "
                        "or a GeoDataFrame.")
    if buffer:
        minx, miny, maxx, maxy = bbox
        bbox = (minx - buffer, miny - buffer, maxx + buffer, maxy + buffer)
    return bbox, geom


def _tiles_for(bbox):
    minx, miny, maxx, maxy = bbox
    tiles = []
    for lat in range(math.floor(miny), math.ceil(maxy)):
        for lon in range(math.floor(minx), math.ceil(maxx)):
            ns, la = ("N", lat) if lat >= 0 else ("S", -lat)
            ew, lo = ("E", lon) if lon >= 0 else ("W", -lon)
            tiles.append(_COP_BASE.format(ns=ns, lat=la, ew=ew, lon=lo))
    return tiles


def load_dem(area, *, buffer=0.0, max_size: int = 1400, clip: bool = True,
             download: bool = True) -> DEM:
    """Download & mosaic a Copernicus GLO-30 DEM for a study area.

    Parameters
    ----------
    area: country/region name, a ``(minx,miny,maxx,maxy)`` bbox, or a
        GeoDataFrame.
    buffer: degrees of padding to add around the area.
    max_size: cap on the longer raster dimension (downsamples large areas so
        plotting stays fast).
    clip: if True and ``area`` has a polygon, mask elevations outside it to nan.
    """
    try:
        import rasterio
        from rasterio.merge import merge
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Terrain features need rasterio. Install with:\n"
            '    pip install "acadgis[terrain]"'
        ) from exc

    bbox, geom = _bbox_of(area, buffer=buffer, download=download)
    minx, miny, maxx, maxy = bbox
    span = max(maxx - minx, maxy - miny)
    res = max(span / max_size, 0.0002777777777777778)  # not finer than native

    srcs = []
    for url in _tiles_for(bbox):
        try:
            srcs.append(rasterio.open(f"/vsicurl/{url}"))
        except Exception:
            continue  # some ocean tiles don't exist
    if not srcs:
        raise RuntimeError(
            f"No Copernicus DEM tiles found for {area!r} (bbox {bbox}). "
            "Ocean-only area, or network unavailable.")

    mosaic, transform = merge(srcs, bounds=bbox, res=res, nodata=-9999)
    for s in srcs:
        s.close()

    data = mosaic[0].astype("float32")
    data[data <= -1000] = np.nan

    dem = DEM(data=data, bounds=bbox, crs="EPSG:4326")

    if clip and geom is not None:
        dem = _clip_to(dem, geom, transform, data.shape)
    return dem


def _clip_to(dem, geom, transform, shape):
    from rasterio.features import geometry_mask
    try:
        geoms = [geom.__geo_interface__]
    except Exception:
        return dem
    mask = geometry_mask(geoms, out_shape=shape, transform=transform,
                         invert=False)  # True = outside
    out = dem.data.copy()
    out[mask] = np.nan
    return DEM(data=out, bounds=dem.bounds, crs=dem.crs)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def hillshade(dem: DEM, *, azimuth: float = 315, altitude: float = 45,
              vert_exag: float = 0.0008) -> np.ndarray:
    """Return a 0–1 hillshade (shaded-relief) array from a DEM."""
    from matplotlib.colors import LightSource
    ls = LightSource(azdeg=azimuth, altdeg=altitude)
    z = np.nan_to_num(dem.data, nan=np.nanmin(dem.data))
    return ls.hillshade(z, vert_exag=vert_exag)


def relief(dem: DEM, *, ax=None, cmap: str = "terrain", hillshade: bool = True,
           blend: float = 0.55, azimuth: float = 315, altitude: float = 45,
           vert_exag: float = 0.0008, legend: bool = True,
           legend_label: str = "Elevation (m)", title: Optional[str] = None,
           graticule: bool = True, north_arrow=True, scale_bar=True,
           ocean_color: Optional[str] = None, sea_level: float = 0.0,
           vmin: Optional[float] = None, figsize=(9, 9), theme="academic"):
    """Plot a hypsometric (elevation-tinted) + hillshaded relief map.

    Set ``ocean_color`` (e.g. ``"#cce5f0"``) to render elevations at/below
    ``sea_level`` — and the area outside the data — as a realistic sea, so the
    topography reads clearly down to the coast. Returns the matplotlib Axes.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource, Normalize

    from . import decorations as deco
    from .themes import get_theme

    th = get_theme(theme)
    bg = ocean_color or th.background
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(bg)
    else:
        fig = ax.figure
    if ocean_color:
        ax.set_facecolor(ocean_color)

    vmax = dem.vmax
    vmin = vmin if vmin is not None else (sea_level if ocean_color else dem.vmin)
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)

    from matplotlib.colors import to_rgb

    if hillshade:
        ls = LightSource(azdeg=azimuth, altdeg=altitude)
        z = np.nan_to_num(dem.data, nan=vmin)
        rgb = ls.shade(z, cmap=cmap_obj, norm=norm, blend_mode="soft",
                       vert_exag=vert_exag, fraction=1.0)
        rgb = rgb[..., :3]
        if ocean_color:
            sea = (np.isnan(dem.data)) | (dem.data <= sea_level)
            rgb[sea] = to_rgb(ocean_color)
            alpha = np.ones(dem.data.shape)
        else:
            alpha = np.where(np.isnan(dem.data), 0.0, 1.0)
        rgba = np.dstack([rgb, alpha])
        ax.imshow(rgba, extent=dem.extent, origin="upper", zorder=4)
    else:
        ax.imshow(dem.data, extent=dem.extent, origin="upper", cmap=cmap_obj,
                  norm=norm, zorder=4)

    minx, maxx, miny, maxy = dem.extent
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    mean_lat = (miny + maxy) / 2.0
    ax.set_aspect(1.0 / max(np.cos(np.radians(mean_lat)), 1e-6))

    if graticule:
        deco.graticule(ax, color=th.grid_color, lw=th.grid_width,
                       alpha=th.grid_alpha, fontsize=th.label_size,
                       label_color=th.label_color, n_lines=5)
    else:
        ax.set_xticks([]); ax.set_yticks([])
    if north_arrow:
        na = {"style": north_arrow} if isinstance(north_arrow, str) else {}
        deco.north_arrow(ax, color=th.decoration_color, **na)
    if scale_bar:
        sb = {"style": scale_bar} if isinstance(scale_bar, str) else {}
        deco.scale_bar(ax, color=th.decoration_color, fontsize=th.label_size,
                       **sb)
    if legend:
        sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap_obj)
        cb = fig.colorbar(sm, ax=ax, shrink=0.5, pad=0.02)
        cb.set_label(legend_label, fontsize=th.label_size + 1)
    if title:
        ax.set_title(title, fontsize=th.title_size, fontweight=th.title_weight,
                     pad=10)
    return ax
