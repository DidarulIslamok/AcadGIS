"""Hydrography: rivers and water bodies as styled vector layers.

Gives the clean "atlas" cartographic look (blue river lines + water-body
polygons over tinted land). Data is bundled Natural Earth (50 m), so it works
offline; finer detail can be added later via download.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import geopandas as gpd

_SAMPLES = Path(__file__).resolve().parent / "data" / "samples"
_NE_BASE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
            "master/geojson/")

# Realistic water cartography palette (from the AcadGIS web app).
RIVER_COLOR = "#3b82f6"
WATER_COLOR = "#a8d8ea"
OCEAN_COLOR = "#cce5f0"
LAND_COLOR = "#f4efe1"

# Relative line widths by OSM waterway kind (× a base width).
KIND_WIDTH = {"river": 1.0, "canal": 0.62, "stream": 0.45, "drain": 0.32,
              "ditch": 0.28}

_OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]
_OSM_HEADERS = {"User-Agent": "acadgis (academic GIS map package)"}


def _cache_dir():
    import os
    d = Path(os.environ.get("ACADGIS_CACHE", Path.home() / ".acadgis" / "cache"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_ne(kind, scale, download):
    """kind in {rivers, lakes}; scale in {50m, 10m}. 50m is bundled; 10m
    downloads & caches; falls back to 50m offline."""
    bundled = _SAMPLES / f"{kind}_50m.geojson"
    if scale == "50m":
        g = gpd.read_file(bundled)
        return g.set_crs("EPSG:4326") if g.crs is None else g

    cache = _cache_dir() / f"{kind}_10m.geojson"
    if not cache.exists() and download:
        try:
            import io
            import requests
            name = ("ne_10m_rivers_lake_centerlines" if kind == "rivers"
                    else "ne_10m_lakes")
            r = requests.get(_NE_BASE + name + ".geojson", timeout=120)
            r.raise_for_status()
            g = gpd.read_file(io.BytesIO(r.content))
            keep = [c for c in ("name", "scalerank", "geometry") if c in g.columns]
            g = g[keep]
            g.to_file(cache, driver="GeoJSON")
        except Exception:
            cache = bundled  # offline / failed -> coarse fallback
    elif not cache.exists():
        cache = bundled
    g = gpd.read_file(cache)
    return g.set_crs("EPSG:4326") if g.crs is None else g


def load_rivers(scale: str = "50m", download: bool = True) -> gpd.GeoDataFrame:
    """Natural Earth river centerlines (EPSG:4326).

    ``scale="50m"`` is bundled/offline; ``"10m"`` is denser (downloads &
    caches on first use, falls back to 50m offline). Has a ``scalerank``
    column (lower = larger river) used to weight line widths.
    """
    return _load_ne("rivers", scale, download)


def load_lakes(scale: str = "50m", download: bool = True) -> gpd.GeoDataFrame:
    """Natural Earth lakes / water bodies (EPSG:4326)."""
    return _load_ne("lakes", scale, download)


def _area_bbox_geom(area, download=True):
    """Resolve area (name | bbox | GeoDataFrame) -> (bbox, polygon|None, key)."""
    from .data import load_boundaries
    from .matching import normalize
    if hasattr(area, "total_bounds"):
        b = tuple(area.total_bounds)
        geom = area.geometry.union_all() if hasattr(area, "geometry") else None
        return b, geom, None
    if isinstance(area, (tuple, list)) and len(area) == 4:
        return tuple(map(float, area)), None, None
    if isinstance(area, str):
        gdf = None
        for lvl in (0, 1):
            try:
                gdf = load_boundaries(area, lvl, download=download); break
            except Exception:
                continue
        if gdf is None:
            raise ValueError(f"Could not resolve area {area!r}.")
        return tuple(gdf.total_bounds), gdf.geometry.union_all(), normalize(area)
    raise TypeError("area must be a name, bbox, or GeoDataFrame.")


def fetch_osm_rivers(area, *, kinds=("river", "canal"), clip=True,
                     timeout=180, download=True, use_cache=True):
    """Download a **dense OpenStreetMap** river/canal/stream network for an area.

    This is the high-fidelity option (e.g. the full delta) — it queries the
    Overpass API for ``waterway`` ways and returns a GeoDataFrame with a
    ``kind`` column (river/canal/stream/…). Results are cached. Add ``"stream"``
    to ``kinds`` for maximum density (larger/slower).
    """
    import geopandas as gpd
    import requests
    from shapely.geometry import LineString

    bbox, geom, key = _area_bbox_geom(area, download=download)
    minx, miny, maxx, maxy = bbox
    kinds = tuple(kinds)

    cache = None
    if use_cache and key:
        cache = _cache_dir() / f"osm_rivers_{key}_{'-'.join(kinds)}.geojson"
        if cache.exists():
            g = gpd.read_file(cache)
            return g.set_crs("EPSG:4326") if g.crs is None else g

    regex = "|".join(kinds)
    query = (f'[out:json][timeout:{timeout}];'
             f'(way["waterway"~"{regex}"]({miny},{minx},{maxy},{maxx}););'
             f'out geom;')

    data = None
    for server in _OVERPASS_SERVERS:
        try:
            r = requests.post(server, data={"data": query},
                              headers=_OSM_HEADERS, timeout=timeout + 30)
            if r.status_code == 200:
                data = r.json(); break
        except Exception:
            continue
    if data is None:
        raise RuntimeError("Overpass API unavailable; could not fetch OSM "
                           "rivers. Try again, or use the Natural Earth source.")

    rows = []
    for el in data.get("elements", []):
        g = el.get("geometry")
        if not g or len(g) < 2:
            continue
        line = LineString([(p["lon"], p["lat"]) for p in g])
        rows.append({"kind": el.get("tags", {}).get("waterway", "river"),
                     "name": el.get("tags", {}).get("name"), "geometry": line})
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    if clip and geom is not None and len(gdf):
        try:
            gdf = gpd.clip(gdf, geom)
        except Exception:
            pass
    if cache is not None and len(gdf):
        try:
            gdf.to_file(cache, driver="GeoJSON")
        except Exception:
            pass
    return gdf


def _ax_bbox(ax):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    return (x0, y0, x1, y1)


def _clip_to_ax(gdf, ax, pad=0.15):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    dx, dy = (x1 - x0) * pad, (y1 - y0) * pad
    try:
        return gdf.cx[x0 - dx:x1 + dx, y0 - dy:y1 + dy]
    except Exception:
        return gdf


def _clip_to_area(gdf, area, download=True, pad=0.1):
    from .data import load_boundaries
    if hasattr(area, "total_bounds"):
        minx, miny, maxx, maxy = area.total_bounds
    elif isinstance(area, (tuple, list)) and len(area) == 4:
        minx, miny, maxx, maxy = area
    else:
        b = None
        for lvl in (0, 1):
            try:
                b = load_boundaries(area, lvl, download=download); break
            except Exception:
                continue
        if b is None:
            return gdf
        minx, miny, maxx, maxy = b.total_bounds
    dx, dy = (maxx - minx) * pad, (maxy - miny) * pad
    return gdf.cx[minx - dx:maxx + dx, miny - dy:maxy + dy]


def add_rivers(ax, area=None, *, source="ne", rivers=None, scale="50m",
               osm_kinds=("river", "canal"), color=RIVER_COLOR, by_order=True,
               width=0.8, max_width=2.6, alpha=0.95, zorder=6, labels=False,
               label_color=None, label_size=7, download=True):
    """Overlay river centerlines on ``ax``.

    ``source``:
      - ``"ne"`` (default): bundled Natural Earth (``scale`` 50m/10m).
      - ``"osm"``: **dense** OpenStreetMap rivers/canals/streams (downloaded &
        cached) — the realistic delta look; width is set per ``kind``.

    ``area`` (name/bbox/GeoDataFrame) clips the rivers; if None, clips to the
    current axes extent. ``labels=True`` draws river names (italic).
    """
    if rivers is None:
        if source == "osm":
            rivers = fetch_osm_rivers(area if area is not None else _ax_bbox(ax),
                                      kinds=osm_kinds, download=download)
        else:
            rivers = load_rivers(scale=scale, download=download)
    rivers = (_clip_to_area(rivers, area, download=download)
              if area is not None else _clip_to_ax(rivers, ax))
    if len(rivers) == 0:
        return ax

    if "kind" in rivers.columns:  # OSM: width (and emphasis) by waterway kind
        # draw small channels first, main rivers last so they sit on top
        order = {"river": 3, "canal": 2, "stream": 1, "drain": 0, "ditch": 0}
        kind_alpha = {"river": alpha, "canal": alpha * 0.7}
        for kind in sorted(rivers["kind"].dropna().unique(),
                           key=lambda k: order.get(k, 0)):
            sub = rivers[rivers["kind"] == kind]
            w = max_width * KIND_WIDTH.get(kind, 0.35)
            sub.plot(ax=ax, color=color, linewidth=float(w),
                     alpha=kind_alpha.get(kind, alpha * 0.6), zorder=zorder)
    elif by_order and "scalerank" in rivers.columns:
        sr = rivers["scalerank"].fillna(rivers["scalerank"].max())
        lo, hi = sr.min(), sr.max()
        rng = (hi - lo) or 1
        lw = width + (max_width - width) * (hi - sr) / rng
        for w, (_, row) in zip(lw, rivers.iterrows()):
            gpd.GeoSeries([row.geometry], crs=rivers.crs).plot(
                ax=ax, color=color, linewidth=float(w), alpha=alpha,
                zorder=zorder)
    else:
        rivers.plot(ax=ax, color=color, linewidth=width, alpha=alpha,
                    zorder=zorder)

    if labels and "name" in rivers.columns:
        import matplotlib.patheffects as pe
        lc = label_color or color
        seen = set()
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        for _, row in rivers.iterrows():
            nm = row.get("name")
            if not nm or nm in seen or row.geometry is None:
                continue
            p = row.geometry.interpolate(0.5, normalized=True)
            if not (x0 <= p.x <= x1 and y0 <= p.y <= y1):
                continue
            seen.add(nm)
            ax.annotate(str(nm), (p.x, p.y), fontsize=label_size, color=lc,
                        fontstyle="italic", ha="center", va="center",
                        zorder=zorder + 2,
                        path_effects=[pe.withStroke(linewidth=2,
                                                    foreground="white")])
    return ax


def add_water(ax, area=None, *, lakes=None, color="#a6cee3",
              edgecolor="#6aa6cf", linewidth=0.4, alpha=1.0, zorder=5,
              download=True):
    """Overlay lake / water-body polygons on ``ax``."""
    lakes = load_lakes() if lakes is None else lakes
    lakes = (_clip_to_area(lakes, area, download=download)
             if area is not None else _clip_to_ax(lakes, ax))
    if len(lakes) == 0:
        return ax
    lakes.plot(ax=ax, color=color, edgecolor=edgecolor, linewidth=linewidth,
               alpha=alpha, zorder=zorder)
    return ax


def atlas(area, *, level="country", neighbors=True, rivers="ne",
          rivers_scale="10m", osm_kinds=("river", "canal"),
          land_color=LAND_COLOR, ocean_color=OCEAN_COLOR,
          neighbor_color="#e6e6e6", river_color=RIVER_COLOR,
          water_color=WATER_COLOR, labels=True, river_labels=True, cities=None,
          pad=0.18, title: Optional[str] = None, figsize=(9, 10),
          download=True, north_arrow=True, scale_bar=True, graticule=True,
          theme="academic"):
    """A clean WorldAtlas-style figure with realistic water cartography.

    Tinted study country over greyed, labelled neighbours; rivers (with names)
    and water bodies; optional ``cities`` points.

    ``rivers="osm"`` uses the **dense** OpenStreetMap network (realistic delta /
    drainage detail, downloaded & cached); ``"ne"`` uses bundled Natural Earth.
    ``cities`` is a DataFrame (``lon``/``lat``/``name``) or ``{name: (lon,lat)}``.

    Returns the matplotlib Axes.
    """
    import matplotlib.pyplot as plt

    from . import decorations as deco
    from .core import _apply_extent, _label_regions, points
    from .data import load_boundaries, name_column, resolve_level
    from .themes import get_theme
    from .world import load_world

    th = get_theme(theme)
    lvl = resolve_level(level)
    gdf = load_boundaries(area, lvl, download=download)
    minx, miny, maxx, maxy = gdf.total_bounds
    dx, dy = (maxx - minx) * pad, (maxy - miny) * pad
    view = (minx - dx, miny - dy, maxx + dx, maxy + dy)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(ocean_color)
    ax.set_facecolor(ocean_color)

    # neighbour context: surrounding countries greyed + labelled
    if neighbors:
        world = load_world()
        country_name = gdf["NAME_0"].iloc[0] if "NAME_0" in gdf.columns else None
        nb = world.cx[view[0]:view[2], view[1]:view[3]]
        nb_others = nb[nb["NAME_0"] != country_name] if country_name else nb
        nb_others.plot(ax=ax, color=neighbor_color, edgecolor="#bdbdbd",
                       linewidth=0.5, zorder=2)
        for _, row in nb_others.iterrows():
            p = row.geometry.representative_point()
            if view[0] <= p.x <= view[2] and view[1] <= p.y <= view[3]:
                ax.annotate(row["NAME_0"], (p.x, p.y), fontsize=th.label_size,
                            color="#9e9e9e", fontstyle="italic", ha="center",
                            va="center", zorder=3)

    # study country land
    gdf.plot(ax=ax, color=land_color, edgecolor=th.edge_color,
             linewidth=th.edge_width, zorder=4)

    ax.set_xlim(view[0], view[2])
    ax.set_ylim(view[1], view[3])
    import numpy as np
    mean_lat = (view[1] + view[3]) / 2.0
    ax.set_aspect(1.0 / max(np.cos(np.radians(mean_lat)), 1e-6))

    # water + rivers across the whole view (so they flow into neighbours)
    add_water(ax, area=view, color=water_color, download=download)
    river_area = gdf if rivers == "osm" else view  # OSM clips to country
    add_rivers(ax, area=river_area, source=rivers, scale=rivers_scale,
               osm_kinds=osm_kinds, color=river_color, labels=river_labels,
               label_color=river_color, download=download)

    if labels and lvl >= 1:
        _label_regions(ax, gdf, name_column(gdf, lvl),
                       fontsize=th.label_size, color=th.label_color)

    if cities is not None:
        points(ax, cities, color="#222222", size=18, fontsize=th.label_size,
               dy=(maxy - miny) * 0.01)

    if graticule:
        deco.graticule(ax, color=th.grid_color, lw=th.grid_width,
                       alpha=th.grid_alpha, fontsize=th.label_size,
                       label_color=th.label_color)
    if north_arrow:
        deco.north_arrow(ax, color=th.decoration_color)
    if scale_bar:
        deco.scale_bar(ax, color=th.decoration_color, fontsize=th.label_size)
    if title:
        ax.set_title(title, fontsize=th.title_size, fontweight=th.title_weight,
                     pad=10)
    return ax


# --------------------------------------------------------------------------- #
# Sea / ocean layer  (sources: "auto" 110m bundled · "ne10m" 10m land · "ocean" 10m ocean)
# --------------------------------------------------------------------------- #
SEA_COLOR = "#9ecae9"

_NE10M_URLS = {
    "ne_10m_land": [
        "https://naciscdn.org/naturalearth/10m/physical/ne_10m_land.zip",
        "https://github.com/nvkelso/natural-earth-vector/raw/master/zips/ne_10m_land.zip",
    ],
    "ne_10m_ocean": [
        "https://naciscdn.org/naturalearth/10m/physical/ne_10m_ocean.zip",
        "https://github.com/nvkelso/natural-earth-vector/raw/master/zips/ne_10m_ocean.zip",
    ],
}


def _ne10m(name):
    """Download (once) + cache + read a Natural Earth 10m physical layer."""
    import urllib.request
    z = _cache_dir() / f"{name}.zip"
    if not z.exists():
        last = None
        for url in _NE10M_URLS[name]:
            try:
                urllib.request.urlretrieve(url, z)
                break
            except Exception as exc:  # try the mirror
                last = exc
        else:
            raise RuntimeError(
                f"Could not download {name} (needs network on first use): {last}")
    g = gpd.read_file(f"zip://{z}")
    return g.set_crs("EPSG:4326") if g.crs is None else g


_LAND_CACHE = {}


def _land_union(source):
    """Cached land geometry (EPSG:4326) for the chosen source."""
    if source not in _LAND_CACHE:
        if source in ("ne10m", "land", "hd", "10m"):
            geom = _ne10m("ne_10m_land").union_all()
        else:  # "auto" / "110m"
            from .world import load_world
            geom = load_world().union_all()
        _LAND_CACHE[source] = geom
    return _LAND_CACHE[source]


def _country_geom(country):
    if country is None:
        return None, None
    crs = getattr(country, "crs", None)
    if hasattr(country, "geometry"):           # GeoDataFrame / GeoSeries
        return country.geometry.union_all(), crs
    return country, None                        # a shapely geometry


def add_sea(ax, country=None, *, source="auto", color=SEA_COLOR,
            extent=None, pad=0.0, background="white",
            neighbours=False, neighbour_color=LAND_COLOR,
            coastline=False, coastline_color="#5a8fb0",
            labels=None, set_view=True, zorder=0):
    """Draw the sea/ocean around a country — no extra imports needed.

    Parameters
    ----------
    country:
        The plotted region (GeoDataFrame/GeoSeries or shapely geometry). Its own
        detailed coast bounds the sea, so there are no coastline slivers. If
        ``None``, the sea is everything in view that is not land (good for world maps).
    source:
        ``"auto"`` — bundled Natural Earth 110 m (offline, fast).
        ``"ne10m"`` — Natural Earth 10 m land, downloaded+cached (crisp, recommended).
        ``"ocean"`` — Natural Earth 10 m ocean polygon, downloaded+cached.
    color:
        Ocean fill colour.
    extent, pad:
        Map frame ``(minx, miny, maxx, maxy)``; default = current axes view.
        ``pad`` extends it into the ocean (fraction if <1, else degrees).
    background:
        Axes/figure background (the land behind, if ``neighbours`` is off).
    neighbours, neighbour_color:
        Fill neighbour land (same source) instead of leaving it as ``background``.
    coastline, coastline_color:
        Draw the country's coastline on top.
    labels:
        ``{"Bay of Bengal": (lon, lat), ...}`` sea labels.

    Landlocked areas produce an empty sea and draw nothing.
    """
    from shapely.geometry import box
    from shapely.ops import unary_union

    cgeom, ccrs = _country_geom(country)
    out_crs = ccrs or "EPSG:4326"
    geographic = str(out_crs).upper() in ("EPSG:4326", "WGS84") or "4326" in str(out_crs)

    if extent is None:
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
    else:
        x0, y0, x1, y1 = extent
    if pad:
        dx = (x1 - x0) * pad if pad < 1 else pad
        dy = (y1 - y0) * pad if pad < 1 else pad
        x0, x1, y0, y1 = x0 - dx, x1 + dx, y0 - dy, y1 + dy
    if geographic:                              # keep the frame valid (antimeridian/poles)
        x0, x1 = max(x0, -180.0), min(x1, 180.0)
        y0, y1 = max(y0, -90.0), min(y1, 90.0)
    frame = box(x0, y0, x1, y1)

    def _to_out(geom_4326):
        if str(out_crs).upper() in ("EPSG:4326", "WGS84"):
            return geom_4326
        return gpd.GeoSeries([geom_4326], crs="EPSG:4326").to_crs(out_crs).iloc[0]

    if source in ("ocean", "ne10m_ocean"):
        ocean = _ne10m("ne_10m_ocean").to_crs(out_crs)
        sea_geom = gpd.clip(ocean, frame).union_all()
    else:
        land = _to_out(_land_union(source))
        mask = unary_union([land, cgeom]) if cgeom is not None else land
        sea_geom = frame.difference(mask)

    if background:
        ax.set_facecolor(background)
        try:
            ax.figure.set_facecolor(background)
        except Exception:
            pass
    if neighbours:
        land = _to_out(_land_union(source))
        gpd.GeoSeries([land], crs=out_crs).clip(frame).plot(
            ax=ax, facecolor=neighbour_color, edgecolor="none", zorder=zorder + 0.3)
    if sea_geom is not None and not sea_geom.is_empty:
        gpd.GeoSeries([sea_geom], crs=out_crs).plot(
            ax=ax, facecolor=color, edgecolor="none", zorder=zorder)
    if coastline and cgeom is not None:
        gpd.GeoSeries([cgeom.boundary], crs=out_crs).plot(
            ax=ax, color=coastline_color, linewidth=0.6, zorder=zorder + 6)
    if labels:
        for name, (lx, ly) in labels.items():
            ax.annotate(name, xy=(lx, ly), fontsize=10, fontstyle="italic",
                        color="#1f5d8c", ha="center", zorder=zorder + 6)
    if set_view:
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
    return ax
