"""Poster-style USA states map (states coloured + labelled, capitals, AK/HI insets)."""
import io
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import acadgis as agis

OUT = os.path.join(os.path.dirname(__file__), "outputs")

# --- state capitals (name, lat, lon) --------------------------------------- #
CAPITALS_CSV = """capital,state,lat,lon
Montgomery,Alabama,32.377,-86.300
Juneau,Alaska,58.302,-134.420
Phoenix,Arizona,33.448,-112.073
Little Rock,Arkansas,34.746,-92.289
Sacramento,California,38.576,-121.494
Denver,Colorado,39.739,-104.990
Hartford,Connecticut,41.764,-72.682
Dover,Delaware,39.158,-75.524
Tallahassee,Florida,30.438,-84.281
Atlanta,Georgia,33.749,-84.388
Honolulu,Hawaii,21.307,-157.858
Boise,Idaho,43.617,-116.200
Springfield,Illinois,39.798,-89.654
Indianapolis,Indiana,39.768,-86.158
Des Moines,Iowa,41.591,-93.604
Topeka,Kansas,39.048,-95.678
Frankfort,Kentucky,38.197,-84.863
Baton Rouge,Louisiana,30.457,-91.187
Augusta,Maine,44.307,-69.782
Annapolis,Maryland,38.979,-76.492
Boston,Massachusetts,42.358,-71.064
Lansing,Michigan,42.733,-84.556
Saint Paul,Minnesota,44.954,-93.090
Jackson,Mississippi,32.299,-90.185
Jefferson City,Missouri,38.579,-92.173
Helena,Montana,46.589,-112.039
Lincoln,Nebraska,40.808,-96.700
Carson City,Nevada,39.164,-119.766
Concord,New Hampshire,43.207,-71.538
Trenton,New Jersey,40.220,-74.770
Santa Fe,New Mexico,35.687,-105.938
Albany,New York,42.652,-73.757
Raleigh,North Carolina,35.780,-78.639
Bismarck,North Dakota,46.808,-100.784
Columbus,Ohio,39.961,-82.999
Oklahoma City,Oklahoma,35.467,-97.516
Salem,Oregon,44.939,-123.029
Harrisburg,Pennsylvania,40.264,-76.883
Providence,Rhode Island,41.831,-71.415
Columbia,South Carolina,34.000,-81.035
Pierre,South Dakota,44.367,-100.351
Nashville,Tennessee,36.166,-86.784
Austin,Texas,30.267,-97.743
Salt Lake City,Utah,40.761,-111.891
Montpelier,Vermont,44.260,-72.575
Richmond,Virginia,37.541,-77.436
Olympia,Washington,47.038,-122.901
Charleston,West Virginia,38.336,-81.612
Madison,Wisconsin,43.073,-89.401
Cheyenne,Wyoming,41.140,-104.820
"""

caps = agis.pd.read_csv(io.StringIO(CAPITALS_CSV))

states = agis.load_boundaries("USA", "state")
conus = states[~states["NAME_1"].isin(["Alaska", "Hawaii"])]
alaska = states[states["NAME_1"] == "Alaska"]
hawaii = states[states["NAME_1"] == "Hawaii"]
caps_conus = caps[~caps["state"].isin(["Alaska", "Hawaii"])]

OCEAN = "#dbeef5"
fig, ax = plt.subplots(figsize=(15, 9))
fig.patch.set_facecolor(OCEAN)
ax.set_facecolor(OCEAN)

# main CONUS map: states coloured + labelled
agis.plot(conus, ax=ax, palette="vibrant", labels=True,
          north_arrow=False, scale_bar=False, graticule=False, border="none")

# capital city dots + names
agis.points(ax, caps_conus, lon="lon", lat="lat", label="capital",
            color="#222222", size=14, fontsize=6, dy=0.25)

# decorative neighbour / ocean labels
ax.text(0.62, 0.95, "CANADA", transform=ax.transAxes, fontsize=15,
        color="#9bb7c4", fontweight="bold", ha="center")
ax.text(0.5, 0.04, "MEXICO", transform=ax.transAxes, fontsize=14,
        color="#9bb7c4", fontweight="bold", ha="center")
ax.text(0.04, 0.4, "Pacific\nOcean", transform=ax.transAxes, fontsize=13,
        color="#5fa6c0", fontweight="bold")
ax.text(0.95, 0.45, "Atlantic\nOcean", transform=ax.transAxes, fontsize=13,
        color="#5fa6c0", fontweight="bold", ha="right")
ax.set_title("United States of America", fontsize=22, fontweight="bold",
             pad=14)

# Alaska inset (bottom-left)
ax_ak = ax.inset_axes([0.0, 0.0, 0.26, 0.30])
agis.plot(alaska, ax=ax_ak, palette="earth", north_arrow=False,
          scale_bar=False, graticule=False, border="solid")
ax_ak.set_title("Alaska", fontsize=9)
ax_ak.set_xticks([]); ax_ak.set_yticks([])

# Hawaii inset
ax_hi = ax.inset_axes([0.27, 0.0, 0.14, 0.20])
agis.plot(hawaii, ax=ax_hi, palette="ocean", north_arrow=False,
          scale_bar=False, graticule=False, border="solid")
ax_hi.set_xlim(-160.5, -154.5); ax_hi.set_ylim(18.5, 22.5)
ax_hi.set_title("Hawaii", fontsize=9)
ax_hi.set_xticks([]); ax_hi.set_yticks([])

fig.savefig(os.path.join(OUT, "usa_states.png"), dpi=110,
            bbox_inches="tight", facecolor=fig.get_facecolor())
print("rendered usa_states.png")
