<div align="center">

<img src="brand/header.svg" alt="AcadGIS — publication-ready academic GIS study-area maps" width="100%">

<br><br>

[![PyPI](https://img.shields.io/pypi/v/acadgis?color=2b6cb0)](https://pypi.org/project/acadgis/)
[![Downloads](https://static.pepy.tech/badge/acadgis)](https://pepy.tech/project/acadgis)
[![Downloads/month](https://img.shields.io/pypi/dm/acadgis?color=2d6a4f&label=downloads%2Fmonth)](https://pypi.org/project/acadgis/)
[![Python](https://img.shields.io/pypi/pyversions/acadgis?color=2d6a4f)](https://pypi.org/project/acadgis/)
[![License](https://img.shields.io/badge/license-Apache--2.0-1b9aaa.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-acadgis.com-ffb567.svg)](https://doc.acadgis.com)

### Publication-ready study area maps for research — in a few lines of Python

**[Website](https://acadgis.com)** &nbsp;&middot;&nbsp; **[Documentation](https://doc.acadgis.com)** &nbsp;&middot;&nbsp; **[PyPI](https://pypi.org/project/acadgis/)** &nbsp;&middot;&nbsp; **[Changelog](CHANGELOG.md)** &nbsp;&middot;&nbsp; **[Quick start](#quick-start)**

</div>

---

AcadGIS is a Python package (and a no-code web app) for making **publication-ready study area
maps, choropleth and the full thematic-map catalogue, locator insets, terrain relief, raster &
vector layers, satellite basemaps and river maps** — for research papers, theses and reports.
Name a place, add your data, and export a journal-ready figure: no QGIS, ArcGIS or shapefiles
required. Everything runs through a single `import acadgis as agis`.

```python
import acadgis as agis

sa = agis.StudyArea("Iraq").zoom_into("Babil")
sa.figure(suptitle="Study Area: Babil Governorate, Iraq")
sa.save("study_area.png", dpi=300)
```

Prefer no code? The companion web app at **[acadgis.com](https://acadgis.com)** offers the
same figures with interactive editing — in the browser.

---

## Gallery

<div align="center">
  <img src="assets/gallery/01_ndvi_dhaka.png" width="32%" alt="Sentinel-2 NDVI">
  <img src="assets/gallery/02_topography_dem.png" width="32%" alt="DEM topography">
  <img src="assets/gallery/03_basemap_styles.png" width="32%" alt="XYZ tile basemaps">
  <br>
  <img src="assets/gallery/04_landcover_switzerland.png" width="32%" alt="ESA WorldCover land cover">
  <img src="assets/gallery/05_landcover_dhaka.png" width="32%" alt="ESA WorldCover (Dhaka)">
  <img src="assets/gallery/06_roads_osm.png" width="32%" alt="OpenStreetMap roads">
  <br>
  <img src="assets/gallery/07_rivers_sites.png" width="32%" alt="rivers + field sites">
  <img src="assets/gallery/08_study_area_terrain.png" width="32%" alt="study area with terrain">
  <img src="assets/gallery/09_study_area_grid.png" width="32%" alt="grid drill-down">
  <br>
  <img src="assets/gallery/10_study_area_cascade.png" width="32%" alt="cascade drill-down">
  <img src="assets/gallery/11_study_area_series.png" width="32%" alt="series layout">
  <img src="assets/gallery/12_study_area_usa.png" width="32%" alt="USA locator">
  <br>
  <img src="assets/gallery/13_study_area_china.png" width="32%" alt="China cascade">
  <img src="assets/gallery/14_sea_india.png" width="32%" alt="sea / ocean layer">
  <img src="assets/gallery/15_india_context.png" width="32%" alt="India context map">
  <br>
  <img src="assets/gallery/16_uk_london.png" width="32%" alt="UK / London">
  <img src="assets/gallery/17_themes.png" width="32%" alt="palettes & themes">
  <img src="assets/gallery/18_usa_poster.png" width="32%" alt="USA states poster">
  <br>
  <img src="assets/gallery/19_choropleth.png" width="32%" alt="choropleth">
  <img src="assets/gallery/20_isopleth.png" width="32%" alt="interpolated isopleth">
  <img src="assets/gallery/21_isolines.png" width="32%" alt="labelled isolines">
  <br>
  <img src="assets/gallery/22_dot_density.png" width="32%" alt="dot-density">
  <img src="assets/gallery/23_world_vegetation.png" width="32%" alt="world vegetation">
  <img src="assets/gallery/24_world_choropleth.png" width="32%" alt="classed world choropleth">

<sub>Curated raster & satellite (NDVI · land cover · DEM · basemaps · roads) · study-area
layouts · sea/ocean · choropleth · isopleth / isolines · dot-density · world thematic maps —
every figure made with <code>import acadgis as agis</code>.</sub>
</div>

---

## Install

```bash
pip install acadgis                    # core (offline demo data + plotting)
pip install "acadgis[full]"            # + live download, fuzzy matching, terrain, drainage
```

| Extra | Adds | For |
|-------|------|-----|
| `acadgis[download]` | `pygadm` | live boundary download for any country |
| `acadgis[match]` | `rapidfuzz` | fuzzy name matching |
| `acadgis[terrain]` | `rasterio`, `rioxarray` | DEM shaded relief / elevation maps |
| `acadgis[drainage]` | `pysheds` | stream networks from a DEM |
| `acadgis[full]` | everything above + `mapclassify` | the lot |

Bangladesh, Iraq, India and the USA ship bundled, so you can try everything offline. One
import gives you the whole stack: `agis.plt`, `agis.np`, `agis.pd`, `agis.gpd`.

---

## Quick start

```python
import acadgis as agis

# 1. Boundaries by friendly level name (auto-download + cache)
gdf = agis.load_boundaries("Bangladesh", level="district")
dhaka = agis.load_boundaries("Bangladesh", "district", within="Dhaka")

# 2. A styled map in one call
agis.plot(gdf, palette="spectral", title="Bangladesh — Districts")

# 3. Choropleth from a spreadsheet — messy names welcome (Chittagong matches Chattogram)
agis.choropleth(gdf, df, value="incidence", palette="magma", scheme="natural_breaks")

# 4. Collected data as graduated symbols, study city highlighted
ax = agis.plot(gdf, highlight="Comilla")
agis.points(ax, survey_df, value="value", size_by="value", cmap="magma", legend=True)

# 5. Terrain relief down to a realistic sea
dem = agis.load_dem("Bagrote Valley")
agis.relief(dem, hillshade=True, ocean_color="#cce5f0")

# 6. The signature multi-panel locator
agis.StudyArea("India", context_level="state").zoom_into(
    "West Bengal", detail_level="district").figure()

# 7. ...or the whole layout in one call — pick a template, the rest is automatic
agis.study_area("Bangladesh",
    steps=[("division", "Dhaka"), ("district", "Madaripur")],
    template="cascade", terrain=True)        # single · two · cascade · series · grid
```

Every decoration is customizable — pass `True`/`False`, a style name, or a dict:

```python
agis.plot(gdf,
    north_arrow={"style": "rose", "size": 0.13, "loc": (0.9, 0.85)},
    scale_bar={"style": "stepped", "length_km": 100},
    border={"style": "checker"})
```

---

## What it does

- **Boundaries on demand** — country, state, district and sub-district, by name, from
  [GADM](https://gadm.org); cached after first use.
- **One-line styled maps** — 12 palettes, 6 themes, north arrows (4 styles), scale bars
  (3 styles), checker border, graticule and legend.
- **Choropleths and graduated symbols** with automatic name matching (renames,
  admin-suffixes, diacritics) and `mapclassify` schemes.
- **Locator insets** — the country to region to detail figure with connecting arrows.
- **Layout presets** — `study_area()` builds the whole multi-panel figure in one call:
  `single`, `two`, `cascade`, `series` or `grid`, with uniform or custom panel sizes,
  customizable connectors, per-panel decorations, and region highlighting.
- **Terrain** — shaded relief and hypsometric tint from Copernicus GLO-30 (no API key),
  with realistic land-to-ocean colouring.
- **Hydrology** — Natural Earth or dense OpenStreetMap river networks and water bodies.
- **Sea / ocean** — `sea=True` (or `agis.add_sea`) draws a clean ocean around any coastal
  country; `source="ne10m"` for crisp coastlines. Sliver-free; landlocked is a no-op.
- **Drainage** — stream networks extracted from a DEM by flow accumulation.
- **Layers** — drop anything on a map: `add_raster` (any GeoTIFF: continuous /
  categorical / RGB), `add_layer` (any vector, auto-styled, label control),
  `add_basemap`/`add_satellite` (6 tile styles), `add_topography`, `add_cities`,
  `add_roads`, plus curated real data: `add_landcover` (ESA WorldCover 10 m) and
  `add_ndvi` (Sentinel-2).
- **Thematic maps — the full catalogue** — choropleth, graduated symbols,
  heat maps (`add_heatmap`), interpolated isopleth surfaces and labelled isolines
  (`interpolate_field` → `add_isopleth`/`add_contours`), dot-density
  (`dot_density`), bivariate choropleths with a 2-D legend (`bivariate`) and
  Dorling / non-contiguous cartograms (`cartogram`).
- **Publication export** — PNG, PDF or SVG at any DPI.

---

## Documentation and tutorials

Full documentation and runnable, step-by-step tutorials live at
**[doc.acadgis.com](https://doc.acadgis.com)**:

- Quick start — load, plot, themes
- Choropleths and name matching
- Study-area locator figures
- World maps and country highlighting
- Customizing decorations (arrows, scale bars, borders)
- Terrain, hydrology and drainage
- Collected-data maps with graduated symbols

---

## Data and attribution

Administrative boundaries: [GADM](https://gadm.org) 4.1 (via
[`pygadm`](https://pypi.org/project/pygadm/)). Terrain: Copernicus GLO-30 (AWS Open Data).
Rivers, water and world layers: Natural Earth and OpenStreetMap (© OpenStreetMap
contributors, ODbL). All free for academic and non-commercial use — please cite the sources
in your work. See [`NOTICE`](NOTICE).

## Citation

```bibtex
@software{acadgis,
  title  = {AcadGIS: publication-ready academic GIS study-area maps},
  author = {Ripon Chandra Malo},
  year   = {2026},
  url    = {https://github.com/riponcm/AcadGIS},
  note   = {Web app: https://acadgis.com}
}
```

## License

[Apache License 2.0](LICENSE) — free to use, modify and distribute, including in academic
work. If AcadGIS helps your research, a citation or a star is appreciated.

## Acknowledgments

AcadGIS is developed with [**projectmem**](https://github.com/projectmem/projectmem) — a
persistent memory + workflow layer that keeps the codebase's decisions, issues and context
across sessions.

<div align="center"><sub>Built on geopandas, matplotlib and shapely — for researchers, by a researcher.</sub></div>
