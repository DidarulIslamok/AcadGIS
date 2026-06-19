"""Render the gallery images shown in the README. Run: python examples/gallery.py"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import acadgis as agis

OUT = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)


def save(ax_or_fig, name, dpi=150):
    agis.save(ax_or_fig, os.path.join(OUT, name), dpi=dpi)
    plt.close("all")
    print("rendered", name)


# 1. Signature locator: Iraq -> Babil
sa = agis.StudyArea("Iraq", theme="atlas").zoom_into("Babil")
sa.figure(suptitle="Study Area: Babil Governorate, Iraq")
save(sa, "study_area_iraq.png")

# 2. Three-panel locator: Bangladesh -> Dhaka -> districts
sa = (agis.StudyArea("Bangladesh", context_level="division")
        .zoom_into("Dhaka", detail_level="district"))
sa.figure(suptitle="Study Area: Dhaka Division, Bangladesh")
save(sa, "study_area_dhaka.png")

# 3. Choropleth from data (with messy names)
gdf = agis.load_boundaries("Bangladesh", "district")
np.random.seed(7)
names = gdf["NAME_2"].tolist()
vals = dict(zip(names, np.random.randint(20, 100, len(names))))
if "Chattogram" in vals:
    vals["Chittagong"] = vals.pop("Chattogram")
df = pd.DataFrame({"district": list(vals), "incidence": list(vals.values())})
ax = agis.choropleth(gdf, df, value="incidence", palette="magma",
                     scheme="natural_breaks", k=5,
                     legend_label="Incidence",
                     title="Disease incidence by district")
save(ax, "choropleth_bd.png")

# 4. Simple qualitative map
ax = agis.plot(gdf, palette="spectral", title="Bangladesh — Districts")
save(ax, "districts_spectral.png")

# 5. World map with study country highlighted
ax = agis.highlight_country("Bangladesh", color="#e6194b",
                            title="Study Country: Bangladesh")
save(ax, "world_bangladesh.png")

# 6. World locator (world -> zoomed country)
fig = agis.world_locator("Bangladesh", color="#e6194b",
                         suptitle="Bangladesh — Location & Extent")
save(fig, "world_bangladesh_locator.png")

# 7. North arrow styles (aspect-corrected)
gdf = agis.load_boundaries("Bangladesh", "district")
fig, axes = plt.subplots(1, 4, figsize=(18, 7))
for ax, st in zip(axes, ["classic", "minimal", "pointer", "rose"]):
    agis.plot(gdf, ax=ax, palette="spectral", graticule=False, scale_bar=False,
              north_arrow={"style": st, "size": 0.16, "loc": (0.82, 0.85)},
              title=f"arrow: {st}")
fig.suptitle("North arrow styles", fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "arrow_styles.png")

# 8. Scale bar styles + checker border
fig, axes = plt.subplots(1, 3, figsize=(15, 7))
for ax, st in zip(axes, ["simple", "bar", "stepped"]):
    agis.plot(gdf, ax=ax, palette="ocean", graticule=False, north_arrow=False,
              border={"style": "checker", "checker_size": 0.05},
              scale_bar={"style": st, "loc": (0.1, 0.08), "size": 1.3},
              title=f"scale: {st} + checker border")
fig.tight_layout()
save(fig, "scalebar_styles.png")

# 9. Fully customized figure
ax = agis.plot(
    gdf, palette="spectral", figsize=(8, 9),
    title="Bangladesh — Districts (custom decorations)",
    north_arrow={"style": "rose", "size": 0.13, "loc": (0.88, 0.86),
                 "color": "#1b4332"},
    scale_bar={"style": "stepped", "loc": (0.06, 0.05), "size": 1.2,
               "length_km": 100, "color": "#222"},
    border={"style": "checker", "checker_size": 0.045, "color": "#2a2a2a"})
save(ax, "custom_decorations.png")

# 10. Themes grid
gov = agis.load_boundaries("Iraq", "governorate")
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for ax, theme in zip(axes.ravel(), agis.list_themes()):
    agis.plot(gov, theme=theme, ax=ax, north_arrow=False, scale_bar=False,
              graticule=False, title=theme)
fig.suptitle("acadgis themes", fontsize=16, fontweight="bold")
fig.tight_layout()
save(fig, "themes_grid.png")

# 10b. India → West Bengal → Kolkata survey (graduated symbols) — offline
wb = agis.load_boundaries("India", "district", within="West Bengal",
                          download=False)
ax = agis.plot(wb, palette="earth", labels=True, highlight="Kolkata",
               title="Collected Survey Data — West Bengal (Kolkata highlighted)",
               figsize=(9, 10))
np.random.seed(1)
_n = 60
_lon = np.random.normal(88.0, 0.7, _n)
_lat = np.random.normal(23.5, 1.1, _n)
_val = np.clip(np.random.normal(50, 20, _n) + (24 - _lat) * 8, 5, 100)
_survey = pd.DataFrame({"lon": _lon, "lat": _lat, "value": _val})
agis.points(ax, _survey, value="value", cmap="magma", size_by="value",
            edgecolor="black", legend=True, legend_label="Measured value")
save(ax, "india_wb_kolkata_survey.png")

# 11. USA states poster (states + capitals + AK/HI insets)
import runpy

runpy.run_path(os.path.join(os.path.dirname(__file__), "usa_demo.py"))

# 12. Atlas style (neighbours + rivers + cities) — WorldAtlas look
_bd_cities = {"Dhaka": (90.41, 23.81), "Chittagong": (91.83, 22.36),
              "Khulna": (89.56, 22.85), "Rajshahi": (88.60, 24.37),
              "Sylhet": (91.87, 24.90), "Rangpur": (89.25, 25.74),
              "Barisal": (90.37, 22.70), "Mymensingh": (90.40, 24.75),
              "Dinajpur": (88.64, 25.63), "Comilla": (91.18, 23.46),
              "Jessore": (89.21, 23.17), "Cox's Bazar": (91.98, 21.43)}
ax = agis.atlas("Bangladesh", level="country", rivers_scale="10m",
                cities=_bd_cities, labels=False, title="Bangladesh",
                figsize=(9, 10))
save(ax, "atlas_bangladesh.png")

# 13-14. Terrain relief + drainage (needs network + [terrain,drainage])
try:
    dem = agis.load_dem((74.35, 35.72, 74.92, 36.30), max_size=900)
    ax = agis.relief(dem, cmap="terrain", hillshade=True,
                     title="Haramosh / Bagrote Valley — Elevation",
                     legend_label="Elevation (m)")
    save(ax, "terrain_relief.png")

    ax = agis.relief(dem, cmap="gist_earth", hillshade=True,
                     title="Elevation & Drainage", legend_label="m")
    streams = agis.drainage(dem, threshold=400)
    agis.add_streams(ax, streams, by_order=True, color="#1f5fbf")
    save(ax, "terrain_drainage.png")

    # coastal "topography to the ocean" (Bay of Naples)
    cdem = agis.load_dem((14.05, 40.45, 14.75, 40.95), max_size=1100)
    ax = agis.relief(cdem, cmap="terrain", hillshade=True,
                     ocean_color="#cce5f0", sea_level=1,
                     title="Bay of Naples — Topography to the Sea",
                     legend_label="Elevation (m)")
    save(ax, "coast_naples.png")
except Exception as exc:  # network/DEM unavailable
    print("terrain gallery skipped:", exc)

# 15. Dense OSM rivers atlas (needs network)
try:
    ax = agis.atlas("Bangladesh", level="country", rivers="osm",
                    osm_kinds=("river", "canal"), cities=_bd_cities,
                    labels=False, river_labels=False,
                    title="Bangladesh — Hydrography (OSM)", figsize=(9, 10))
    save(ax, "atlas_osm_rivers.png")
except Exception as exc:
    print("osm rivers gallery skipped:", exc)

print("GALLERY DONE")
