# Changelog

All notable changes to **AcadGIS** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-06-18

First public release.

### Added
- `load_boundaries(country, level, within=, download=)` — boundary loader with
  bundled-sample → local-cache → live-GADM-download resolution and friendly
  level names (`country`/`state`/`district`/`upazila`/…).
- `plot()` — one-line styled qualitative/categorical maps with north arrow,
  scale bar, lat/lon graticule, legend, labels and region highlighting.
- `choropleth()` — data-driven choropleths with automatic fuzzy **name
  matching** (handles renames, admin suffixes and diacritics) and optional
  `mapclassify` classification schemes.
- `StudyArea` — multi-panel **locator figures** (country → region → detail) with
  connecting arrows; the signature AcadGIS layout.
- `load_world()`, `highlight_country()` and `world_locator()` — world map with a
  selected study country marked, plus a world → zoomed-country two-panel figure
  (bundled Natural Earth 110m layer, fully offline).
- Batteries-included re-exports: `agis.plt` / `agis.np` / `agis.pd` /
  `agis.gpd` / `agis.show()` so one import is enough.
- **Customizable decorations** ported from the web app:
  - North arrows: `classic`, `minimal`, `pointer`, `rose` — now
    **aspect-corrected** so shapes never stretch on tall/wide maps.
  - Scale bars: `simple`, `bar`, `stepped`, with `units` km/mi.
  - Borders: `solid`, `checker` (zebra), `none`.
  - Each `north_arrow` / `scale_bar` / `border` argument accepts a bool, a
    style string, or a dict of `style`/`size`/`color`/`loc` for full control.
- 12 colour palettes and 6 themes (`academic`, `atlas`, `mono`, `nature`,
  `ocean`, `viridis`).
- `points()` — overlay point markers (capital cities, study sites, sampling
  locations) from a DataFrame, dict, or list, with optional labels; supports
  **graduated symbols** for collected data (`value=` colour-by-value with a
  colorbar, `size_by=` proportional marker size).
- Bundled offline sample data for Bangladesh (adm 0/1/2), Iraq (adm 0/1),
  USA states (adm 1, incl. Alaska & Hawaii), and India (adm 0/1/2); world
  countries + rivers/lakes (Natural Earth).
- Country-name aliases (e.g. ``"USA"`` → United States).
- `save()` helper for PNG / PDF / SVG export at any DPI.
- Branding: full brand kit in `brand/` — the "study-area map" mark (Midnight +
  Light), wordmark lockups, animated SVG header, 1280×640 social-preview card,
  favicons + app icons (16–512), `favicon.ico`, and a PWA `site.webmanifest`;
  plus a redesigned GitHub `README.md` and a PyPI-tuned `README_PyPI.md`.
  Regenerate rasters with `python scripts/build_brand.py`.
- Nine executed tutorial notebooks and a gallery script.
- Test suite (15 offline tests) and GitHub Actions CI.

- **Terrain** (`acadgis[terrain]`): `load_dem()` downloads & mosaics Copernicus
  GLO-30 (30 m global, no API key) for a name/bbox/GeoDataFrame; `relief()`
  renders hillshaded + hypsometric-tinted elevation maps; `hillshade()` helper.
- **Drainage** (`acadgis[drainage]`): `drainage()` extracts stream networks from
  a DEM via flow accumulation; `add_streams()` weights width by flow.
- **Hydrology**: `load_rivers()` / `load_lakes()` (bundled Natural Earth 50 m,
  optional 10 m download/cache), `add_rivers()` / `add_water()` overlays with
  river-name labels, and `atlas()` — WorldAtlas-style cartography with greyed &
  labelled neighbour countries, the river network with names, water bodies, and
  optional `cities` point markers.
- **Dense OpenStreetMap rivers**: `fetch_osm_rivers()` and `rivers="osm"`
  (in `atlas`/`add_rivers`) pull the full river/canal/stream network from
  Overpass (cached), styled with realistic blues and width-by-`kind`.
- **Topography to the ocean**: `relief(..., ocean_color=, sea_level=)` renders
  the sea in a realistic colour so terrain reads clearly down to the coast.

### Roadmap
- CSV point-layer overlay (study sites, sampling locations).
- Hatch / pattern fills for black-and-white printing.
- More bundled countries; projection options (Albers, Robinson).
- Inset locator auto-placement in a figure corner.
