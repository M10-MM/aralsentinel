"""Salinity/drought PROXY risk, FAO-based rotation generator and water-cut simulator.

Satellites do not measure soil salt directly. The risk index combines conditions that
are known to drive secondary salinisation and crop stress in irrigated Central Asia:
dry climate, dry root zone, summer heat, declining vegetation and heavy/alkaline soil.
Thresholds below are team assumptions, documented next to each line.
"""
from itertools import product
from statistics import mean

# ---------------------------------------------------------------- helpers
def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def values(series) -> list[float]:
    return [p["value"] for p in (series or []) if p.get("value") is not None]


def recent_mean(series, n: int = 5):
    v = values(series)
    return mean(v[-n:]) if v else None


def slope_per_year(series):
    """Least-squares trend of a [{'year','value'}] series (units per year)."""
    pts = [(p["year"], p["value"]) for p in (series or []) if p.get("value") is not None]
    if len(pts) < 4:
        return None
    xs, ys = zip(*pts)
    mx, my = mean(xs), mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in pts) / den if den else None


# ---------------------------------------------------------------- risk (proxy)
RISK_WEIGHTS = {"rain": 0.20, "soil_moisture": 0.20, "heat": 0.20, "ndvi_trend": 0.25, "soil_texture": 0.15}


def risk_score(series: dict, soil_props: dict) -> dict:
    """0-100 salinity/drought PROXY index. Missing inputs are skipped and reported."""
    comp, inputs = {}, {}

    rain = recent_mean(series.get("rain"))
    if rain is not None:                                   # <100 mm/yr = 1, >400 mm/yr = 0
        comp["rain"] = clamp((400 - rain) / 300)
        inputs["rain_mm_yr"] = round(rain)

    wet = recent_mean(series.get("soil"))
    if wet is not None:                                    # GWETROOT 0.2 = 1, 0.6 = 0
        comp["soil_moisture"] = clamp((0.6 - wet) / 0.4)
        inputs["gwetroot"] = round(wet, 2)

    lst = recent_mean(series.get("lst"))
    tmax = recent_mean(series.get("tmax"))
    if lst is not None:                                    # MODIS Jun-Aug daytime LST 35 C = 0, 50 C = 1
        comp["heat"] = clamp((lst - 35) / 15)
        inputs["summer_lst_c"] = round(lst, 1)
    elif tmax is not None:                                 # fallback: POWER Jun-Aug monthly PEAK Tmax, 38 C = 0, 48 C = 1
        comp["heat"] = clamp((tmax - 38) / 10)
        inputs["summer_peak_tmax_c"] = round(tmax, 1)

    trend = slope_per_year(series.get("ndvi"))
    if trend is not None:                                  # -0.01 NDVI/yr or worse = 1
        comp["ndvi_trend"] = clamp(-trend / 0.01)
        inputs["ndvi_trend_per_yr"] = round(trend, 4)

    clay, ph = (soil_props or {}).get("clay_pct"), (soil_props or {}).get("ph")
    if clay is not None and ph is not None:                # heavy clay drains poorly; pH>8 hints sodicity
        comp["soil_texture"] = 0.5 * clamp((clay - 20) / 30) + 0.5 * clamp((ph - 7.5) / 1.5)
        inputs.update({"clay_pct": clay, "ph": ph})

    missing = [k for k in RISK_WEIGHTS if k not in comp]
    if not comp:
        return {"score": None, "level": "unknown", "main_driver": None, "missing": missing,
                "components": {}, "inputs": {}, "proxy": True}
    used = sum(RISK_WEIGHTS[k] for k in comp)              # re-normalise over available inputs
    contrib = {k: RISK_WEIGHTS[k] * comp[k] / used for k in comp}
    score = round(100 * sum(contrib.values()))
    level = "low" if score < 35 else "medium" if score < 60 else "high"
    return {
        "score": score, "level": level,
        "main_driver": max(contrib, key=contrib.get),
        "missing": missing,
        "components": {k: round(v, 2) for k, v in comp.items()},
        "contributions": {k: round(100 * v, 1) for k, v in contrib.items()},
        "inputs": inputs,
        "proxy": True,
    }


def water_availability(series: dict) -> str:
    """'high' only if the root zone is moist AND rainfall is not very low (proxy for irrigation supply)."""
    wet, rain = recent_mean(series.get("soil")), recent_mean(series.get("rain"))
    if wet is None or rain is None:
        return "unknown"
    return "high" if wet >= 0.5 and rain >= 300 else "low"


# ---------------------------------------------------------------- rotations
SALT_TOLERANT_ECE = 6.0   # FAO-29: threshold >= 6 dS/m = moderately tolerant or better


def _ph_factor(crop: dict, ph) -> float:
    """1.0 inside the crop's pH range, -0.15 per pH unit outside, min 0.6."""
    if ph is None:
        return 1.0
    lo, hi = crop["ph_range"]
    dist = max(lo - ph, ph - hi, 0)
    return max(0.6, 1 - 0.15 * dist)


def candidate_rotations(crops: dict, risk_level: str, water: str) -> tuple[list[tuple], list[str]]:
    """All 3-year sequences that obey the agronomic rules. Returns (rotations, warnings)."""
    warnings = []
    allowed = list(crops)
    if water != "high":
        allowed.remove("alfalfa")                          # "alfalfa trap": thirsty perennial
        warnings.append("alfalfa_trap")
    out = []
    for seq in product(allowed, repeat=3):
        if seq[0] == seq[1] or seq[1] == seq[2] or seq[2] == seq[0]:
            continue                                       # no same crop 2 years in a row (also when the cycle repeats)
        if not any(crops[c]["is_legume"] for c in seq):
            continue                                       # >= 1 legume in 3 years
        if risk_level == "high" and sum(crops[c]["salt_threshold_ece"] >= SALT_TOLERANT_ECE for c in seq) < 2:
            continue                                       # high-risk field: >= 2 salt-tolerant years
        out.append(seq)
    if risk_level == "high":
        warnings.append("salt_tolerant_only")
    return out, warnings


def score_rotation(seq, crops: dict, risk: dict, ph, weights: dict) -> dict:
    cs = [crops[c] for c in seq]
    water_need = mean(c["water_need_mm"] for c in cs)
    income_usd = mean(c["yield_t_ha"] * c["price_usd_t"] for c in cs)   # ESTIMATE, gross revenue / ha / yr
    max_income = max(c["yield_t_ha"] * c["price_usd_t"] for c in crops.values())

    water_saving = clamp((1300 - water_need) / 1000) * 100            # 300 mm = 100, 1300 mm = 0
    salt_tol = mean(clamp(c["salt_threshold_ece"] / 8) for c in cs) * 100
    soil_health = min(100, mean(c["soil_benefit"] for c in cs) + 10 * sum(c["is_legume"] for c in cs[:3]) / 1.5)
    income = income_usd / max_income * 100
    ph_fit = mean(_ph_factor(c, ph) for c in cs)

    # user weights + salt tolerance weighted by field risk
    w = {"water": weights.get("water", 0.33), "soil": weights.get("soil", 0.33),
         "income": weights.get("income", 0.33), "salt": (risk.get("score") or 0) / 100}
    total = sum(w.values()) or 1
    weighted = (w["water"] * water_saving + w["soil"] * soil_health +
                w["income"] * income + w["salt"] * salt_tol) / total
    fit = weighted * ph_fit

    return {
        "id": "-".join(seq),
        "crops": list(seq),
        "years": [c["name"] for c in cs],                               # [{en,uz,ru}, ...] year 1..3
        "name": {lg: " → ".join(c["name"][lg] for c in cs) for lg in ("en", "uz", "ru")},
        "fit": round(fit),
        "water_saving": round(water_saving),
        "salt_tolerance": round(salt_tol),
        "soil_health": round(soil_health),
        "income": round(income),
        "water_need_mm": round(water_need),
        "income_usd_ha": round(income_usd),
        "income_is_estimate": True,
        "ph_fit": round(ph_fit, 2),
    }


def rank_rotations(crops: dict, risk: dict, series: dict, soil_props: dict, weights: dict, top: int = 5):
    water = water_availability(series)
    seqs, warnings = candidate_rotations(crops, risk.get("level"), water)
    ph = (soil_props or {}).get("ph")
    scored = [score_rotation(s, crops, risk, ph, weights) for s in seqs]
    scored.sort(key=lambda r: r["fit"], reverse=True)
    # keep one order per crop set (scores do not depend on order), so the top 5 really differ
    seen, unique = set(), []
    for r in scored:
        key = frozenset(r["crops"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return (unique[:top] if top else unique), {"water_availability": water, "warnings": warnings, "candidates": len(seqs)}


# ---------------------------------------------------------------- water-cut simulator
def water_cut_simulation(rotation: dict, crops: dict, cuts=(10, 20, 30, 50)) -> list[dict]:
    """FAO-33: 1 - Ya/Ym = Ky * (1 - ETa/ETm). Assumes ETa/ETm = 1 - cut (no extra rain/groundwater)."""
    out = []
    for cut in cuts:
        losses, usd = [], []
        for name in rotation["crops"]:
            c = crops[name]
            loss = clamp(c["ky"] * cut / 100)                           # fraction of max yield lost
            losses.append(loss)
            usd.append(loss * c["yield_t_ha"] * c["price_usd_t"])
        out.append({"cut_pct": cut,
                    "yield_loss_pct": round(100 * mean(losses), 1),
                    "income_loss_usd_ha": round(mean(usd)),
                    "income_is_estimate": True})
    return out
