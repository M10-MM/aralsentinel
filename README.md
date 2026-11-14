# AralSentinel

**Salinity-risk proxy and climate-smart crop rotations for Uzbek farmers, built on NASA open data.**
NASA Space Apps Challenge 2026 — challenge **“Field Shift: Adapting Farms with NASA Data”**.

**Live demo:** {{NETLIFY_URL}}  ·  **Code:** {{GITHUB_URL}}
Docs: [pitch](docs/pitch.md) · [slides](docs/slides.md) · [video script](docs/video_script.md) · [submission texts](docs/submission.md)

## Problem

Soil salinisation is a major problem on Uzbekistan's irrigated land. It is a legacy of the Aral Sea crisis
and of decades of cotton–wheat cropping with heavy irrigation. Our data for the Jizzakh demo field shows
how dry it is: NASA POWER rainfall averages **365 mm/yr** (2015–2025), with only **~16 mm in June–August**,
and MODIS summer land-surface temperature is about **40 °C**. Farmers and extension agents have little
field-level evidence for which fields are at risk, or which rotation would save water and soil without
wrecking income.

## Solution

AralSentinel is a map-based web app in English, Uzbek and Russian. Click a field to get:

1. **10-year satellite and climate trends (2015–2025):** vegetation (NDVI), summer land-surface temperature, root-zone soil wetness, rainfall and summer peak air temperature.
2. **A salinity/drought risk proxy (0–100)** with its main driver and a list of any missing inputs.
3. **The top 5 three-year crop rotations** (Year 1 → Year 2 → Year 3). They come from FAO agronomic rules and are ranked by the farmer's own priorities (save water / protect soil / income).
4. **A water-cut simulator:** the yield and income loss of the best rotation if irrigation water is cut by 10/20/30/50 %, using the FAO-33 yield-response equation.

The app works offline. All data is pre-downloaded, and the frontend falls back to static JSON when no server is reachable.

## How it works

```
backend/fetch_data.py ──► data/cache/raw/*.json   (raw API responses, downloaded once)
                      └─► data/field_data.json   (clean yearly series per field)
data/crops.json  (FAO crop parameters)
        │
backend/app/main.py   FastAPI: /api/fields, /api/fields/{id}/report   (reads local files only)
backend/app/scoring.py  risk proxy, rotation rules + scoring, water-cut simulator
        │
frontend/  Leaflet map + Chart.js (vendored, works offline), i18n EN/UZ/RU
frontend/api/  static copy of the API (backend/export_static.py) for offline / static hosting
```

## Data sources (all free, no API key)

| Variable | Product | Mission / model | Access |
|---|---|---|---|
| Vegetation (NDVI), Jun–Aug mean | **MOD13Q1 v061**, 250 m, 16-day | NASA **Terra / MODIS** | [ORNL DAAC MODIS Web Service](https://modis.ornl.gov/data/modis_webservice.html) · [LP DAAC product page](https://lpdaac.usgs.gov/products/mod13q1v061/) |
| Land-surface temperature (day), Jun–Aug mean | **MOD11A2 v061**, 1 km, 8-day | NASA **Terra / MODIS** | ORNL DAAC · [LP DAAC product page](https://lpdaac.usgs.gov/products/mod11a2v061/) |
| Rainfall (PRECTOTCORR), root-zone soil wetness (GWETROOT), max air temp (T2M_MAX) | NASA **POWER** monthly, Agroclimatology | **MERRA-2** reanalysis (NASA GMAO) | [power.larc.nasa.gov](https://power.larc.nasa.gov/) |
| Soil pH, clay, sand, organic carbon (0–30 cm) | **SoilGrids v2.0** | ISRIC | [soilgrids.org](https://soilgrids.org/) |
| Crop water need, yield response Ky | FAO Irrigation & Drainage Paper **33** and **56** | FAO | [FAO-33](https://www.fao.org/4/i2800e/i2800e.pdf) · [FAO-56](https://www.fao.org/4/x0490e/x0490e00.htm) |
| Crop salt tolerance (ECe threshold, slope) | FAO Irrigation & Drainage Paper **29** Rev.1 (Ayers & Westcot 1985) | FAO | [FAO-29](https://www.fao.org/4/t0234e/t0234e00.htm) |

## Method

**Risk proxy (0–100).** Each input is scaled 0–1 and weighted. Missing inputs are dropped and the remaining weights are re-normalised:

| Component | Input | 0 → 1 scale | Weight |
|---|---|---|---|
| rain | mean rainfall, last 5 years | 400 → 100 mm/yr | 0.20 |
| soil_moisture | GWETROOT, last 5 years | 0.6 → 0.2 | 0.20 |
| heat | MODIS summer LST (fallback: POWER summer peak Tmax) | 35 → 50 °C (38 → 48 °C) | 0.20 |
| ndvi_trend | least-squares NDVI slope 2015–2025 | 0 → −0.01 / yr | 0.25 |
| soil_texture | SoilGrids clay % and pH | clay 20 → 50 %, pH 7.5 → 9 | 0.15 |

Levels: low < 35 ≤ medium < 60 ≤ high. `main_driver` is the largest weighted contribution.

**Rotations.** Every 3-year sequence of 6 crops (cotton, winter wheat, alfalfa, maize, sorghum, mung bean) is generated, then filtered by these rules:
- No crop repeats in consecutive years, including when the rotation cycles back to Year 1.
- At least one legume in the 3 years.
- Alfalfa only where water availability is high (root-zone wetness ≥ 0.5 and rain ≥ 300 mm). Otherwise an **“alfalfa trap”** warning is shown.
- On high-risk fields, at least 2 of the 3 years must be salt-tolerant crops (FAO-29 ECe threshold ≥ 6 dS/m).

Each rotation then gets four scores (0–100):
- **water_saving**, from FAO seasonal water need
- **salt_tolerance**, from the FAO-29 threshold
- **soil_health**, from legumes and a rule-of-thumb soil-benefit score
- **income**, from estimated yield × price

The final **fit** = (user-weighted water, soil and income + salt tolerance weighted by field risk) × a soil pH suitability factor. The top 5 distinct crop sets are returned.

**Water-cut simulator** (FAO-33): `1 − Ya/Ym = Ky × (1 − ETa/ETm)`, assuming a water cut of X % lowers ETa/ETm by X %.

## Limitations (please read)

- **The risk score is a proxy index.** Satellites do not measure soil salinity directly. No field EC measurements were used for calibration, and the thresholds and weights are team assumptions.
- **Yields and prices in `data/crops.json` are rough estimates** (marked `"estimate": true`) and are used for ranking only.
- **Pixel scale:** one MODIS pixel at the field centre (250 m NDVI, 1 km LST) and one ~50 km POWER grid cell. The MODIS QC layers were not applied.
- **Scope:** the fields in `data/fields.json` are demo locations, not surveyed farms. The water-cut model ignores rain, groundwater and deficit-irrigation timing.
- **Sample data:** if a field has no downloaded data, it gets clearly labelled SAMPLE values (yellow banner in the app, `"sample": true` in the JSON).
- **Advice:** the recommendations are options to explore, not agronomic advice. Check them with an agronomist.

## How to run (Windows)

```powershell
# one-time setup (from the project root)
py -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt

# 1) download data once (needs internet; ~30-60 min because ORNL is slow; safe to re-run, uses cache)
backend\.venv\Scripts\python backend\fetch_data.py
#    rebuild from cache only, no internet:   backend\.venv\Scripts\python backend\fetch_data.py --offline

# 2) export static copy for offline / static hosting
backend\.venv\Scripts\python backend\export_static.py

# 3) start the app -> http://localhost:8000   (or double-click backend\start.bat)
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000
```

macOS/Linux: use `python3 -m venv backend/.venv` and `backend/.venv/bin/python`.

## Deploy

### Public URL (primary): static site on Netlify

The public demo is the **static build**: the `frontend/` folder plus the pre-computed JSON in `frontend/api/`.
It needs no server, never sleeps, and works the same way offline.

1. Refresh the data and export it:
   ```powershell
   backend\.venv\Scripts\python backend\fetch_data.py --offline
   backend\.venv\Scripts\python backend\export_static.py
   ```
2. Go to [app.netlify.com/drop](https://app.netlify.com/drop) and drag the **`frontend/`** folder onto the page.
3. Netlify gives you a URL such as `https://<name>.netlify.app`. Rename it under Site settings → Change site name, and put it in the submission.
4. To update the site, repeat step 1, then use Deploys → drag the `frontend/` folder again.

How it works: `app.js` first tries the live API (`api/fields`). On a static host that request fails, so the app
loads `api/fields.json` and `api/fields/<id>/report.json` instead, and shows a "Static version" banner.
Every field's report includes all candidate rotations, so the sliders and the water-cut simulator still work in the browser.

GitHub Pages works the same way: publish the `frontend/` folder.

### Optional: full backend on Render (free tier)

Use this only if you want the live API (`/api/...`, `/docs`).
1. Push the repo to GitHub, **including `data/field_data.json` and `data/crops.json`**.
2. On [render.com](https://render.com), choose New → Blueprint, then pick the repo. It reads `render.yaml`. Alternatively, choose New → Web Service and set:
   - Build: `pip install -r backend/requirements.txt`
   - Start: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
3. Open the `.onrender.com` URL. The first load after idle takes about 30–50 s while the free instance wakes up.

## Project layout

```
backend/app/main.py        API + serves frontend/ at /
backend/app/scoring.py     risk proxy, rotations, water-cut simulator
backend/fetch_data.py      downloads NASA POWER, MODIS (ORNL), SoilGrids -> data/
backend/export_static.py   writes frontend/api/*.json
data/fields.json           demo field coordinates
data/crops.json            FAO crop parameters (+ marked estimates)
data/field_data.json       built yearly series per field (API reads only this)
data/cache/raw/            raw API responses (cache; git-ignored except the Jizzakh sample)
frontend/                  index.html, app.js, i18n.js, style.css, vendor/ (Leaflet, Chart.js)
frontend/api/              static copy of the API (deploy this folder to Netlify)
```

## AI tools disclosure

We used AI coding assistants (Anthropic Claude, via Claude Code) to help write and refactor code
(data download, scoring logic, frontend fixes) and this README. The team chose the method,
the data sources and the FAO parameters, and reviewed the results. All data comes from the sources
listed above; no data was generated by AI. Any placeholder value is labelled SAMPLE or estimate.
