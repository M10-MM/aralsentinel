# AralSentinel — slides (7)

Screenshots are in `docs/screenshots/`. All numbers come from the app and `data/field_data.json`; *(estimate)* marks values based on the estimated yields and prices.

---

## Slide 1 — AralSentinel
**NASA data → crop rotations for saline, water-scarce fields in Uzbekistan**
- NASA Space Apps Challenge 2026 · "Field Shift: Adapting Farms with NASA Data"
- Live demo: {{NETLIFY_URL}}
- Open source: {{GITHUB_URL}}

🖼 Screenshot: `1_map_overview.png`

---

## Slide 2 — The problem (Jizzakh, 2015–2025)
- Rain: **365 mm/yr** on average, **342 mm/yr** over the last 5 years (NASA POWER)
- Summer is almost dry: **~16 mm** in total for June to August
- Summer land-surface temperature is **~40 °C** (MODIS Terra LST)
- Farmers choose next season's crops without field-level data on water, heat or salt risk

🖼 Screenshot: crop of the charts from `2_jizzakh_report.png` (rain + surface temperature)

---

## Slide 3 — What AralSentinel does
- **Risk:** a 0–100 salinity/drought **proxy** index, with its main driver
- **Rotations:** the top 5 three-year rotations, ranked by the farmer's own priorities (water / soil / income)
- **Water-cut simulator:** yield and income loss at −10 / −20 / −30 / −50 % water
- EN / UZ / RU, works on a phone and **works offline**

🖼 Screenshot: `2_jizzakh_report.png`

---

## Slide 4 — Rotations that follow FAO rules
- 96 valid rotations generated for the Jizzakh field: no crop two years in a row, ≥ 1 legume, salt-tolerant crops on high-risk fields
- Best for the default priorities: **Winter wheat → Sorghum → Mung bean**, averaging **450 mm/season**, against **900 mm** for cotton (FAO-33)
- **"Alfalfa trap"** warning where water is scarce (Karakalpakstan: 209 mm/yr rain, risk 40)
- Moving the sliders re-ranks the table live

🖼 Screenshot: `3_rotation_table.png`

---

## Slide 5 — What a water cut costs
- FAO-33: **1 − Ya/Ym = Ky × (1 − ETa/ETm)**
- Jizzakh, best rotation: **−20 % water → −20.3 % yield, −$214/ha/yr** *(estimate)*
- **−50 % water → −50.8 % yield, −$535/ha/yr** *(estimate)*
- Farmers can plan before the season, not after the harvest fails

🖼 Screenshot: `4_water_cut_simulator.png`

---

## Slide 6 — Data, method and honesty
- **NASA POWER (MERRA-2):** rain, root-zone wetness, Tmax · **MODIS Terra MOD13Q1** NDVI 250 m · **MOD11A2** LST 1 km · **ISRIC SoilGrids**
- **FAO-33 / FAO-56 / FAO-29:** water needs, yield response, salt tolerance
- The risk score is a **proxy** (satellites do not measure salt directly), prices are **estimates**, resolution is 250 m–1 km for MODIS and ~0.5° for POWER
- The limitations are written on the page itself

🖼 Screenshot: `5_about_limitations.png`

---

## Slide 7 — Next steps
- Real farm boundaries and more fields: the pipeline already takes any coordinates
- Calibrate the index with soil-salinity (EC) samples, and add SMAP soil moisture
- **Pilot in Jizzakh** with Uzbekcosmos and extension services, with an agronomist review of the crop table
- **Try it:** {{NETLIFY_URL}}

🖼 Screenshot: `6_full_page.png` (or a QR code to the live URL)
