# AralSentinel — 5-minute pitch (English)

Live demo: https://symphonious-twilight-34e8d7.netlify.app · Code: https://github.com/M10-MM/aralsentinel

> Every number below comes from `data/field_data.json`, `data/crops.json` or the app's own output,
> using the default sliders (water 0.4, soil 0.3, income 0.3).
> Numbers marked *(estimate)* depend on the estimated yields and prices in `data/crops.json`.

---

## Spoken script (≈ 5:00)

### 0:00 – 0:40 · Problem
> "This is Jizzakh, in the heart of Uzbekistan's irrigated cotton belt, downstream of the shrinking Aral Sea basin.
> NASA's POWER data shows that this field gets on average **365 millimetres of rain a year** between 2015 and 2025, and only **342 mm** over the last five years.
> In summer, when crops need water most, it gets almost nothing: **about 16 millimetres in total for June, July and August**.
> Meanwhile, MODIS sees the land surface reaching **about 40 °C** on summer days.
> Every drop comes from irrigation, and irrigation water that evaporates in this heat leaves salt behind.
> Farmers have to decide what to plant next year, with less water, more heat and more salt, and they have almost no field-level data to decide with."

### 0:40 – 1:05 · Solution
> "AralSentinel turns free NASA satellite and climate data into three answers for any field:
> one, how high is the salinity and drought risk;
> two, which **three-year crop rotation** fits this field and the farmer's priorities;
> and three, **what happens to yield and income if the water allocation is cut**.
> It runs in the browser, in English, Uzbek and Russian, and it works offline."

### 1:05 – 2:50 · Live demo (exact clicks)
1. **Open https://symphonious-twilight-34e8d7.netlify.app.** The Jizzakh demo field opens automatically.
   > "This is a real field location in Jizzakh. Ten years of NASA data are already loaded."
2. **Point at the risk card: 23, Low risk · proxy index.**
   > "The risk index is 23 out of 100, which is low. The biggest contributor is the vegetation trend: NDVI has slightly declined, by about 0.003 per year. Rainfall is 342 millimetres a year, root-zone soil wetness is 0.55, and the soil has pH 7.67 and 30 % clay."
3. **Scroll over the 5 charts.**
   > "Five ten-year series: MODIS vegetation, MODIS summer surface temperature, NASA POWER root-zone wetness, rainfall, and summer peak air temperature."
4. **Rotation table: row 1 is *Winter wheat → Sorghum → Mung bean*, fit 69.**
   > "The app generated 96 valid three-year rotations for this field using FAO rules: no crop two years in a row, at least one legume, and salt-tolerant crops where risk is high. The best one for these priorities is winter wheat, then sorghum, then mung bean. By FAO water needs it averages **450 mm per season**, half of cotton's **900 mm**."
5. **Drag *Income* to the right and *Save water* to the left.**
   > "If the farmer cares most about income, the ranking changes live: cotton comes back to the top."
   **Then put the sliders back** (water 0.4, soil 0.3, income 0.3).
6. **Water-cut simulator: click −20 %, then −50 %.**
   > "Now the question every farmer here faces: what if the canal delivers less water? With FAO-33's yield-response equation, a **20 % water cut** costs the best rotation **20.3 % of its yield, about 214 dollars per hectare per year** *(estimate)*. A 50 % cut costs **50.8 %, about 535 dollars** *(estimate)*."
7. **Click the *Karakalpakstan demo field* button.**
   > "Closer to the Aral Sea it is much drier: **209 mm** of rain a year over the last five years, and only **157 mm** on average since 2015. Summer surface temperature is **43.9 °C**, and risk is **40, medium**. Water availability is low, so the app warns about the **'alfalfa trap'**: alfalfa is great for soil, but it needs about **1,100 mm**, so it is excluded here."
8. **Switch the language to *O'zbekcha*, then *Русский*.**
   > "Everything is available in Uzbek and Russian, the languages farmers and extension officers actually use."

### 2:50 – 3:30 · How it works
> "We use four open sources and no API keys.
> **NASA POWER**, based on the **MERRA-2** reanalysis, for monthly rainfall, root-zone soil wetness and air temperature.
> **MODIS on NASA's Terra satellite**: **MOD13Q1** NDVI at 250 metres and **MOD11A2** land-surface temperature at 1 kilometre, through the ORNL DAAC web service.
> **ISRIC SoilGrids** for soil pH, clay, sand and organic carbon.
> And three FAO handbooks: **FAO-33 and FAO-56** for crop water needs and yield response, and **FAO-29** for crop salt tolerance.
> A Python script downloads everything once and caches it, and the app then needs no internet at all."

### 3:30 – 4:05 · Impact for farmers
> "It is open and free: a link that works on a phone, even offline.
> It makes trade-offs visible: the same field, three priorities, different answers.
> It puts a number on water cuts *before* the season, for example 214 dollars per hectare for a 20 % cut on the Jizzakh field *(estimate)*.
> And it protects farmers from common mistakes, like planting thirsty alfalfa where water will not arrive."

### 4:05 – 4:30 · Honesty and limitations
> "We want to be clear about what this is.
> The risk score is a **proxy index**: satellites cannot measure salt directly, and we have not yet calibrated it against field salinity measurements.
> Yields and prices are **estimates**, so the dollar figures are indicative.
> Resolution is one MODIS pixel and a roughly 50-kilometre climate grid per field.
> Every one of these limitations is written on the page itself, under *About, limitations & honesty*."

### 4:30 – 4:50 · Next steps
> "Next, we want to add real farm boundaries instead of four demo points, calibrate the index with soil-salinity samples, and add SMAP soil moisture. We would like to run a pilot in Jizzakh with Uzbekcosmos and local extension services, and check the crop table with agronomists."

### 4:50 – 5:00 · Closing
> "NASA satellites already watch every field in Uzbekistan. AralSentinel turns that into a decision a farmer can make before the water runs out. Thank you."

---

## Numbers used (source → value)

| Claim | Value | Source |
|---|---|---|
| Jizzakh rain, mean 2015–2025 | 365 mm/yr (range 256–584) | `field_data.json` → jizzakh-1 → rain |
| Jizzakh rain, last 5 years | 342 mm/yr | app risk inputs |
| Jizzakh rain, Jun–Aug total | 16.4 mm mean (range 4.5–36.2) | `data/cache/raw/power_jizzakh-1.json` monthly PRECTOTCORR |
| Jizzakh summer LST | 39.9 °C mean, max 41.5 °C (2023); last 5 yrs 39.5 °C | MOD11A2 series |
| Jizzakh root-zone wetness | 0.55 (last 5 yrs) | POWER GWETROOT |
| Jizzakh soil | pH 7.67, clay 30.33 % | SoilGrids |
| Jizzakh risk | 23, low, driver NDVI trend (−0.0028/yr) | app |
| Jizzakh valid rotations | 96 | app `rotation_meta.candidates` |
| Best rotation, Jizzakh | Winter wheat → Sorghum → Mung bean, fit 69, 450 mm/season avg | app + `crops.json` |
| Cotton water need | 900 mm/season | `crops.json` (FAO-33) |
| Water cut −20 % / −50 % | −20.3 % / −50.8 % yield; −$214 / −$535 per ha per yr *(estimate)* | app `water_cut` |
| Karakalpakstan | rain 209 mm/yr last 5 yrs (157 mean 2015–2025), summer LST 43.9 °C last 5 yrs, risk 40 medium, alfalfa trap | app + `field_data.json` |
| Income slider max, water 0 (Jizzakh) | top = Cotton → Winter wheat → Alfalfa, fit 81 | app |
| Alfalfa water need | 1,100 mm/season | `crops.json` |

---

## 10 likely jury questions

1. **"Can satellites really see salt?"**
   Not directly. That is why we call it a *proxy* index. We combine conditions that drive salinisation and crop stress (dry climate, dry root zone, heat, falling NDVI, heavy alkaline soil). The next step is calibration with field EC samples.

2. **"Why these weights and thresholds?"**
   They are transparent team assumptions, documented line by line in `backend/app/scoring.py` and in the README. They can be tuned once we have field measurements.

3. **"Where do the crop numbers come from?"**
   Water needs and Ky come from FAO-33/56, and salt-tolerance thresholds from FAO-29 (Ayers & Westcot). Yields and prices are labelled estimates and are only used to compare rotations.

4. **"How accurate is the water-cut simulator?"**
   It is the standard FAO-33 seasonal equation 1 − Ya/Ym = Ky(1 − ETa/ETm). It assumes the water cut reduces evapotranspiration by the same share and ignores rain and groundwater. It is a planning estimate, not a forecast.

5. **"Which NASA data exactly?"**
   NASA POWER (MERRA-2) monthly PRECTOTCORR, GWETROOT and T2M_MAX; MODIS Terra MOD13Q1 v061 NDVI and MOD11A2 v061 LST_Day, 2015–2025, via ORNL DAAC.

6. **"What resolution?"**
   NDVI at 250 m, LST at 1 km, POWER on a grid of roughly 0.5°. That is good for screening a field or district, not for variation inside a field.

7. **"Does it work without internet?"**
   Yes. All data is pre-downloaded, the libraries are bundled, and the site is static. Without internet only the background satellite imagery is missing; the markers, charts and rankings all work.

8. **"Why is alfalfa excluded on some fields?"**
   It needs about 1,100 mm a season. Where root-zone wetness and rainfall indicate low water availability, recommending it would set farmers up to fail (the "alfalfa trap").

9. **"How would a farmer actually use it?"**
   Through an extension officer or a phone: open the link, find the field, set priorities, compare rotations, and check the cost of a water cut before signing up for next season's crops.

10. **"What's next / how does it scale?"**
    Real field polygons, more fields (the pipeline already takes any coordinates from `fields.json`), SMAP soil moisture, calibration samples, and a Jizzakh pilot with Uzbekcosmos and extension services.
