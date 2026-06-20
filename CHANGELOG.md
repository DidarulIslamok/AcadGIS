# Changelog

All notable changes to **AcadGIS** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

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
