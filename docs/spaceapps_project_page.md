# Space Apps 2026 project page — "Field Shift: Adapting Farms with NASA Data"

Copy each section into the matching field on spaceappschallenge.org.

---

## Project name
AralSentinel

## One-line summary
A free, offline-ready map app that turns ten years of NASA satellite and climate data into a field-level salinity/drought risk index and ranks water-saving crop rotations for farmers in Uzbekistan.

---

## High-level project summary

**Problem.** Uzbekistan's irrigated farmland carries the legacy of the Aral Sea crisis: decades of cotton–wheat monoculture and heavy irrigation have left large areas salt-affected, while water is getting scarcer. At our Jizzakh pilot field, NASA POWER shows only 342 mm of rain a year over the last five years and about 16 mm in June–August, and MODIS measures summer land-surface temperatures of about 40 °C. Farmers and extension agents rarely have field-level evidence of which fields are at risk, or which rotation would save water and soil without losing income.

**What we built.** AralSentinel is a map-based web app in English, Uzbek and Russian. Clicking a field shows:
- 10-year trends (2015–2025) of NDVI, land-surface temperature, root-zone soil wetness, rainfall and peak air temperature;
- a transparent 0–100 salinity/drought **proxy** risk index with its main driver;
- the top 5 three-year crop rotations, built from FAO agronomic rules and re-ranked live by the farmer's priorities (save water / protect soil / income);
- a water-cut simulator that shows yield and income loss if irrigation is cut by 10–50 %.

**Who it helps.** Smallholder farmers, water-user associations and agricultural extension agents in Uzbekistan's irrigated regions (Jizzakh, Syrdarya, Tashkent, Karakalpakstan), plus students and NGOs working on the Aral Sea basin.

**Why it matters for Uzbekistan.** Water allocations are shrinking and salinity is rising. A tool that shows the cost of a water cut before the season, and that warns against water-hungry choices on dry fields (the "alfalfa trap"), helps farmers adapt crop choices instead of reacting to losses. It is free, needs no login, runs on a phone and works without internet.

---

## Project details

**How it works**
1. `backend/fetch_data.py` downloads and caches, once, for each demo field:
   - NASA POWER monthly data 2015–2025 (rainfall, root-zone soil wetness, max air temperature);
   - MODIS Terra NDVI (MOD13Q1) and land-surface temperature (MOD11A2) for June–August of each year, via the ORNL DAAC MODIS web service;
   - ISRIC SoilGrids soil pH, clay, sand and organic carbon at 0–30 cm.
2. A FastAPI backend computes the risk index and rotations. `backend/export_static.py` exports every result as static JSON, so the public site runs on Netlify with no server and works offline.

**Risk score method (proxy index, 0–100).** Each input is scaled 0–1 and weighted; missing inputs are dropped and the weights re-normalised:

| Component | Input | Weight |
|---|---|---|
| Low rainfall | POWER mean rain, last 5 years (400 → 100 mm/yr) | 0.20 |
| Dry root zone | POWER GWETROOT (0.6 → 0.2) | 0.20 |
| Summer heat | MODIS summer LST (35 → 50 °C) | 0.20 |
| Vegetation decline | NDVI least-squares trend 2015–2025 | 0.25 |
| Soil texture | SoilGrids clay % and pH | 0.15 |

Levels: low < 35 ≤ medium < 60 ≤ high. The heat term follows published work from Syrdarya showing that canopy/land-surface temperature from MODIS is a usable indicator of soil salinity on cropped land (see References 1–2). Satellites do not measure salinity directly, so we call it a proxy and show every input.

**Rotation ranking.** All 3-year sequences of six crops (cotton, winter wheat, alfalfa, maize, sorghum, mung bean) are generated, then filtered:
- no crop repeats in consecutive years (including Year 3 → Year 1);
- at least one legume;
- alfalfa only where water availability is high, otherwise an "alfalfa trap" warning;
- on high-risk fields, at least 2 of 3 years with salt-tolerant crops (FAO-29 threshold ≥ 6 dS/m).

Each rotation is scored for water saving (FAO-56 seasonal water need), salt tolerance (FAO-29), soil health (legumes, soil benefit) and income (yield × price, marked estimates). The final fit is weighted by the user's sliders and the field's risk, times a soil-pH suitability factor. The water-cut simulator uses the FAO-33 equation 1 − Ya/Ym = Ky (1 − ETa/ETm).

Example (Jizzakh, default priorities): risk 23 (low, main driver declining NDVI); best rotation Winter wheat → Sorghum → Mung bean (fit 69); a 20 % water cut means −20.3 % yield and about −$214/ha/yr (estimate).

**Tech stack.** Python 3 (FastAPI, Uvicorn, Requests), JavaScript, HTML, CSS, Leaflet 1.9.4, Chart.js 4.4.1 (vendored for offline use), Netlify static hosting, GitHub. No paid APIs, no API keys.

**Links**
- Live app: https://symphonious-twilight-34e8d7.netlify.app
- Source code: https://github.com/M10-MM/aralsentinel

**Limitations.** The risk score is an uncalibrated proxy (no field EC measurements). Yields and prices are rough estimates. Data are point samples (one MODIS pixel, one ~50 km POWER cell); MODIS QC layers were not applied. Fields are demo locations, not surveyed farms. Results are options to discuss with an agronomist, not advice.

---

## Use of NASA data
- **NASA POWER** (Prediction Of Worldwide Energy Resources), monthly point API, Agroclimatology community, MERRA-2 based — PRECTOTCORR (rain), GWETROOT (root-zone soil wetness), T2M_MAX (max air temperature), 2015–2025. https://power.larc.nasa.gov/
- **MODIS Terra MOD13Q1 v061**, 250 m 16-day vegetation indices (NDVI, June–August mean per year). https://lpdaac.usgs.gov/products/mod13q1v061/ — doi:10.5067/MODIS/MOD13Q1.061
- **MODIS Terra MOD11A2 v061**, 1 km 8-day land-surface temperature (LST_Day_1km, June–August mean per year). https://lpdaac.usgs.gov/products/mod11a2v061/ — doi:10.5067/MODIS/MOD11A2.061
- **ORNL DAAC MODIS/VIIRS Land Product Subsets web service**, used to download the MODIS pixels. https://modis.ornl.gov/data/modis_webservice.html — doi:10.3334/ORNLDAAC/1379
- **MERRA-2** reanalysis (NASA GMAO), the model behind the POWER variables. https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/

## Space agency partner data and other data
- No space-agency partner datasets were used.
- **ISRIC SoilGrids v2.0** — soil pH, clay, sand, organic carbon, 0–30 cm. https://soilgrids.org/
- **FAO Irrigation and Drainage Paper 33** (yield response to water, Ky). https://www.fao.org/4/i2800e/i2800e.pdf
- **FAO Irrigation and Drainage Paper 56** (crop water needs). https://www.fao.org/4/x0490e/x0490e00.htm
- **FAO Irrigation and Drainage Paper 29 Rev.1** (crop salt tolerance). https://www.fao.org/4/t0234e/t0234e00.htm
- Basemap: Esri World Imagery, OpenStreetMap fallback.

## References
1. Khasanov, S., Oymatov, R., Kulmatov, R. (2023). Canopy temperature: as an indicator of soil salinity (a case study in Syrdarya province, Uzbekistan). *IOP Conf. Ser.: Earth Environ. Sci.* 1142, 012109. https://doi.org/10.1088/1755-1315/1142/1/012109
2. Ivushkin, K., Bartholomeus, H., Bregt, A.K., Pulatov, A. (2017). Satellite thermography for soil salinity assessment of cropped areas in Uzbekistan. *Land Degradation & Development* 28(3), 870–877. https://doi.org/10.1002/ldr.2670
3. ICBA (International Center for Biosaline Agriculture) — on-farm demonstration trials of salt-tolerant crops (sorghum, pearl millet, triticale, mung bean and others) in Karauzyak district, Karakalpakstan, from 2015. Project reports via CGIAR MEL: https://mel.cgiar.org/reporting/downloadmelspace/hash/3ecdca986d039762b4f3b4772e9c2073/v/ea8783290e489977098adc4222b77d94
4. ICBA — Development of Sustainable Agricultural Production Systems in Degraded Areas of Karakalpakstan (2022–2026). https://www.biosaline.org/projects/development-sustainable-agricultural-production-systems-degraded-areas-karakalpakstan
5. NASA POWER Project, NASA Langley Research Center. https://power.larc.nasa.gov/
6. Didan, K. (2021). MOD13Q1 MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD13Q1.061
7. Wan, Z., Hook, S., Hulley, G. (2021). MOD11A2 MODIS/Terra Land Surface Temperature/Emissivity 8-Day L3 Global 1km SIN Grid V061. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD11A2.061
8. ORNL DAAC (2018). MODIS and VIIRS Land Products Global Subsetting and Visualization Tool. https://doi.org/10.3334/ORNLDAAC/1379
9. Poggio, L. et al. (2021). SoilGrids 2.0. *SOIL* 7, 217–240. https://doi.org/10.5194/soil-7-217-2021
10. Doorenbos, J., Kassam, A.H. (1979). Yield response to water. FAO Irrigation and Drainage Paper 33.
11. Allen, R.G. et al. (1998). Crop evapotranspiration. FAO Irrigation and Drainage Paper 56.
12. Ayers, R.S., Westcot, D.W. (1985). Water quality for agriculture. FAO Irrigation and Drainage Paper 29 Rev.1.

## Use of AI tools
We used AI assistants (Anthropic Claude, through Claude Code) to help write and refactor code (the data-download script, risk and rotation scoring, frontend fixes, offline mode, translations) and to draft written material (README, pitch, slides, these texts, the video script). The team chose the problem, data sources, method, FAO parameters and risk weights, and checked that every number we quote matches the app output and `data/field_data.json`. No data, images or results were generated by AI: all data comes from NASA POWER, MODIS (ORNL DAAC), ISRIC SoilGrids and FAO publications. Uzbek and Russian translations were drafted with AI help. Yields and prices are labelled as estimates.
