"""Boundary data loading for acadgis.

Resolution order for any request:

1. **Bundled samples** shipped with the package (instant, offline) — used for
   the demo countries (Bangladesh, Iraq).
2. **Local cache** in the user's home (``~/.acadgis/cache``) from prior
   downloads.
3. **Live download** from GADM via :mod:`pygadm`, then cached for next time.

The public entry point is :func:`load_boundaries`.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

import geopandas as gpd

from .matching import match_one, normalize

# --- level vocabulary -------------------------------------------------------
# Friendly names -> GADM content level. We keep this generous so researchers
# can use whatever word their country uses.
LEVEL_ALIASES = {
    "country": 0, "nation": 0, "adm0": 0, "0": 0,
    "state": 1, "province": 1, "division": 1, "governorate": 1,
    "region": 1, "adm1": 1, "1": 1,
    "district": 2, "county": 2, "zila": 2, "zilla": 2, "adm2": 2, "2": 2,
    "subdistrict": 3, "upazila": 3, "tehsil": 3, "taluk": 3, "thana": 3,
    "adm3": 3, "3": 3,
    "ward": 4, "union": 4, "adm4": 4, "4": 4,
}

_BUNDLED = {
    ("bangladesh", 0): "bangladesh_adm0.geojson",
    ("bangladesh", 1): "bangladesh_adm1.geojson",
    ("bangladesh", 2): "bangladesh_adm2.geojson",
    ("iraq", 0): "iraq_adm0.geojson",
    ("iraq", 1): "iraq_adm1.geojson",
    ("united states", 1): "usa_adm1.geojson",
    ("india", 0): "india_adm0.geojson",
    ("india", 1): "india_adm1.geojson",
    ("india", 2): "india_adm2.geojson",
}

# Aliases so friendly country names resolve to a bundled key.
_COUNTRY_ALIASES = {
    "usa": "united states",
    "us": "united states",
    "u s a": "united states",
    "united states of america": "united states",
    "america": "united states",
}

_SAMPLES_DIR = Path(__file__).resolve().parent / "data" / "samples"


def _cache_dir() -> Path:
    d = Path(os.environ.get("ACADGIS_CACHE", Path.home() / ".acadgis" / "cache"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_level(level: Union[str, int]) -> int:
    """Translate a friendly level name (or int) to a GADM content level."""
    if isinstance(level, int):
        return level
    key = str(level).strip().lower()
    if key not in LEVEL_ALIASES:
        raise ValueError(
            f"Unknown level {level!r}. Try one of: "
            "country, state/province/division, district, subdistrict, "
            "or an integer 0-4."
        )
    return LEVEL_ALIASES[key]


def name_column(gdf: gpd.GeoDataFrame, level: Optional[int] = None) -> str:
    """Return the GADM name column for the deepest (or given) level present."""
    if level is not None:
        col = f"NAME_{level}"
        if col in gdf.columns:
            return col
    name_cols = sorted(
        [c for c in gdf.columns if c.startswith("NAME_")],
        key=lambda c: int(c.split("_")[1]),
    )
    if not name_cols:
        raise ValueError("No GADM NAME_* column found in this GeoDataFrame.")
    return name_cols[-1]


def list_available() -> list:
    """List bundled (country, level) datasets that work fully offline."""
    return sorted(_BUNDLED.keys())


def _from_bundled(country_key: str, level: int) -> Optional[gpd.GeoDataFrame]:
    fname = _BUNDLED.get((country_key, level))
    if fname is None:
        return None
    path = _SAMPLES_DIR / fname
    if path.exists():
        return gpd.read_file(path)
    return None


def _from_cache(country_key: str, level: int) -> Optional[gpd.GeoDataFrame]:
    path = _cache_dir() / f"{country_key}_adm{level}.geojson"
    if path.exists():
        return gpd.read_file(path)
    return None


def _download(country: str, level: int, country_key: str) -> gpd.GeoDataFrame:
    try:
        import pygadm
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Live boundary download needs the optional dependency 'pygadm'.\n"
            "Install it with:  pip install pygadm\n"
            "Or use one of the bundled offline countries: "
            f"{sorted({c for c, _ in _BUNDLED})}"
        ) from exc

    gdf = pygadm.Items(name=country, content_level=level)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    # cache for next time
    try:
        gdf.to_file(_cache_dir() / f"{country_key}_adm{level}.geojson", driver="GeoJSON")
    except Exception:  # pragma: no cover
        pass
    return gdf


def load_boundaries(
    country: str,
    level: Union[str, int] = "country",
    *,
    within: Optional[str] = None,
    download: bool = True,
) -> gpd.GeoDataFrame:
    """Load administrative boundaries for ``country`` at ``level``.

    Parameters
    ----------
    country:
        Country name, e.g. ``"Bangladesh"``.
    level:
        Friendly level name (``"country"``, ``"division"``/``"state"``,
        ``"district"``, ``"upazila"`` …) or GADM integer 0-4.
    within:
        Optional parent-region name to subset by (e.g. all districts
        *within* the ``"Dhaka"`` division). Uses fuzzy name matching.
    download:
        If ``True`` (default), fall back to a live GADM download when the
        data is not bundled or cached.

    Returns
    -------
    geopandas.GeoDataFrame in EPSG:4326.
    """
    lvl = resolve_level(level)
    country_key = normalize(country)
    country_key = _COUNTRY_ALIASES.get(country_key, country_key)

    gdf = _from_bundled(country_key, lvl)
    if gdf is None:
        gdf = _from_cache(country_key, lvl)
    if gdf is None:
        if not download:
            raise FileNotFoundError(
                f"No bundled/cached data for {country!r} level {lvl} and "
                "download=False."
            )
        # if the user used an alias (e.g. "USA"), download under the canonical
        # GADM name so pygadm can resolve it
        download_name = country
        if normalize(country) in _COUNTRY_ALIASES:
            download_name = country_key.title()
        gdf = _download(download_name, lvl, country_key)

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    if within and lvl >= 1:
        parent_col = f"NAME_{lvl - 1}"
        if parent_col in gdf.columns:
            matched, _ = match_one(within, gdf[parent_col].unique().tolist())
            if matched is not None:
                gdf = gdf[gdf[parent_col] == matched].copy()
            else:
                raise ValueError(
                    f"Could not match parent region {within!r} in column "
                    f"{parent_col}. Available: "
                    f"{sorted(gdf[parent_col].unique())[:10]} ..."
                )
    return gdf.reset_index(drop=True)
