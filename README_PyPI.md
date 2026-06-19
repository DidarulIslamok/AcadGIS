<p align="center">
  <img src="https://raw.githubusercontent.com/riponcm/AcadGIS/main/brand/logo.svg" alt="AcadGIS" width="120">
</p>

<h1 align="center">AcadGIS</h1>

<p align="center"><b>Publication-ready study area maps for research — in a few lines of Python.</b></p>

<p align="center">
  <a href="https://pypi.org/project/acadgis/"><img src="https://img.shields.io/badge/version-0.1.0-2b6cb0.svg" alt="Version"></a>
  <a href="https://pypi.org/project/acadgis/"><img src="https://img.shields.io/badge/python-3.9%2B-2d6a4f.svg" alt="Python"></a>
  <a href="https://www.apache.org/licenses/LICENSE-2.0"><img src="https://img.shields.io/badge/license-Apache--2.0-1b9aaa.svg" alt="License"></a>
  <a href="https://doc.acadgis.com"><img src="https://img.shields.io/badge/docs-acadgis.com-ffb567.svg" alt="Docs"></a>
</p>

<p align="center">
  <b><a href="https://acadgis.com">Website</a></b> &nbsp;&middot;&nbsp;
  <b><a href="https://doc.acadgis.com">Documentation</a></b> &nbsp;&middot;&nbsp;
  <b><a href="https://github.com/riponcm/AcadGIS">Source</a></b>
</p>

---

AcadGIS is a Python package (and a no-code web app) for making publication-ready study area
maps, choropleth maps, locator insets, terrain relief and river maps — for research papers,
theses and reports. Name a place, add your data, and export a journal-ready figure in three
lines: no QGIS, ArcGIS or shapefiles required.

```python
import acadgis as agis

sa = agis.StudyArea("Iraq").zoom_into("Babil")
sa.figure(suptitle="Study Area: Babil Governorate, Iraq")
sa.save("study_area.png", dpi=300)
```

<p align="center">
  <img src="https://raw.githubusercontent.com/riponcm/AcadGIS/main/examples/outputs/study_area_iraq.png" width="80%" alt="locator figure">
</p>

## Install

```bash
pip install acadgis                 # core (offline demo data + plotting)
pip install "acadgis[full]"         # + live download, fuzzy matching, terrain, drainage
```

Optional extras: `acadgis[download]` (any-country boundaries via `pygadm`), `acadgis[match]`
(fuzzy names), `acadgis[terrain]` (DEM relief), `acadgis[drainage]` (streams from a DEM).
Bangladesh, Iraq, India and the USA ship bundled — everything works offline.

## What it does

- Boundaries on demand — country, state, district and sub-district, by name, from GADM.
- One-line styled maps — 12 palettes, 6 themes, north arrows, scale bars, checker borders,
  graticules and legends.
- Choropleths and graduated symbols with automatic name matching (Chittagong matches
  Chattogram, dropped admin-suffixes, diacritics) and `mapclassify` schemes.
- Locator insets — the country to region to detail figure with connecting arrows.
- Layout presets — `study_area()` builds the whole multi-panel figure in one call
  (`single`, `two`, `cascade`, `series`, `grid`) with uniform or custom panel sizes,
  customizable connectors and region highlighting.
- Terrain — shaded relief and hypsometric tint from Copernicus GLO-30 (no API key), with
  realistic land-to-ocean colouring.
- Hydrology — Natural Earth or dense OpenStreetMap river networks and water bodies.
- Drainage — stream networks extracted from a DEM.
- Export — PNG, PDF or SVG at any DPI.

## Quick start

```python
import acadgis as agis

gdf = agis.load_boundaries("Bangladesh", level="district")     # auto-download + cache
agis.plot(gdf, palette="spectral", title="Bangladesh — Districts")

agis.choropleth(gdf, df, value="incidence", palette="magma")   # messy names welcome

ax = agis.plot(gdf, highlight="Comilla")
agis.points(ax, survey_df, value="value", size_by="value", cmap="magma", legend=True)

dem = agis.load_dem("Bagrote Valley")
agis.relief(dem, hillshade=True, ocean_color="#cce5f0")

agis.study_area("Bangladesh",                                  # whole layout, one call
    steps=[("division", "Dhaka"), ("district", "Madaripur")],
    template="cascade", terrain=True)
```

## Links and attribution

- Web app: https://acadgis.com
- Documentation: https://doc.acadgis.com
- Source: https://github.com/riponcm/AcadGIS
- Data: GADM (boundaries), Copernicus GLO-30 (terrain), Natural Earth and OpenStreetMap
  (hydrography). Free for academic and non-commercial use — please cite the sources.

## License

Apache License 2.0.
