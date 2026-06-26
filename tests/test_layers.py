"""Offline tests for the layer system (synthetic data, no network)."""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402

import geopandas as gpd  # noqa: E402
import acadgis as agis  # noqa: E402
from acadgis.layers import _pick_label_field, _select_labels  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def _points():
    return gpd.GeoDataFrame(
        {"name": ["A", "B", "C"], "pop": [30, 10, 20],
         "geometry": [Point(90.4, 23.8), Point(91.8, 22.4), Point(88.6, 24.4)]},
        crs="EPSG:4326")


# --- label policy ---------------------------------------------------------- #
def test_select_labels_policy():
    g = _points()
    assert len(_select_labels(g, None)) == 0          # hide
    assert len(_select_labels(g, False)) == 0
    assert len(_select_labels(g, True)) == 3          # all
    assert len(_select_labels(g, "all")) == 3
    assert len(_select_labels(g, "one")) == 1
    assert len(_select_labels(g, 2)) == 2
    # ranked by population -> the largest first
    top = _select_labels(g, 1, rank_field="pop")
    assert top.iloc[0]["name"] == "A"


def test_pick_label_field():
    assert _pick_label_field(_points(), None) == "name"
    assert _pick_label_field(_points(), "pop") == "pop"


# --- add_layer (points / lines / polygons + labels) ------------------------ #
def test_add_layer_points_label_control():
    g = _points()
    for labels, expected in [(None, 0), ("one", 1), ("all", 3)]:
        fig, ax = plt.subplots()
        ax.set_xlim(88, 92); ax.set_ylim(22, 25)
        agis.add_layer(ax, g, labels=labels)
        assert len(ax.texts) == expected
        assert len(ax.collections) >= 1                # the scatter


def test_add_layer_lines_and_polygons():
    line = gpd.GeoDataFrame(
        geometry=[LineString([(90, 23), (91, 24)])], crs="EPSG:4326")
    fig, ax = plt.subplots(); ax.set_xlim(89, 92); ax.set_ylim(22, 25)
    agis.add_layer(ax, line, color="#3a7bd5")
    poly = agis.load_boundaries("Bangladesh", "division", download=False)
    agis.add_layer(ax, poly, facecolor="none", edgecolor="#333", clip=False)
    assert len(ax.collections) >= 1


# --- add_raster (needs rioxarray) ------------------------------------------ #
def _write_tif(path, *, dtype="float32", nodata=-9999.0):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_bounds
    H = W = 40
    data = (np.linspace(0, 1, H * W).reshape(H, W)).astype(dtype)
    tr = from_bounds(88, 20.5, 92.7, 26.7, W, H)
    with rasterio.open(path, "w", driver="GTiff", height=H, width=W, count=1,
                       dtype=dtype, crs="EPSG:4326", transform=tr, nodata=nodata) as d:
        d.write(data, 1)
    return str(path)


def test_add_raster_continuous(tmp_path):
    pytest.importorskip("rioxarray")
    p = _write_tif(tmp_path / "r.tif")
    fig, ax = plt.subplots()
    agis.add_raster(ax, p, cmap="YlGn", colorbar=True)
    assert len(ax.images) == 1


def test_add_raster_categorical(tmp_path):
    pytest.importorskip("rioxarray")
    p = _write_tif(tmp_path / "lc.tif", dtype="uint8", nodata=0)
    fig, ax = plt.subplots()
    agis.add_raster(ax, p, categorical=True,
                    classes={1: ("#4a90d9", "Water"), 2: ("#2a9d4a", "Forest")},
                    legend=True)
    assert len(ax.images) == 1
    assert ax.get_legend() is not None


def test_add_raster_categorical_requires_classes(tmp_path):
    pytest.importorskip("rioxarray")
    p = _write_tif(tmp_path / "x.tif")
    fig, ax = plt.subplots()
    with pytest.raises(ValueError):
        agis.add_raster(ax, p, categorical=True)


def test_basemap_bad_style():
    pytest.importorskip("contextily")
    fig, ax = plt.subplots(); ax.set_xlim(90, 91); ax.set_ylim(23, 24)
    with pytest.raises(ValueError):
        agis.add_basemap(ax, style="not-a-style")
