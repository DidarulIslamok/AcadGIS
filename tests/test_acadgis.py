"""Offline tests for acadgis (use bundled sample data only, no network)."""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

import acadgis as agis  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


# --- data loading ---------------------------------------------------------- #
def test_bundled_available():
    avail = agis.list_available()
    assert ("bangladesh", 2) in avail
    assert ("iraq", 1) in avail


def test_load_country():
    gdf = agis.load_boundaries("Bangladesh", "country", download=False)
    assert len(gdf) == 1
    assert str(gdf.crs).upper().endswith("4326")


def test_load_districts():
    gdf = agis.load_boundaries("Bangladesh", "district", download=False)
    assert len(gdf) == 64
    assert agis.name_column(gdf) == "NAME_2"


def test_level_aliases():
    assert agis.resolve_level("division") == 1
    assert agis.resolve_level("upazila") == 3
    assert agis.resolve_level(2) == 2
    with pytest.raises(ValueError):
        agis.resolve_level("galaxy")


def test_within_subset():
    gdf = agis.load_boundaries("Bangladesh", "district", within="Dhaka",
                               download=False)
    assert 0 < len(gdf) < 64
    assert set(gdf["NAME_1"].unique()) == {"Dhaka"}


# --- name matching --------------------------------------------------------- #
def test_normalize():
    assert agis.normalize("Dhaka District") == "dhaka"
    assert agis.normalize("Chittagong") == "chattogram"  # alias
    assert agis.normalize("Cumilla") == "cumilla"


def test_match_one():
    cands = ["Chattogram", "Dhaka", "Cumilla"]
    m, score = agis.match_one("Chittagong", cands)
    assert m == "Chattogram"
    assert score >= 80


# --- palettes & themes ----------------------------------------------------- #
def test_palette_colors():
    cols = agis.get_colors("spectral", 5)
    assert len(cols) == 5
    assert all(c.startswith("#") for c in cols)


def test_palette_cycles():
    cols = agis.get_colors("classic", 50)
    assert len(cols) == 50  # cycles past palette length


def test_themes():
    assert "atlas" in agis.list_themes()
    t = agis.get_theme("atlas")
    assert t.palette == "spectral"
    t2 = t.with_(palette="ocean")
    assert t2.palette == "ocean"
    assert t.palette == "spectral"  # original unchanged


# --- plotting -------------------------------------------------------------- #
def test_plot_returns_ax():
    gdf = agis.load_boundaries("Bangladesh", "district", download=False)
    ax = agis.plot(gdf, title="x", legend=True)
    assert ax is not None
    assert len(ax.figure.axes) >= 1


def test_choropleth_join_and_match():
    gdf = agis.load_boundaries("Bangladesh", "district", download=False)
    names = gdf["NAME_2"].tolist()
    data = {n: i for i, n in enumerate(names)}
    # inject a historical name to exercise fuzzy matching
    if "Chattogram" in data:
        data["Chittagong"] = data.pop("Chattogram")
    ax = agis.choropleth(gdf, data, palette="magma", scheme="quantiles")
    assert ax is not None


def test_studyarea_two_panel():
    sa = agis.StudyArea("Iraq", download=False).zoom_into("Babil")
    fig = sa.figure()
    assert fig is not None
    assert len(fig.axes) >= 2


def test_studyarea_bad_region():
    sa = agis.StudyArea("Iraq", download=False)
    with pytest.raises(ValueError):
        sa.zoom_into("Nowhereistan")


def test_load_world():
    w = agis.load_world()
    assert len(w) > 150
    assert "NAME_0" in w.columns
    assert "Bangladesh" in w["NAME_0"].values


def test_highlight_country():
    ax = agis.highlight_country("Bangladesh")
    assert ax is not None


def test_highlight_country_fuzzy():
    # fuzzy / partial name still resolves
    ax = agis.highlight_country("Banglades")
    assert ax is not None


def test_highlight_country_bad():
    with pytest.raises(ValueError):
        agis.highlight_country("Nowhereistan")


def test_world_locator():
    fig = agis.world_locator("Iraq")
    assert fig is not None
    assert len(fig.axes) >= 2


@pytest.mark.parametrize("style", ["classic", "minimal", "pointer", "rose"])
def test_north_arrow_styles(style):
    gdf = agis.load_boundaries("Iraq", "state", download=False)
    ax = agis.plot(gdf, north_arrow={"style": style, "size": 0.15,
                                     "loc": (0.9, 0.85), "color": "#1b4332"},
                   scale_bar=False, graticule=False)
    assert ax is not None


@pytest.mark.parametrize("style", ["simple", "bar", "stepped"])
def test_scale_bar_styles(style):
    gdf = agis.load_boundaries("Iraq", "state", download=False)
    ax = agis.plot(gdf, scale_bar={"style": style, "length_km": 200,
                                   "loc": (0.07, 0.06)},
                   north_arrow=False, graticule=False)
    assert ax is not None


@pytest.mark.parametrize("style", ["solid", "checker", "none"])
def test_border_styles(style):
    gdf = agis.load_boundaries("Iraq", "state", download=False)
    ax = agis.plot(gdf, border={"style": style, "checker_size": 0.05},
                   north_arrow=False, scale_bar=False, graticule=False)
    assert ax is not None


def test_decoration_arg_forms():
    """bool, string and dict forms all accepted."""
    gdf = agis.load_boundaries("Iraq", "state", download=False)
    assert agis.plot(gdf, north_arrow=True, scale_bar="stepped",
                     border="checker") is not None
    assert agis.plot(gdf, north_arrow=False, scale_bar=False,
                     border="none") is not None


def test_scale_bar_units_mi():
    gdf = agis.load_boundaries("Iraq", "state", download=False)
    ax = agis.plot(gdf, scale_bar={"units": "mi", "length_km": 100})
    assert ax is not None


def test_usa_states_and_alias():
    g = agis.load_boundaries("USA", "state", download=False)   # alias -> United States
    assert len(g) >= 50
    assert "California" in g["NAME_1"].values
    assert {"Alaska", "Hawaii"}.issubset(set(g["NAME_1"]))


def test_points_overlay():
    g = agis.load_boundaries("USA", "state", download=False)
    conus = g[~g["NAME_1"].isin(["Alaska", "Hawaii"])]
    ax = agis.plot(conus, palette="vibrant", labels=True, north_arrow=False,
                   scale_bar=False, graticule=False, border="none")
    pts = {"Denver": (-104.99, 39.74), "Austin": (-97.74, 30.27)}
    agis.points(ax, pts, color="black", size=12)
    assert ax is not None


def test_india_west_bengal_kolkata():
    wb = agis.load_boundaries("India", "district", within="West Bengal",
                              download=False)
    assert len(wb) > 10
    assert wb["NAME_2"].str.contains("Kolkata").any()


def test_points_graduated():
    import numpy as np
    wb = agis.load_boundaries("India", "district", within="West Bengal",
                              download=False)
    ax = agis.plot(wb, highlight="Kolkata", labels=False)
    df = agis.pd.DataFrame({"lon": np.linspace(87, 89, 10),
                            "lat": np.linspace(22, 25, 10),
                            "value": np.arange(10.0)})
    agis.points(ax, df, value="value", size_by="value", cmap="magma",
                legend=True)
    assert ax is not None


def test_studyarea_india_locator():
    sa = (agis.StudyArea("India", context_level="state", download=False)
          .zoom_into("West Bengal", detail_level="district"))
    fig = sa.figure()
    assert fig is not None and len(fig.axes) >= 2


def test_points_dataframe():
    g = agis.load_boundaries("Iraq", "state", download=False)
    df = agis.pd.DataFrame({"lon": [44.4, 43.7], "lat": [33.3, 36.3],
                            "name": ["Baghdad", "Mosul"]})
    ax = agis.plot(g)
    agis.points(ax, df, lon="lon", lat="lat", label="name")
    assert ax is not None


# --- hydrology (offline, bundled Natural Earth) ---------------------------- #
def test_load_rivers_lakes():
    r = agis.load_rivers()
    k = agis.load_lakes()
    assert len(r) > 100 and "scalerank" in r.columns
    assert len(k) > 100


def test_add_rivers_water():
    gdf = agis.load_boundaries("Bangladesh", "country", download=False)
    ax = agis.plot(gdf, palette="ocean")
    agis.add_water(ax, area=gdf)
    agis.add_rivers(ax, area=gdf, by_order=True)
    assert ax is not None


def test_atlas_offline():
    ax = agis.atlas("Bangladesh", level="division", download=False)
    assert ax is not None


# --- terrain & drainage on a synthetic DEM (no network needed) ------------- #
def _synthetic_dem():
    import numpy as np
    yy, xx = np.mgrid[0:80, 0:80]
    z = (1000 + 600 * np.exp(-((xx - 40) ** 2 + (yy - 30) ** 2) / 300.0)
         + 8 * (yy))  # a peak + a slope so water flows
    return agis.DEM(data=z.astype("float32"), bounds=(90.0, 23.0, 91.0, 24.0))


def test_relief_and_hillshade():
    dem = _synthetic_dem()
    hs = agis.hillshade(dem)
    assert hs.shape == dem.data.shape
    ax = agis.relief(dem, hillshade=True, legend=True, title="synthetic")
    assert ax is not None


def test_relief_ocean():
    import numpy as np
    dem = _synthetic_dem()
    dem.data[dem.data < 1100] = -5  # carve a "sea"
    ax = agis.relief(dem, hillshade=True, ocean_color="#cce5f0", sea_level=0)
    assert ax is not None


def test_osm_rivers_exported():
    # OSM fetch is network-bound; just confirm the API is wired up
    assert callable(agis.fetch_osm_rivers)
    assert "osm" in agis.atlas.__doc__.lower()


def test_drainage_synthetic():
    pysheds = pytest.importorskip("pysheds")  # noqa: F841
    dem = _synthetic_dem()
    streams = agis.drainage(dem, threshold=50)
    assert streams is not None  # may be empty for a smooth surface, that's ok
    ax = agis.relief(dem, hillshade=False)
    agis.add_streams(ax, streams)
    assert ax is not None


def test_layout_templates_exist():
    assert set(agis.TEMPLATES) == {"single", "two", "cascade", "series", "grid"}


def test_study_area_single():
    fig = agis.study_area("India", steps=[("district", "Chamoli")],
                          template="single", download=False)
    assert len(fig.axes) == 1


def test_study_area_two():
    fig = agis.study_area("India", steps=[("state", "Uttarakhand")],
                          template="two", download=False)
    assert len(fig.axes) >= 2


def test_study_area_series():
    fig = agis.study_area(
        "India", steps=[("state", "Uttarakhand"), ("district", "Chamoli")],
        template="series", download=False)
    assert len(fig.axes) >= 3


def test_study_area_wrong_panel_count():
    with pytest.raises(ValueError):
        agis.study_area("India", steps=[("state", "Uttarakhand")],
                        template="grid", download=False)


def test_save(tmp_path):
    gdf = agis.load_boundaries("Iraq", "state", download=False)
    ax = agis.plot(gdf)
    out = tmp_path / "m.png"
    agis.save(ax, str(out), dpi=60)
    assert out.exists() and out.stat().st_size > 0
