"""acadgis.layers — generic raster, vector, basemap & topography overlays.

Every function is an ``add_*(ax, ...)`` overlay so it composes with
:func:`acadgis.plot`, :func:`acadgis.study_area` panels, or any matplotlib Axes.

    import acadgis as agis
    ax = agis.plot(gdf)
    agis.add_basemap(ax, style="satellite")         # XYZ tiles
    agis.add_raster(ax, "ndvi.tif", cmap="YlGn", colorbar=True)
    agis.add_layer(ax, "sites.geojson", labels="name")
    agis.add_cities(ax, area=gdf, top=8)

Raster / topography need ``acadgis[terrain]`` (rasterio + rioxarray); basemaps
need ``acadgis[basemap]`` (contextily). Both are optional — clear errors point
to the right extra.
"""
from __future__ import annotations

from typing import Optional, Sequence, Union

import geopandas as gpd
import numpy as np

# Z-ORDER LADDER (so layers stack predictably):
#   sea 0 · basemap/raster 1 · land polygons 5 · rivers/roads 6 · points/labels 8
Z_BASEMAP = 0
Z_RASTER = 1
Z_VECTOR = 6
Z_POINT = 8


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #
def _ax_extent_box(ax):
    from shapely.geometry import box
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _as_geoms(area):
    """area (GeoDataFrame/GeoSeries/shapely) -> list of shapely geometries."""
    if area is None:
        return None
    if hasattr(area, "geometry"):
        return list(area.geometry.values)
    if hasattr(area, "geoms") or hasattr(area, "exterior") or hasattr(area, "coords"):
        return [area]
    return list(area)


def _halo(color="white", lw=2.2):
    import matplotlib.patheffects as pe
    return [pe.withStroke(linewidth=lw, foreground=color)]


def _pick_label_field(gdf, label_field):
    if label_field and label_field in gdf.columns:
        return label_field
    for c in ("name", "NAME", "label", "NAME_3", "NAME_2", "NAME_1", "NAME_0"):
        if c in gdf.columns:
            return c
    return None


def _select_labels(gdf, labels, *, rank_field=None):
    """Resolve the hide / one / N / all label policy -> subset to annotate.

    ``labels``: ``None``/``False`` = hide · ``True``/``"all"`` = every feature ·
    ``"one"``/``1`` = a single label · an ``int`` = that many (ranked by
    ``rank_field`` if present, e.g. population)."""
    if labels in (None, False):
        return gdf.iloc[0:0]
    if labels in (True, "all"):
        return gdf
    n = 1 if labels == "one" else (labels if isinstance(labels, int) else None)
    if n is None:
        return gdf
    if rank_field and rank_field in gdf.columns:
        return gdf.sort_values(rank_field, ascending=False).head(n)
    return gdf.head(n)


def _draw_labels(ax, gdf, field, *, size, color, halo, zorder, dy=4):
    eff = _halo() if halo else None
    for geom, txt in zip(gdf.geometry, gdf[field]):
        if geom is None or txt is None:
            continue
        p = geom.representative_point()
        ax.annotate(str(txt), (p.x, p.y), fontsize=size, color=color, ha="center",
                    va="bottom", xytext=(0, dy), textcoords="offset points",
                    zorder=zorder, path_effects=eff)


# --------------------------------------------------------------------------- #
#  RASTER
# --------------------------------------------------------------------------- #
def add_raster(ax, src, *, area=None, cmap: str = "viridis", categorical: bool = False,
               classes: Optional[dict] = None, rgb: bool = False, opacity: float = 1.0,
               vmin: Optional[float] = None, vmax: Optional[float] = None,
               colorbar: bool = False, colorbar_label: Optional[str] = None,
               legend: bool = False, legend_loc: str = "lower left",
               legend_title: str = "Class", interpolation: Optional[str] = None,
               zorder: int = Z_RASTER):
    """Overlay any raster (GeoTIFF/NetCDF path, or a rioxarray DataArray) on ``ax``.

    Three modes:

    - **continuous** (default): single band → ``cmap`` (+ ``colorbar``). NDVI,
      temperature, rainfall, elevation, …
    - **categorical** (``categorical=True`` + ``classes={value: (color, label)}``):
      a class raster with an automatic legend. Land cover / land use.
    - **rgb** (``rgb=True``): a 3–4 band true-colour image.

    ``area`` (GeoDataFrame/GeoSeries/shapely) clips the raster to that geometry.
    Rasters in any CRS are reprojected to lon/lat (EPSG:4326) so they line up
    with AcadGIS maps. Returns ``ax``.
    """
    try:
        import rioxarray  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            'add_raster needs rasterio + rioxarray. Install with:\n'
            '    pip install "acadgis[terrain]"') from exc
    import rioxarray

    da = src if hasattr(src, "rio") else rioxarray.open_rasterio(src, masked=not rgb)
    if da.rio.crs is not None and da.rio.crs.to_epsg() != 4326:
        da = da.rio.reproject("EPSG:4326")
    geoms = _as_geoms(area)
    if geoms is not None:
        da = da.rio.clip(geoms, crs="EPSG:4326", drop=True, all_touched=True)

    arr = da.values  # (band, y, x) or (y, x) for a computed single-band array
    band2d = arr if arr.ndim == 2 else arr[0]
    xs, ys = da["x"].values, da["y"].values
    left, right = float(xs.min()), float(xs.max())
    bottom, top = float(ys.min()), float(ys.max())
    origin = "upper" if ys[0] > ys[-1] else "lower"
    extent = (left, right, bottom, top)

    if rgb:
        img = np.transpose(arr[:3], (1, 2, 0)).astype(float)
        if np.nanmax(img) > 1:
            img = img / 255.0
        ax.imshow(img, extent=extent, origin=origin, zorder=zorder, alpha=opacity,
                  interpolation=interpolation)
    elif categorical:
        from matplotlib.colors import BoundaryNorm, ListedColormap
        import matplotlib.patches as mpatches
        if not classes:
            raise ValueError("categorical=True needs classes={value: (color, label)}")
        band = band2d.astype(float)
        vals = sorted(classes)
        cmap_c = ListedColormap([classes[v][0] for v in vals])
        norm = BoundaryNorm([vals[0] - 0.5] + [v + 0.5 for v in vals], cmap_c.N)
        ax.imshow(band, extent=extent, origin=origin, cmap=cmap_c, norm=norm,
                  zorder=zorder, alpha=opacity, interpolation=interpolation or "nearest")
        if legend:
            h = [mpatches.Patch(color=classes[v][0], label=classes[v][1]) for v in vals]
            ax.legend(handles=h, loc=legend_loc, fontsize=7, framealpha=0.92,
                      title=legend_title)
    else:
        band = band2d.astype(float)
        im = ax.imshow(band, extent=extent, origin=origin, cmap=cmap, vmin=vmin,
                       vmax=vmax, zorder=zorder, alpha=opacity, interpolation=interpolation)
        if colorbar:
            ax.figure.colorbar(im, ax=ax, shrink=0.6, label=colorbar_label or "")
    return ax


# --------------------------------------------------------------------------- #
#  VECTOR
# --------------------------------------------------------------------------- #
def add_layer(ax, src, *, area=None, color: Optional[str] = None,
              facecolor: Optional[str] = None, edgecolor: Optional[str] = None,
              linewidth: float = 0.8, markersize: float = 26, marker: str = "o",
              alpha: float = 1.0, label: Optional[str] = None,
              labels: Union[bool, str, int, None] = None,
              label_field: Optional[str] = None, label_size: float = 7,
              label_color: str = "#222", label_halo: bool = True,
              legend: bool = False, legend_loc: str = "upper right",
              clip: bool = True, zorder: Optional[int] = None):
    """Overlay any vector source (file path or GeoDataFrame/GeoSeries) on ``ax``.

    Geometry type is auto-detected and styled sensibly — **polygons** (fill +
    edge), **lines** (colour + width) or **points** (markers). ``area`` clips to a
    geometry; otherwise it clips to the current view (``clip=True``).

    Label control via ``labels``: ``None``/``False`` = none (default) ·
    ``True``/``"all"`` = every feature · ``"one"``/``1`` = a single label · an
    ``int`` = that many. ``label_field`` chooses the column (auto-detected if
    omitted). Returns ``ax``.
    """
    gdf = src if isinstance(src, (gpd.GeoDataFrame, gpd.GeoSeries)) else gpd.read_file(src)
    if isinstance(gdf, gpd.GeoSeries):
        gdf = gpd.GeoDataFrame(geometry=gdf)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    geoms = _as_geoms(area)
    if geoms is not None:
        from shapely.ops import unary_union
        gdf = gpd.clip(gdf, unary_union(geoms))
    elif clip:
        gdf = gpd.clip(gdf, _ax_extent_box(ax))
    if len(gdf) == 0:
        return ax

    gt = gdf.geom_type.dropna().iloc[0]
    if "Polygon" in gt:
        z = Z_VECTOR - 1 if zorder is None else zorder
        gdf.plot(ax=ax, facecolor=(facecolor if facecolor is not None else (color or "none")),
                 edgecolor=edgecolor or "#555", linewidth=linewidth, alpha=alpha,
                 zorder=z, label=label)
    elif "Line" in gt:
        z = Z_VECTOR if zorder is None else zorder
        gdf.plot(ax=ax, color=color or "#3a7bd5", linewidth=linewidth, alpha=alpha,
                 zorder=z, label=label)
    else:
        z = Z_POINT if zorder is None else zorder
        ax.scatter(gdf.geometry.x, gdf.geometry.y, s=markersize, c=color or "#c0392b",
                   marker=marker, edgecolor=edgecolor or "white", linewidth=0.6,
                   alpha=alpha, zorder=z, label=label)

    field = _pick_label_field(gdf, label_field) if labels not in (None, False) else None
    if field:
        sel = _select_labels(gdf, labels)
        _draw_labels(ax, sel, field, size=label_size, color=label_color,
                     halo=label_halo, zorder=Z_POINT + 1)
    if legend and label:
        ax.legend(loc=legend_loc, fontsize=7, framealpha=0.92)
    return ax


# --------------------------------------------------------------------------- #
#  BASEMAP (XYZ tiles)
# --------------------------------------------------------------------------- #
def _providers():
    import contextily as cx
    P = cx.providers
    return {
        "satellite": P.Esri.WorldImagery,
        "osm": P.OpenStreetMap.Mapnik,
        "light": P.CartoDB.Positron,
        "dark": P.CartoDB.DarkMatter,
        "terrain": P.OpenTopoMap,
        "toner": P.CartoDB.Voyager,
    }


def add_basemap(ax, *, style: str = "satellite", alpha: float = 1.0,
                zoom: Union[int, str] = "auto", attribution: bool = False,
                zorder: int = Z_BASEMAP):
    """Add an XYZ **tile basemap** under the current view.

    ``style`` ∈ {``satellite``, ``osm``, ``light``, ``dark``, ``terrain``,
    ``toner``}. Works directly on lon/lat axes (tiles are reprojected to
    EPSG:4326). Set the map extent first (e.g. draw your data), then call this.
    Needs ``pip install "acadgis[basemap]"``. Returns ``ax``.
    """
    try:
        import contextily as cx
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            'add_basemap needs contextily. Install with:\n'
            '    pip install "acadgis[basemap]"') from exc
    provs = _providers()
    if style not in provs:
        raise ValueError(f"Unknown style {style!r}. Options: {list(provs)}")
    cx.add_basemap(ax, crs="EPSG:4326", source=provs[style], alpha=alpha,
                   zoom=zoom, attribution=attribution)
    if ax.images:
        ax.images[-1].set_zorder(zorder)
    return ax


def add_satellite(ax, **kw):
    """Shortcut for :func:`add_basemap` with ``style='satellite'``."""
    kw.setdefault("style", "satellite")
    return add_basemap(ax, **kw)


# --------------------------------------------------------------------------- #
#  TOPOGRAPHY (DEM hillshade)
# --------------------------------------------------------------------------- #
def add_topography(ax, area=None, *, cmap: str = "terrain", hillshade: bool = True,
                   ocean_color: Optional[str] = None, sea_level: float = 0.0,
                   azimuth: float = 315, altitude: float = 45,
                   vert_exag: float = 0.0008, vmin: Optional[float] = None,
                   opacity: float = 1.0, colorbar: bool = False,
                   colorbar_label: str = "Elevation (m)", max_size: int = 1000,
                   buffer: float = 0.0, zorder: int = Z_RASTER, download: bool = True):
    """Overlay a hypsometric + hillshaded **topography** layer on ``ax``.

    Downloads a DEM for ``area`` (name / bbox / GeoDataFrame; defaults to the
    current view) and renders shaded relief. Set ``ocean_color`` to paint sea.
    Needs ``acadgis[terrain]``. Returns ``ax``.
    """
    from .terrain import load_dem, relief
    if area is None:
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        area = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    dem = load_dem(area, max_size=max_size, buffer=buffer, download=download)
    relief(dem, ax=ax, cmap=cmap, hillshade=hillshade, ocean_color=ocean_color,
           sea_level=sea_level, azimuth=azimuth, altitude=altitude,
           vert_exag=vert_exag, vmin=vmin, legend=colorbar,
           legend_label=colorbar_label, graticule=False, north_arrow=False,
           scale_bar=False)
    if ax.images:
        ax.images[-1].set_zorder(zorder)
        if opacity < 1.0:
            ax.images[-1].set_alpha(opacity)
    return ax


# --------------------------------------------------------------------------- #
#  CURATED VECTOR SHORTCUTS
# --------------------------------------------------------------------------- #
def load_places(download: bool = True) -> gpd.GeoDataFrame:
    """Natural Earth populated places (cities) with ``name`` + ``pop`` columns."""
    from .hydro import _NE_BASE, _cache_dir
    cache = _cache_dir() / "ne_10m_populated_places.geojson"
    if not cache.exists() and download:
        import io
        import requests
        r = requests.get(_NE_BASE + "ne_10m_populated_places_simple.geojson", timeout=120)
        r.raise_for_status()
        g = gpd.read_file(io.BytesIO(r.content))
        ncol = "name" if "name" in g.columns else ("NAME" if "NAME" in g.columns else None)
        pcol = next((c for c in ("pop_max", "POP_MAX", "max_pop") if c in g.columns), None)
        g = g.rename(columns={ncol: "name", **({pcol: "pop"} if pcol else {})})
        keep = [c for c in ("name", "pop", "geometry") if c in g.columns]
        g = g[keep]
        g.to_file(cache, driver="GeoJSON")
    g = gpd.read_file(cache)
    return g.set_crs("EPSG:4326") if g.crs is None else g


def add_cities(ax, area=None, *, top: Optional[int] = None, min_pop: Optional[float] = None,
               labels: Union[bool, str, int] = True, label_field: str = "name",
               label_size: float = 8, label_color: str = "#222", label_halo: bool = True,
               color: str = "#1b1b1b", markersize: float = 28, marker: str = "o",
               edgecolor: str = "white", alpha: float = 1.0, zorder: int = Z_POINT,
               download: bool = True):
    """Plot Natural Earth **cities** clipped to ``area``/view, ranked by population.

    ``top=N`` keeps the N largest; ``min_pop`` filters by population. ``labels``
    follows the hide / one / N / all policy (see :func:`add_layer`). Returns ``ax``.
    """
    g = load_places(download=download)
    box_geom = None
    geoms = _as_geoms(area)
    if geoms is not None:
        from shapely.ops import unary_union
        box_geom = unary_union(geoms)
    else:
        box_geom = _ax_extent_box(ax)
    g = gpd.clip(g, box_geom)
    if "pop" in g.columns:
        if min_pop is not None:
            g = g[g["pop"].fillna(0) >= min_pop]
        g = g.sort_values("pop", ascending=False)
    if top is not None:
        g = g.head(top)
    if len(g) == 0:
        return ax
    ax.scatter(g.geometry.x, g.geometry.y, s=markersize, c=color, marker=marker,
               edgecolor=edgecolor, linewidth=0.6, alpha=alpha, zorder=zorder,
               label="Cities")
    field = _pick_label_field(g, label_field) if labels not in (None, False) else None
    if field:
        sel = _select_labels(g, labels, rank_field="pop")
        _draw_labels(ax, sel, field, size=label_size, color=label_color,
                     halo=label_halo, zorder=zorder + 1)
    return ax


_OSM_HEADERS = {"User-Agent": "acadgis/0.1 (+https://acadgis.com)"}
_OVERPASS = ("https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter")
_ROAD_WIDTH = {"motorway": 1.6, "trunk": 1.3, "primary": 1.0, "secondary": 0.7,
               "tertiary": 0.5}


def fetch_osm_roads(area, *, classes=("motorway", "trunk", "primary"),
                    timeout: int = 180, download: bool = True,
                    use_cache: bool = True) -> gpd.GeoDataFrame:
    """Download an OpenStreetMap **road** network for ``area`` (Overpass).

    ``classes`` selects ``highway`` types (default major roads). Cached per area.
    Returns a GeoDataFrame with a ``kind`` column. Larger areas / more classes
    are slower.
    """
    import requests
    from shapely.geometry import LineString
    from .hydro import _area_bbox_geom, _cache_dir
    bbox, geom, key = _area_bbox_geom(area, download=download)
    minx, miny, maxx, maxy = bbox
    classes = tuple(classes)
    cache = None
    if use_cache and key:
        cache = _cache_dir() / f"osm_roads_{key}_{'-'.join(classes)}.geojson"
        if cache.exists():
            g = gpd.read_file(cache)
            return g.set_crs("EPSG:4326") if g.crs is None else g
    regex = "|".join(classes)
    query = (f'[out:json][timeout:{timeout}];'
             f'(way["highway"~"^({regex})$"]({miny},{minx},{maxy},{maxx}););out geom;')
    data = None
    for server in _OVERPASS:
        try:
            r = requests.post(server, data={"data": query}, headers=_OSM_HEADERS,
                              timeout=timeout + 30)
            if r.status_code == 200:
                data = r.json(); break
        except Exception:
            continue
    if not data:
        raise RuntimeError("Overpass road query failed (network/server). Try again "
                           "or pass a smaller area.")
    rows = []
    for el in data.get("elements", []):
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        if len(pts) >= 2:
            rows.append({"kind": el.get("tags", {}).get("highway"),
                         "geometry": LineString(pts)})
    g = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    if use_cache and cache is not None and len(g):
        try:
            g.to_file(cache, driver="GeoJSON")
        except Exception:
            pass
    return g


def add_roads(ax, area=None, *, classes=("motorway", "trunk", "primary"),
              color: str = "#6b4f3a", width: float = 0.6, max_width: float = 1.8,
              by_class: bool = True, alpha: float = 0.9, label: Optional[str] = None,
              legend: bool = False, zorder: int = Z_VECTOR, download: bool = True):
    """Overlay OpenStreetMap **roads** on ``ax`` (major classes by default).

    Widths scale by ``highway`` class when ``by_class=True``. ``area`` defaults to
    the current view. Needs network access. Returns ``ax``.
    """
    if area is None:
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        area = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    g = fetch_osm_roads(area, classes=classes, download=download)
    if len(g) == 0:
        return ax
    if by_class and "kind" in g.columns:
        for kind, sub in g.groupby("kind"):
            lw = max_width * _ROAD_WIDTH.get(kind, 0.4)
            sub.plot(ax=ax, color=color, linewidth=lw, alpha=alpha, zorder=zorder)
    else:
        g.plot(ax=ax, color=color, linewidth=width, alpha=alpha, zorder=zorder,
               label=label)
    if legend and label:
        ax.legend(loc="upper right", fontsize=7, framealpha=0.92)
    return ax


# --------------------------------------------------------------------------- #
#  CURATED RASTER DATA SOURCES (fetch a known global dataset for an area)
# --------------------------------------------------------------------------- #
# Official ESA WorldCover classes + colours (v100 2020 / v200 2021).
WORLDCOVER_CLASSES = {
    10: ("#006400", "Tree cover"), 20: ("#ffbb22", "Shrubland"),
    30: ("#ffff4c", "Grassland"), 40: ("#f096ff", "Cropland"),
    50: ("#fa0000", "Built-up"), 60: ("#b4b4b4", "Bare / sparse"),
    70: ("#f0f0f0", "Snow / ice"), 80: ("#0064c8", "Water"),
    90: ("#0096a0", "Wetland"), 95: ("#00cf75", "Mangroves"),
    100: ("#fae6a0", "Moss / lichen"),
}
_WORLDCOVER_S3 = "https://esa-worldcover.s3.eu-central-1.amazonaws.com"
_STAC_SEARCH = "https://earth-search.aws.element84.com/v1/search"


def _area_bounds(area, *, download=True):
    """area (name / bbox / GeoDataFrame) -> ((minx,miny,maxx,maxy), polygon|None)."""
    if hasattr(area, "total_bounds"):
        geom = area.geometry.union_all() if hasattr(area, "geometry") else None
        return tuple(map(float, area.total_bounds)), geom
    if isinstance(area, (list, tuple)) and len(area) == 4:
        return tuple(map(float, area)), None
    if isinstance(area, str):
        from .data import load_boundaries
        g = None
        for lvl in (0, 1):
            try:
                g = load_boundaries(area, lvl, download=download); break
            except Exception:
                continue
        if g is None:
            raise ValueError(f"Could not resolve area {area!r}.")
        return tuple(map(float, g.total_bounds)), g.geometry.union_all()
    raise TypeError("area must be a name, bbox (minx,miny,maxx,maxy), or GeoDataFrame")


def _worldcover_tiles(bbox):
    """3-degree WorldCover tile names covering ``bbox`` (named by lower-left corner)."""
    import math
    minx, miny, maxx, maxy = bbox
    out = []
    for la in range(math.floor(miny / 3) * 3, math.floor(maxy / 3) * 3 + 1, 3):
        for lo in range(math.floor(minx / 3) * 3, math.floor(maxx / 3) * 3 + 1, 3):
            ns, ew = ("N" if la >= 0 else "S"), ("E" if lo >= 0 else "W")
            out.append(f"{ns}{abs(la):02d}{ew}{abs(lo):03d}")
    return out


def add_landcover(ax, area, *, year: int = 2021, legend: bool = True,
                  legend_loc: str = "lower left", opacity: float = 1.0,
                  clip: bool = True, zorder: int = Z_RASTER, download: bool = True):
    """Real **ESA WorldCover 10 m** land cover for ``area`` (name / bbox / GeoDataFrame).

    Reads the public cloud-optimized GeoTIFFs with windowed remote requests (no
    full download) and renders the 11-class map with the official palette + a
    legend. ``year`` 2021 (v200) or 2020 (v100). Needs ``acadgis[terrain]``.
    """
    try:
        import rioxarray  # noqa: F401
        from rioxarray.merge import merge_arrays
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            'add_landcover needs rasterio + rioxarray. Install with:\n'
            '    pip install "acadgis[terrain]"') from exc
    import rioxarray
    bbox, geom = _area_bounds(area, download=download)
    ver, vtag, yr = (("v200/2021", "v200", 2021) if year >= 2021
                     else ("v100/2020", "v100", 2020))
    arrs = []
    for t in _worldcover_tiles(bbox):
        url = f"{_WORLDCOVER_S3}/{ver}/map/ESA_WorldCover_10m_{yr}_{vtag}_{t}_Map.tif"
        try:
            arrs.append(rioxarray.open_rasterio(url, masked=False).rio.clip_box(*bbox))
        except Exception:
            continue
    if not arrs:
        raise RuntimeError("No ESA WorldCover tiles cover this area (or network failed).")
    da = arrs[0] if len(arrs) == 1 else merge_arrays(arrs)
    return add_raster(ax, da, area=(geom if (clip and geom is not None) else None),
                      categorical=True, classes=WORLDCOVER_CLASSES, legend=legend,
                      legend_loc=legend_loc, legend_title=f"Land cover (ESA {yr})",
                      opacity=opacity, zorder=zorder)


def add_ndvi(ax, area, *, start: str = "2023-01-01", end: str = "2024-12-31",
             max_cloud: float = 10, collection: str = "sentinel-2-l2a",
             cmap: str = "RdYlGn", vmin: float = -0.1, vmax: float = 0.9,
             colorbar: bool = True, clip: bool = True, zorder: int = Z_RASTER,
             download: bool = True):
    """Real **Sentinel-2 NDVI** for ``area`` — the least-cloudy scene in a window.

    Queries the Earth Search STAC API, reads the red & NIR bands (windowed) and
    computes ``NDVI = (NIR - Red) / (NIR + Red)``. Narrow ``start``/``end`` to a
    season for a date-specific map. The chosen scene date is stored on
    ``ax._acadgis_ndvi_date``. Needs ``acadgis[terrain]`` + network.
    """
    try:
        import rioxarray  # noqa: F401
        from rasterio.warp import transform_bounds
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            'add_ndvi needs rasterio + rioxarray. Install with:\n'
            '    pip install "acadgis[terrain]"') from exc
    import requests
    import rioxarray
    bbox, geom = _area_bounds(area, download=download)
    body = {"collections": [collection], "bbox": list(bbox),
            "datetime": f"{start}T00:00:00Z/{end}T00:00:00Z",
            "query": {"eo:cloud_cover": {"lt": max_cloud}}, "limit": 50}
    r = requests.post(_STAC_SEARCH, json=body, timeout=60)
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        raise RuntimeError("No clear Sentinel-2 scene found — widen start/end or "
                           "raise max_cloud.")
    feats.sort(key=lambda f: f["properties"].get("eo:cloud_cover", 100))
    a = feats[0]["assets"]
    date = feats[0]["properties"]["datetime"][:10]
    red_k = "red" if "red" in a else "B04"
    nir_k = "nir" if "nir" in a else "B08"
    red = rioxarray.open_rasterio(a[red_k]["href"], masked=True)
    crs = red.rio.crs
    bx = transform_bounds("EPSG:4326", crs, *bbox)
    red = red.rio.clip_box(*bx).squeeze().astype("float32")
    nir = rioxarray.open_rasterio(a[nir_k]["href"], masked=True).rio.clip_box(*bx).squeeze().astype("float32")
    ndvi = (nir - red) / (nir + red)
    ndvi.rio.write_crs(crs, inplace=True)
    ndvi = ndvi.rio.reproject("EPSG:4326")
    add_raster(ax, ndvi, area=(geom if (clip and geom is not None) else None),
               cmap=cmap, vmin=vmin, vmax=vmax, colorbar=colorbar,
               colorbar_label=f"NDVI — {collection} {date}", zorder=zorder)
    ax._acadgis_ndvi_date = date
    return ax
