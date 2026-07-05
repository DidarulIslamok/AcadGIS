"""acadgis — publication-ready academic GIS study-area maps in a few lines.

Quick start
-----------
>>> import acadgis as agis
>>> gdf = agis.load_boundaries("Bangladesh", level="district")
>>> agis.plot(gdf, palette="spectral", title="Bangladesh Districts")

Choropleth from a data table
----------------------------
>>> agis.choropleth(gdf, data=df, value="cases", palette="magma")

Multi-panel locator figure (the signature layout)
-------------------------------------------------
>>> sa = agis.StudyArea("Iraq").zoom_into("Babil")
>>> fig = sa.figure(suptitle="Study Area")
>>> sa.save("study_area.png", dpi=300)

The companion web app lives at https://acadgis.com
"""
from __future__ import annotations

# --- batteries included: re-export the common scientific stack so users can
# do everything through `agis.` without separate imports -------------------- #
import geopandas as gpd  # noqa: E402
import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ._version import __version__
from .core import choropleth, plot, points
from .data import (
    list_available,
    load_boundaries,
    name_column,
    resolve_level,
)
from .inset import StudyArea
from .layouts import TEMPLATES, study_area
from .zoominset import callout, zoom_axes
from .connectors import connect
from .matching import match_one, match_table, normalize
from .palettes import ALL_PALETTES, get_cmap, get_colors
from .themes import Theme, get_theme, list_themes
from .world import highlight_country, load_world, world_locator

# Terrain & hydrology are optional (terrain needs rasterio); import lazily so
# the core package still works without the extra dependencies.
try:
    from .terrain import DEM, hillshade, load_dem, relief
    _HAVE_TERRAIN = True
except Exception:  # pragma: no cover
    _HAVE_TERRAIN = False

    def _need_terrain(*_a, **_k):
        raise ImportError(
            'Terrain features need the optional extra. Install with:\n'
            '    pip install "acadgis[terrain]"'
        )

    load_dem = relief = hillshade = _need_terrain  # type: ignore
    DEM = None  # type: ignore

from .hydro import (
    add_rivers,
    add_sea,
    add_water,
    atlas,
    fetch_osm_rivers,
    load_lakes,
    load_rivers,
)

# Generic layer system (raster / vector / basemap / topography). The module
# imports cleanly with the core deps; heavy backends (rasterio/rioxarray for
# raster & topography, contextily for basemaps) are imported lazily per call.
from .layers import (
    add_basemap,
    add_cities,
    add_landcover,
    add_layer,
    add_ndvi,
    add_raster,
    add_roads,
    add_satellite,
    add_topography,
    fetch_osm_roads,
    load_places,
)

# Thematic map types (heatmap, isopleth, isolines, dot-density, bivariate,
# cartogram) — completes the standard thematic catalogue.
from .thematic import (
    BIVARIATE_PALETTE,
    add_contours,
    add_heatmap,
    add_isopleth,
    bivariate,
    cartogram,
    dot_density,
    interpolate_field,
)

try:
    from .drainage import add_streams, drainage
    _HAVE_DRAINAGE = True
except Exception:  # pragma: no cover
    _HAVE_DRAINAGE = False

    def _need_drainage(*_a, **_k):
        raise ImportError(
            'Drainage extraction needs the optional extra. Install with:\n'
            '    pip install "acadgis[drainage]"'
        )

    drainage = add_streams = _need_drainage  # type: ignore

__all__ = [
    "__version__",
    # data
    "load_boundaries",
    "list_available",
    "name_column",
    "resolve_level",
    # plotting
    "plot",
    "choropleth",
    "points",
    "StudyArea",
    "study_area",
    "zoom_axes",
    "callout",
    "connect",
    "TEMPLATES",
    # world maps
    "load_world",
    "highlight_country",
    "world_locator",
    # terrain (optional: needs rasterio)
    "load_dem",
    "relief",
    "hillshade",
    "DEM",
    # hydrology
    "load_rivers",
    "load_lakes",
    "add_rivers",
    "add_sea",
    "add_water",
    "atlas",
    "fetch_osm_rivers",
    # layer system (raster / vector / basemap / topography)
    "add_raster",
    "add_layer",
    "add_basemap",
    "add_satellite",
    "add_topography",
    "add_cities",
    "add_roads",
    "fetch_osm_roads",
    "load_places",
    # curated raster data
    "add_landcover",
    "add_ndvi",
    # thematic map types
    "interpolate_field",
    "add_isopleth",
    "add_contours",
    "add_heatmap",
    "dot_density",
    "bivariate",
    "cartogram",
    "BIVARIATE_PALETTE",
    # drainage (optional: needs pysheds)
    "drainage",
    "add_streams",
    # styling
    "Theme",
    "get_theme",
    "list_themes",
    "get_colors",
    "get_cmap",
    "ALL_PALETTES",
    # matching
    "normalize",
    "match_one",
    "match_table",
    # convenience
    "save",
    "show",
    # re-exported stack
    "plt",
    "mpl",
    "np",
    "pd",
    "gpd",
]


def show(*args, **kwargs):
    """Display all open figures (wrapper around ``matplotlib.pyplot.show``).

    Lets you finish a plain script with ``agis.show()`` instead of importing
    matplotlib yourself.
    """
    return plt.show(*args, **kwargs)


def save(obj, path, *, dpi: int = 300, **kwargs):
    """Save a matplotlib Axes/Figure or a :class:`StudyArea` to ``path``.

    >>> ax = agis.plot(gdf)
    >>> agis.save(ax, "map.png", dpi=300)
    """
    if isinstance(obj, StudyArea):
        return obj.save(path, dpi=dpi, **kwargs)
    fig = getattr(obj, "figure", None)
    # matplotlib Axes has .figure (a Figure); Figure has .savefig
    if hasattr(obj, "savefig"):
        fig = obj
    elif fig is not None and hasattr(fig, "savefig"):
        pass
    else:
        raise TypeError(f"Don't know how to save object of type {type(obj)!r}")
    fig.savefig(path, dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor(), **kwargs)
    return path
