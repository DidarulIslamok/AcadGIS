# AcadGIS — brand kit

The AcadGIS mark is a **study-area map**: a subdivided region (choropleth
districts) inside a crop frame, on a graticule. It says *“define and map a study
area”* — research, not navigation. Primary style is **Midnight** (dark); a
**Light** variant is provided for documents and print.

## Files

### Master vectors (`brand/`)
| File | Use |
|------|-----|
| `logo.svg` | **primary** mark — Midnight, **white** capture frame (colorblind-safe) |
| `logo-green.svg` | secondary mark — Midnight, green capture frame |
| `logo-light.svg` | mark for light backgrounds / print (ink frame) |
| `favicon-mark.svg` | simplified mark for tiny sizes (no grid/brackets) |
| `logo-wordmark.svg` | horizontal lockup, dark text (light bg) |
| `logo-wordmark-dark.svg` | horizontal lockup, light text (dark bg) |
| `header.svg` | animated README / website hero banner |
| `social-preview.svg` | 1280×640 GitHub / Twitter / OG card |

### Raster exports (`brand/png/`)
`icon-{16,32,48,64,128,180,192,256,512}.png`, `logo-512.png`,
`logo-light-512.png`, `logo-wordmark*.png`, `header.png`,
`social-preview.png`, `favicon.ico`.
Sizes 16/32/48 use the simplified mark for legibility; larger sizes use the full logo.

### Web / PWA (`brand/web/`)
`favicon.ico`, `favicon.svg`, `favicon-16x16.png`, `favicon-32x32.png`,
`apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png`, `site.webmanifest`.

Drop-in HTML:
```html
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#0f2233">
<meta property="og:image" content="/social-preview.png">
```

## Palette

| Role | Hex |
|------|-----|
| Midnight (bg) | `#0f2233` |
| Ink (light-bg text) | `#16263a` |
| District green | `#3ad29f` (dark) · `#2d6a4f` (light) |
| District teal | `#2ec4d6` (dark) · `#1b9aaa` (light) |
| District blue | `#5a9bff` (dark) · `#3b82f6` (light) |
| District amber | `#ffb567` (dark) · `#f4a261` (light) |
| Graticule | `#2b6cb0` |
| Capture frame (primary) | `#ffffff` (white) |
| Capture frame (secondary) | `#22c55e` (green) |
| Warm accent (wordmark route) | `#e76f51` (coral) |
| Paper (light bg) | `#f4efe1` |

## Usage notes

- Keep clear space around the mark ≈ one crop-bracket length.
- Primary frame is **white** (works on any page — the mark sits on its own dark
  tile); `logo-green.svg` is the approved secondary.
- Use `logo-light.svg` on light/printed backgrounds; `logo.svg` everywhere else.
- Regenerate all rasters with `python scripts/build_brand.py`.
