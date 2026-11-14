"""Pre-download ALL data for every field in data/fields.json, then build data/field_data.json.

The API reads only data/field_data.json, so the demo needs no internet.
Every raw response is cached in data/cache/raw/ and never downloaded twice.

Sources (all free, no API key):
  rain, soil wetness, air temp : NASA POWER monthly (MERRA-2 based)      2015-2025
  NDVI                         : MODIS Terra MOD13Q1 v061 via ORNL DAAC   growing season (DOY 153-244)
  LST                          : MODIS Terra MOD11A2 v061 via ORNL DAAC   summer (DOY 153-244)
  soil properties (static)     : ISRIC SoilGrids v2.0                     0-30 cm average

Run from the project root:
    backend\\.venv\\Scripts\\python backend/fetch_data.py            # download missing + build
    backend\\.venv\\Scripts\\python backend/fetch_data.py --offline  # build from cache only
    backend\\.venv\\Scripts\\python backend/fetch_data.py --skip-modis
"""
import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "cache" / "raw"
OUT = DATA / "field_data.json"
RAW.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2015, 2026))
OFFLINE = False  # set by --offline: never touch the network

POWER_URL = ("https://power.larc.nasa.gov/api/temporal/monthly/point?start=2015&end=2025"
             "&latitude={lat}&longitude={lon}&community=ag"
             "&parameters=PRECTOTCORR,GWETROOT,T2M_MAX&format=json")
ORNL_URL = ("https://modis.ornl.gov/rst/api/v1/{product}/subset?latitude={lat}&longitude={lon}"
            "&band={band}&startDate=A{year}{d0:03d}&endDate=A{year}{d1:03d}"
            "&kmAboveBelow=0&kmLeftRight=0")
SOIL_URL = ("https://rest.isric.org/soilgrids/v2.0/properties/query?lat={lat}&lon={lon}"
            "&property=phh2o&property=clay&property=sand&property=soc"
            "&depth=0-5cm&depth=5-15cm&depth=15-30cm&value=mean")

# ORNL allows max 10 composites per request. NDVI (16-day) fits in one window;
# LST (8-day) needs two windows to cover DOY 153-244.
NDVI_WINDOWS = [(153, 244)]
LST_WINDOWS = [(153, 196), (201, 244)]

RETRY_STATUS = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------- download helpers
def cached_get(url: str, name: str, headers=None, tries=5, sleep_after=0.0):
    """Return parsed JSON from data/cache/raw/<name>, downloading it once if needed.

    Retries 429/5xx/timeouts with exponential backoff. Returns None on permanent failure
    (failures are NOT cached, so the next run tries again)."""
    path = RAW / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if OFFLINE:
        return None
    delay = 5
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code in RETRY_STATUS:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            if r.status_code != 200:
                print(f"   ! {name}: HTTP {r.status_code} {r.text[:120]}")
                return None
            data = r.json()
            path.write_text(json.dumps(data), encoding="utf-8")
            time.sleep(sleep_after)
            return data
        except (requests.RequestException, ValueError) as e:
            print(f"   retry {attempt}/{tries} {name}: {e}; waiting {delay}s")
            time.sleep(delay)
            delay *= 2
    return None


# ---------------------------------------------------------------- parsers
def parse_power(d) -> dict:
    """Yearly rain (mm/yr), root-zone wetness (0-1), summer Tmax (deg C). -999 = fill."""
    if not d:
        return {}
    p = d["properties"]["parameter"]
    ok = lambda v: v is not None and v > -900
    rain, wet, tmax = [], [], []
    for y in YEARS:
        v = p["PRECTOTCORR"].get(f"{y}13")
        if ok(v):
            rain.append({"year": y, "value": round(v * 365, 1)})   # mm/day annual mean -> mm/yr
        v = p["GWETROOT"].get(f"{y}13")
        if ok(v):
            wet.append({"year": y, "value": round(v, 3)})
        jja = [p["T2M_MAX"].get(f"{y}{m:02d}") for m in (6, 7, 8)]
        if all(ok(v) for v in jja):
            tmax.append({"year": y, "value": round(mean(jja), 2)})  # Jun-Aug mean of monthly PEAK Tmax
    return {"rain": rain, "soil": wet, "tmax": tmax}


def ornl_values(d, scale: float, valid) -> list[float]:
    """Scaled, valid pixel values from an ORNL subset response."""
    if not d or "subset" not in d:
        return []
    return [v * scale for s in d["subset"] for v in s.get("data", []) if v is not None and valid(v)]


def parse_soil(d) -> dict:
    """0-30 cm average. After d_factor: pH, clay %, sand %, SOC g/kg."""
    if not d:
        return {}
    out = {}
    for layer in d["properties"]["layers"]:
        f = layer["unit_measure"].get("d_factor") or 1
        vals = [dp["values"]["mean"] for dp in layer["depths"] if dp["values"].get("mean") is not None]
        if vals:
            out[layer["name"]] = round(mean(vals) / f, 2)
    if not out:
        return {}
    return {"ph": out.get("phh2o"), "clay_pct": out.get("clay"),
            "sand_pct": out.get("sand"), "soc_g_kg": out.get("soc")}


# ---------------------------------------------------------------- per-field fetch
def fetch_modis_year(field: dict, year: int) -> tuple[int, float | None, float | None]:
    fid, lat, lon = field["id"], field["lat"], field["lon"]
    hdr = {"Accept": "application/json"}
    ndvi_vals, lst_vals = [], []
    for d0, d1 in NDVI_WINDOWS:
        url = ORNL_URL.format(product="MOD13Q1", band="250m_16_days_NDVI", lat=lat, lon=lon, year=year, d0=d0, d1=d1)
        d = cached_get(url, f"ndvi_{fid}_{year}_{d0}.json", headers=hdr)
        ndvi_vals += ornl_values(d, 0.0001, lambda v: v != -3000)          # -3000 = fill
    for d0, d1 in LST_WINDOWS:
        url = ORNL_URL.format(product="MOD11A2", band="LST_Day_1km", lat=lat, lon=lon, year=year, d0=d0, d1=d1)
        d = cached_get(url, f"lst_{fid}_{year}_{d0}.json", headers=hdr)
        lst_vals += ornl_values(d, 0.02, lambda v: v > 0)                   # 0 = fill; Kelvin*50
    ndvi = round(mean(ndvi_vals), 4) if ndvi_vals else None
    lst = round(mean(lst_vals) - 273.15, 2) if lst_vals else None           # K -> deg C
    return year, ndvi, lst


def fetch_field(field: dict, skip_modis: bool) -> dict:
    fid, lat, lon = field["id"], field["lat"], field["lon"]
    print(f"== {fid} ({lat}, {lon})")
    power = parse_power(cached_get(POWER_URL.format(lat=lat, lon=lon), f"power_{fid}.json"))
    print(f"   POWER: rain {len(power.get('rain', []))} y, soil {len(power.get('soil', []))} y, tmax {len(power.get('tmax', []))} y")

    soil_cached = (RAW / f"soil_{fid}.json").exists()
    soil = parse_soil(cached_get(SOIL_URL.format(lat=lat, lon=lon), f"soil_{fid}.json",
                                 sleep_after=0 if soil_cached else 13))  # SoilGrids ~5 req/min
    print(f"   SoilGrids: {soil or 'no data'}")

    ndvi, lst = [], []
    if not skip_modis:
        with ThreadPoolExecutor(max_workers=4) as ex:
            for year, n, t in sorted(ex.map(lambda y: fetch_modis_year(field, y), YEARS)):
                if n is not None:
                    ndvi.append({"year": year, "value": n})
                if t is not None:
                    lst.append({"year": year, "value": t})
    print(f"   MODIS: NDVI {len(ndvi)} y, LST {len(lst)} y")

    series = {"ndvi": ndvi, "lst": lst, "soil": power.get("soil", []),
              "rain": power.get("rain", []), "tmax": power.get("tmax", [])}
    sources = {
        "ndvi": "MODIS Terra MOD13Q1 v061 NDVI 250 m, Jun-Aug mean (ORNL DAAC)",
        "lst": "MODIS Terra MOD11A2 v061 LST_Day 1 km, Jun-Aug mean (ORNL DAAC)",
        "soil": "NASA POWER GWETROOT root-zone soil wetness (MERRA-2)",
        "rain": "NASA POWER PRECTOTCORR precipitation (MERRA-2)",
        "tmax": "NASA POWER T2M_MAX (monthly peak daily max), Jun-Aug mean (MERRA-2)",
        "soil_props": "ISRIC SoilGrids v2.0, 0-30 cm mean",
    }
    sources = {k: v for k, v in sources.items() if (series.get(k) if k != "soil_props" else soil)}
    has_any = any(series.values())
    if not has_any:
        return sample_field(field)
    return {"sample": False, "series": series, "soil_props": soil, "sources": sources}


def sample_field(field: dict) -> dict:
    """Clearly labelled FAKE values, used only when no real data could be downloaded."""
    print(f"   !! no real data for {field['id']} -> SAMPLE values")
    rnd = random.Random(field["id"])
    s = lambda start, trend, noise: [{"year": y, "value": round(start + trend * i + rnd.uniform(-noise, noise), 3)}
                                     for i, y in enumerate(YEARS)]
    return {
        "sample": True,
        "series": {"ndvi": s(0.45, -0.006, 0.02), "lst": s(38, 0.15, 0.6), "soil": s(0.45, -0.005, 0.02),
                   "rain": s(250, -3, 30), "tmax": s(33, 0.1, 0.5)},
        "soil_props": {"ph": 8.0, "clay_pct": 25.0, "sand_pct": 35.0, "soc_g_kg": 6.0},
        "sources": {"all": "SAMPLE values (not real data) - download failed"},
    }


def main():
    global OFFLINE
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="build from cache only, no network")
    ap.add_argument("--skip-modis", action="store_true", help="skip slow ORNL MODIS downloads")
    ap.add_argument("--only", nargs="*", help="field ids to download (others are rebuilt from cache)")
    args = ap.parse_args()
    OFFLINE = args.offline

    fields = json.loads((DATA / "fields.json").read_text(encoding="utf-8"))
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "years": [YEARS[0], YEARS[-1]], "fields": {}}
    # demo priority: Jizzakh fields first, so they are ready even if the run is cut short
    for f in sorted(fields, key=lambda f: "jizzakh" not in f["id"].lower()):
        if args.only and f["id"] not in args.only:
            OFFLINE, saved = True, OFFLINE          # not selected: build from cache, no network
            out["fields"][f["id"]] = fetch_field(f, args.skip_modis)
            OFFLINE = saved
        else:
            out["fields"][f["id"]] = fetch_field(f, args.skip_modis)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    n_sample = sum(v["sample"] for v in out["fields"].values())
    print(f"\nWrote {OUT.relative_to(ROOT)}: {len(fields)} fields, {n_sample} with SAMPLE data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
