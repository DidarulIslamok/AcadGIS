# Changelog

All notable changes to **AcadGIS** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-06-26

### Fixed
- **`grid` template connectors** followed `country→state`, `country→district`,
  `state→sub-district` (skipping levels) instead of the drill-down chain. They
  now link sequentially `0→1→2→3` (country → state → district → sub-district).

### Added
- **Thematic map types** — completes the standard thematic catalogue (choropleth
  and graduated symbols already shipped). All single-import, publication-ready:
  - `agis.interpolate_field(lon, lat, values, …)` — sparse samples → smooth grid
    (numpy Gaussian kernel, no SciPy), with `clip=` to mask the ocean/outside.
    The shared engine for the isopleth/isoline/heatmap family.
  - `agis.add_isopleth(ax, data, …)` — filled interpolated surface (filled
    contours). `data` may be the `(Z, extent)` from `interpolate_field`, a bare
    2-D array + `extent=`, a `DEM`, or a GeoTIFF path/DataArray.
  - `agis.add_contours(ax, data, …)` — isolines with inline labels (isotherms,
    isobars, elevation contours). Same input forms.
  - `agis.add_heatmap(ax, lon, lat, kind=…)` — point-density surface.
    `"kde"` (smooth, weighted, best for sparse features), `"hexbin"` (dense event
    data) or `"auto"`.
  - `agis.dot_density(ax, gdf, value, per=…)` — classic dot-density (1 dot =
    `per` units), rejection-sampled inside each region, deterministic `seed`,
    `max_dots` guard.
  - `agis.bivariate(gdf, x, y)` — two variables at once via a 3×3 blended
    palette (`BIVARIATE_PALETTE`, customizable) + an automatic 2-D legend.
  - `agis.cartogram(gdf, value, kind=…)` — `"dorling"` (circles ∝ value with
    overlap repulsion + labels) and `"noncontig"` (regions scaled in place;
    median-normalized + clipped so shapes never collapse), with ghost outlines
    and optional colorbar. True contiguous cartograms remain on the roadmap.
- **`study_area()` layer toggles** — `sea`, `rivers` and `labels` are now
  first-class arguments, each a scalar (all panels) or a per-panel list, so you
  can turn the ocean, river network and region-name labels on/off per map:
  `sea=[True, False, False]`, `rivers={'source': 'osm'}`, `labels=[False, True, False]`.
- **Connector customization on `study_area()`** — `links=` now also accepts a
  dict for full control of the panel-to-panel connectors:
  `single` (one line per hop), `shrink=(a, b)` (trim/stretch each end in
  points — negative extends), `arrow`/`arrow_size` (arrowhead at the
  destination end — `True` or an arrowstyle like `"->"`/`"wedge"`),
  `dots`/`dot_size`/`dot_color` (enlargeable
  endpoint markers), `alpha`, `pad` (locator-box padding), `anchors` (attach at
  any corner/edge name `tl·tr·bl·br·t·b·l·r·c` or an explicit `(lon, lat)`
  point → any `(x, y)` axes fraction on the target panel; per-hop via a dict),
  plus `color`/`width`/`style`/`box` overrides. `links=True/False` unchanged.

## [0.1.4] — 2026-06-25

### Added
- **Layer system** — drop any raster or vector onto a map. Every function is an
  `add_*(ax, …)` overlay, so it composes with `plot()` and every `study_area`
  panel. Rasters are reprojected to lon/lat automatically.
  - `agis.add_raster(ax, src, …)` — any GeoTIFF/NetCDF (or rioxarray DataArray)
    in three modes: **continuous** (`cmap` + `colorbar`), **categorical**
    (`classes={value: (color, label)}` + legend) and **rgb** (true-colour). An
    `area` argument clips to a geometry. (needs `acadgis[terrain]`)
  - `agis.add_layer(ax, src, …)` — any vector source (file path or
    GeoDataFrame/GeoSeries); auto-detects polygon/line/point and styles each.
    **Label control** via `labels=`: `None`/`False` (hide) · `"one"`/`1`
    (single) · an `int` (top-N) · `True`/`"all"` (every feature), with
    `label_field`, `rank_field` (rank which features get labelled, e.g. by
    population), halo, size & colour.
  - `agis.add_basemap(ax, style=…)` / `agis.add_satellite(ax)` — XYZ tile
    basemaps (`satellite`, `osm`, `light`, `dark`, `terrain`, `toner`),
    reprojected to work directly on lon/lat axes. (needs `acadgis[basemap]`)
  - `agis.add_topography(ax, area=…)` — hypsometric + hillshaded relief from a
    downloaded DEM, as a composable layer. (needs `acadgis[terrain]`)
  - `agis.add_cities(ax, area=…, top=N)` + `agis.load_places()` — Natural Earth
    populated places, ranked by population, with the same label control.
  - `agis.add_roads(ax, area=…)` + `agis.fetch_osm_roads()` — OpenStreetMap road
    network, widths scaled by `highway` class.
- **Curated raster data** — fetch a real global dataset for an area with one call
  (no GeoTIFF needed):
  - `agis.add_landcover(ax, area)` — ESA WorldCover 10 m land cover (public COGs,
    windowed remote read) with the official 11-class palette + legend.
  - `agis.add_ndvi(ax, area)` — Sentinel-2 NDVI: queries the Earth Search STAC
    API for the least-cloudy scene in a date window and computes
    `(NIR-Red)/(NIR+Red)`. (both need `acadgis[terrain]` + network)
- **`highlight_style` on `plot()`** — highlight a region as a solid `fill`
  (default) or as an `overlay` / `rect` / `circle` marker, with
  `highlight_color` / `highlight_edge` / `highlight_alpha` / `highlight_width`.
- **New extras:** `acadgis[basemap]` (contextily + xyzservices) and
  `acadgis[raster]` (rasterio + rioxarray); both folded into `full`/`dev`.
- **Z-order convention** documented: sea 0 · basemap/raster 1 · land 5 ·
  rivers/roads 6 · points/labels 8.

## [0.1.3] — 2026-06-21

### Added
- **Sea / ocean layer** — show the ocean around a country with one argument.
  - `agis.add_sea(ax, country=…, source=…, …)` — wraps geopandas/shapely
    internally, so only `import acadgis` is needed.
  - `sea=` on `plot()` and `study_area()` — `bool | colour | dict | per-panel list`.
  - **Sources:** `"auto"` (Natural Earth 110 m, bundled/offline),
    `"ne10m"` (Natural Earth 10 m land — crisp coastline, downloaded + cached),
    `"ocean"` (Natural Earth 10 m ocean polygon).
  - Options: `color`, `extent`/`pad` (auto-reveals the ocean), `background`,
    `neighbours`, `coastline`, `labels`, `set_view`.
  - The country's own detailed coast bounds the sea, so there are **no coastline
    slivers**. Landlocked areas produce an empty sea (no-op). Antimeridian and
    projected-CRS cases are handled; the land geometry is cached for speed.

## [0.1.2] — 2026-06-20

Full customization of the study-area figure — every decoration is now a `bool`,
a style string, a dict of options, or a per-panel list, all reachable through a
single `import acadgis as agis`.

### Added
- **Grid & ticks** — `graticule` accepts a dict (or per-panel list) for
  independent control: grid on/off + `grid_color`/`grid_lw`/`grid_alpha`/
  `grid_style`, square cells (`square`), per-axis `interval`, tick direction
  (`tick_dir` in/out/inout), `minor` ticks, 4-side labels (`sides`/`tick_sides`),
  and label `fontsize`/`bold`/`italic`/`font`/`rotate_x`/`rotate_y`.
  `grid=False` keeps ticks but drops the lines.
- **North arrow** — `coords="data"` to place by `(lon, lat)`, plus `edge`,
  `label_color`, `label_size` and `rotation`.
- **Scale bar** — two new QGIS-style styles `double` and `ticks` (now
  `bar`/`simple`/`stepped`/`double`/`ticks`), plus `coords="data"`, `edge`,
  `text_color` and `divisions`.
- **Per-map zoom** — `study_area(zoom=[…])` and `agis.zoom_axes(ax, factor)`
  (>1 in, <1 out).
- **`agis.callout()`** — framed sub-region insets placed anywhere (the
  Alaska/Hawaii pattern), with `color`/`palette`/`terrain` fill.
- **Layout** — `panel_scale={index_or_role: factor}` resizes specific panels;
  `gap` sets easy spacing between maps.
- **`agis.connect()`** — wrapped panel-to-panel connectors (coordinate systems
  by name: `data`/`axes`/`figure`, optional arrowhead) — no matplotlib import.
- **Titles** — `title_inside` / `title_loc` / `title_box` to place a map's title
  inside the panel.
- **Colorbar** — `study_area(colorbar={'loc': 'right'|'bottom'|'inside', …})` and
  `relief(legend_loc=, legend_length=, legend_size=, legend_pad=)`.
- New top-level exports: `zoom_axes`, `callout`, `connect`.

### Changed
- `study_area(box=…)` now defaults to **`False`** — the highlight is no longer
  doubled by a connector box (set `box=True` to bring it back).
- The graticule now draws **square cells** by default (equal interval on both
  axes); set `square=False` or per-axis intervals for the old behaviour.
- The non-terrain focus panel honours `uniform_panels`, and the terrain colorbar
  no longer shrinks its panel (drawn in a dedicated inset) — panels are more
  uniform by default.

## [0.1.1] — 2026-06-19

### Added
- `study_area(country, steps=, template=)` — build the entire multi-panel
  locator figure in a single call. Five templates: `single`, `two`,
  `cascade` (two context panels + a focused detail panel), `series` (three
  uniform panels) and `grid` (2×2). Each preset is fully customizable —
  `width_ratios`/`height_ratios`/`wspace`/`hspace`/`figsize` for panel sizing,
  `uniform_panels` for equal panel boxes, `highlight_style`
  (`overlay`/`rect`/`circle`) + colour/alpha/width for region highlighting,
  per-panel `graticule`/`north_arrow`/`scale_bar`, and `links`/`link_color`/
  `link_width`/`link_style`/`box` for the connectors. Returns the Figure with
  `fig.panels` exposed for hand-drawn overlays.
- `TEMPLATES` — the preset registry (`single`/`two`/`cascade`/`series`/`grid`).
- `terrain=True` renders the focus panel as Copernicus GLO-30 shaded relief.

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
