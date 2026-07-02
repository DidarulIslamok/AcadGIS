# AcadGIS roadmap

Living plan for upcoming work. Shipped items move to [CHANGELOG.md](CHANGELOG.md).

## Interactive studio (`agis.edit`)

An interactive editing layer over any `study_area` / `plot` figure: move, resize,
toggle and restyle every element with the mouse + a small control panel, then
**export a PNG/PDF and the Python code that reproduces it** (reproducibility is
never lost).

- **Surface:** notebook-first via `ipympl` (`%matplotlib widget`) + `ipywidgets`,
  shipped as an optional extra `pip install "acadgis[interactive]"`. The polished
  pointer-native version lives in the web app (acadgis.com).
- **Module:** `acadgis/studio.py` — `Studio` (event wiring) + `edit(fig)` helper.

### Features

| Element | Interaction |
|---|---|
| Text / titles / region labels | drag to move; edit text (widget / double-click) |
| North arrow | drag to move; resize; restyle |
| Scale bar | drag to move; change length / style |
| Highlight (overlay / rect / circle) | drag + resize handles; restyle; recolour |
| Connectors | drag endpoints; add / remove; shape via multiple lines |
| Markers / sampling points | drag to reposition |
| Map / panel box size | drag panel edges (free-form `set_position`) or sliders |
| Grid / ticks | toggle on/off per panel |
| Template / palette / terrain / colours | widgets → re-render (cached data) |
| Export | PNG / PDF + paste-ready code ("Emit code") |

Two edit classes: **live artist manipulation** (positions, visibility — instant)
and **structural re-render** (template, sizes, palette — re-call `study_area`,
cheap because boundaries/terrain are cached). A single **state dict** drives both
re-rendering and code export.

### Phases

1. **MVP — draggable elements + code export.** Drag text/labels, highlight box,
   markers and connector endpoints; "Emit code" + PNG/PDF.  ← *in progress*
2. **Control panel.** Grid on/off, highlight style, colours, template, text edit.
3. **Drag-resize panels.** Free-form panel boxes via `set_position` (hardest).
4. **Web-app editor.** Pointer-native UI; reuse the Python engine as the backend.

### Known hard parts

- Panel resize: gridspec isn't draggable → switch panels to free-form
  `set_position` so edges can be dragged (connectors anchored via `transAxes`
  follow automatically).
- `ipympl` can lag with many live artists; a Qt window (script mode) is smoother —
  support both.
- matplotlib has no text input → label editing uses `ipywidgets` or a
  double-click prompt.

## Thematic map types — full coverage (Geoapify parity)

Target: cover every standard thematic map type, benchmarked against
[Geoapify's thematic map catalogue](https://www.geoapify.com/thematic-maps-types-examples/).
All as the usual one-call / `add_*(ax)` API, eye-catching defaults, single import.

| # | Type | What it shows | AcadGIS status | API |
|---|---|---|---|---|
| 1 | **Choropleth** | regions shaded by value | ✅ shipped | `choropleth()`; classed via `scheme=`/`bins` |
| 2 | **Graduated / proportional symbol** | symbol size ∝ value | ✅ shipped | `points(value=, size_by=, size_range=)` |
| 3 | **Heat map** (density) | density surface from points | ✅ shipped 0.2.0 | `add_heatmap(ax, lon, lat, kind="kde"\|"hexbin"\|"auto")` |
| 4 | **Isopleth** (filled interpolated field) | continuous field, clipped | ✅ shipped 0.2.0 | `interpolate_field(...)` → `add_isopleth(ax, …)` |
| 5 | **Isoline** (contours) | equal-value lines/labels | ✅ shipped 0.2.0 | `add_contours(ax, field\|DEM\|raster, levels=, labels=)` |
| 6 | **Dot-density** | N dots ∝ count per region | ✅ shipped 0.2.0 | `dot_density(ax, gdf, value, per=N)` |
| 7 | **Bivariate** | two variables, blended palette | ✅ shipped 0.2.0 | `bivariate(gdf, x, y)` + 3×3 2-D legend |
| 8 | **Cartogram** | regions resized by value | 🟡 0.2.0: dorling + noncontig | `cartogram(gdf, value, kind="dorling"\|"noncontig")` |

### Remaining
- **Contiguous cartogram** (`kind="contig"`, Gastner–Newman diffusion) — needs a
  vendored algorithm or optional dep; ship when warranted.
- **Kriging** interpolation behind an extra (`scikit-gstat`/`pykrige`) as an
  alternative engine for `interpolate_field`.

## Other planned work

- CSV point-layer overlay convenience loader.
- Hatch / pattern fills for black-and-white printing.
- More bundled countries; projection options (Albers, Robinson).
- Inset locator auto-placement in a figure corner.
