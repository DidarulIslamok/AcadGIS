"""Offline tests for study_area connector customization (links=dict)."""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import ConnectionPatch  # noqa: E402

import acadgis as agis  # noqa: E402

STEPS = [("division", "Dhaka"), ("district", "Gazipur")]


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def _cps(fig):
    return [a for a in fig.artists if isinstance(a, ConnectionPatch)]


def test_links_true_unchanged():
    fig = agis.study_area("Bangladesh", STEPS, template="series", download=False)
    assert len(_cps(fig)) == 4                     # 2 hops x 2 corners


def test_links_single_shrink_dots():
    fig = agis.study_area(
        "Bangladesh", STEPS, template="series", download=False,
        links={"single": True, "shrink": (10, -18), "dots": True,
               "dot_size": 9, "color": "#ff0000", "width": 2.0})
    cps = _cps(fig)
    assert len(cps) == 2                           # one line per hop
    assert cps[0].shrinkA == 10 and cps[0].shrinkB == -18   # stretch = negative
    dots = [a for a in fig.artists if isinstance(a, Line2D)]
    assert len(dots) == 4                          # 2 lines x 2 endpoint dots
    assert dots[0].get_markersize() == 9


def test_links_anchors_named_and_point():
    fig = agis.study_area(
        "Bangladesh", STEPS, template="series", download=False,
        links={"anchors": [("r", (0.0, 0.5))]})    # right edge -> panel middle
    assert len(_cps(fig)) == 2
    # explicit (lon, lat) source anchor also accepted
    fig2 = agis.study_area(
        "Bangladesh", STEPS, template="series", download=False,
        links={"anchors": [((90.4, 23.8), (0.0, 0.5))]})
    assert len(_cps(fig2)) == 2


def test_links_dict_color_override():
    fig = agis.study_area(
        "Bangladesh", STEPS, template="series", download=False,
        links={"color": "#123456"})
    assert _cps(fig)[0].get_edgecolor()[:3] == pytest.approx(
        (0x12 / 255, 0x34 / 255, 0x56 / 255), abs=1e-3)


def test_links_show_false():
    fig = agis.study_area("Bangladesh", STEPS, template="series", download=False,
                          links={"show": False, "dots": True})
    assert len(_cps(fig)) == 0


# --- per-panel layer toggles (offline: bundled data + Natural Earth 50m/110m) --- #
def test_study_area_labels_per_panel():
    fig = agis.study_area("Bangladesh", STEPS, template="series",
                          labels=[False, True, False], download=False)
    assert len(fig.panels) == 3
    # the division panel gains region-name texts beyond its title
    assert len(fig.panels[1].texts) > len(fig.panels[0].texts)


def test_study_area_sea_offline():
    fig = agis.study_area("Bangladesh", STEPS, template="series",
                          sea=[True, False, False], download=False)
    assert len(fig.panels[0].patches) >= 1        # sea polygon on the country panel


def test_study_area_rivers_offline():
    fig = agis.study_area("Bangladesh", STEPS, template="series",
                          rivers=[{"scale": "50m"}, False, False], download=False)
    assert len(fig.panels) == 3                   # accepted; runs offline (bundled 50m)
