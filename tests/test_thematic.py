"""Offline tests for the thematic map types (synthetic data, no network)."""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from shapely.geometry import box  # noqa: E402

import geopandas as gpd  # noqa: E402
import acadgis as agis  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def _squares():
    """A tiny 2x2 grid of unit squares with values."""
    geoms = [box(0, 0, 1, 1), box(1, 0, 2, 1), box(0, 1, 1, 2), box(1, 1, 2, 2)]
    return gpd.GeoDataFrame(
        {"name": list("ABCD"), "v": [1.0, 2.0, 3.0, 4.0],
         "v2": [4.0, 1.0, 3.0, 2.0], "pop": [100.0, 200.0, 300.0, 400.0]},
        geometry=geoms, crs="EPSG:4326")


# --- interpolate_field ------------------------------------------------------ #
def test_interpolate_field_shape_and_extent():
    Z, ext = agis.interpolate_field([0, 1, 2], [0, 1, 2], [1, 2, 3],
                                    bbox=(0, 0, 2, 2), res=50)
    assert Z.shape == (50, 50)
    assert ext == (0.0, 2.0, 0.0, 2.0)
    assert not np.isnan(Z).any()
    # smooth field spans the sample values
    assert 0.9 < np.nanmin(Z) and np.nanmax(Z) < 3.1


def test_interpolate_field_clip_masks_outside():
    clip = _squares().iloc[[0]]                      # unit square at (0,0)-(1,1)
    Z, _ = agis.interpolate_field([0.5], [0.5], [1.0],
                                  bbox=(0, 0, 2, 2), res=40, clip=clip)
    assert np.isnan(Z).any() and not np.isnan(Z).all()


# --- isopleth / contours ---------------------------------------------------- #
def test_isopleth_and_contours_from_field():
    Z, ext = agis.interpolate_field([0, 2], [0, 2], [0.0, 10.0],
                                    bbox=(0, 0, 2, 2), res=40)
    fig, ax = plt.subplots()
    cf = agis.add_isopleth(ax, (Z, ext), colorbar=True)
    assert cf is not None
    fig2, ax2 = plt.subplots()
    cs = agis.add_contours(ax2, Z, extent=ext, levels=5, labels=False)
    assert cs is not None


def test_contours_bare_array_needs_extent():
    Z = np.ones((10, 10))
    fig, ax = plt.subplots()
    with pytest.raises(ValueError):
        agis.add_contours(ax, Z)


# --- heatmap ---------------------------------------------------------------- #
def test_heatmap_hexbin():
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots()
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    agis.add_heatmap(ax, rng.uniform(0, 10, 500), rng.uniform(0, 10, 500),
                     kind="hexbin")
    assert len(ax.collections) >= 1


def test_heatmap_kde():
    pytest.importorskip("scipy")
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots()
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    agis.add_heatmap(ax, rng.uniform(0, 10, 300), rng.uniform(0, 10, 300),
                     kind="kde", res=50)
    assert len(ax.images) == 1


# --- dot-density ------------------------------------------------------------ #
def test_dot_density_counts():
    g = _squares()
    fig, ax = plt.subplots()
    agis.dot_density(ax, g, "pop", per=10, seed=1)     # 10+20+30+40 = 100 dots
    pts = ax.collections[-1].get_offsets()
    assert len(pts) == 100
    # all dots inside the union of the squares
    union = g.union_all()
    inside = gpd.GeoSeries(gpd.points_from_xy(pts[:, 0], pts[:, 1]), crs=4326).within(
        union.buffer(1e-9))
    assert inside.all()


def test_dot_density_guard():
    g = _squares()
    fig, ax = plt.subplots()
    with pytest.raises(ValueError):
        agis.dot_density(ax, g, "pop", per=0.0001)


# --- bivariate --------------------------------------------------------------- #
def test_bivariate_colors_and_legend():
    g = _squares()
    ax = agis.bivariate(g, "v", "v2", xlabel="X", ylabel="Y")
    assert ax is not None
    assert len(ax.child_axes) == 1                     # the 2-D legend inset
    ax2 = agis.bivariate(g, "v", "v2", legend=False)
    assert len(ax2.child_axes) == 0


# --- cartogram ---------------------------------------------------------------- #
def test_cartogram_dorling_circles():
    from matplotlib.patches import Circle
    g = _squares()
    ax = agis.cartogram(g, "pop", kind="dorling", iterations=20)
    circles = [p for p in ax.patches if isinstance(p, Circle)]
    assert len(circles) == 4
    radii = sorted(c.get_radius() for c in circles)
    assert radii[-1] > radii[0]                        # biggest value -> biggest circle


def test_cartogram_noncontig_scales_within_bounds():
    g = _squares()
    ax = agis.cartogram(g, "pop", kind="noncontig", clip_scale=(0.4, 1.7))
    assert ax is not None


def test_cartogram_bad_kind():
    with pytest.raises(ValueError):
        agis.cartogram(_squares(), "pop", kind="contig")
