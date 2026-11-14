"""AralSentinel API (NASA Space Apps 2026 - Field Shift).

Reads ONLY local files (no live calls during the demo):
    data/fields.json      demo fields
    data/field_data.json  built by backend/fetch_data.py
    data/crops.json       FAO crop parameters

Run from the project root:
    backend\\.venv\\Scripts\\python -m uvicorn backend.app.main:app --port 8000
Then open http://localhost:8000  (API docs: /docs)
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .scoring import rank_rotations, risk_score, water_cut_simulation

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

app = FastAPI(title="AralSentinel API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@lru_cache(maxsize=8)
def _load(name: str, mtime: float):
    """Cached JSON load; mtime in the key means edits are picked up without a restart."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load(name: str):
    path = DATA / name
    if not path.exists():
        raise HTTPException(503, f"{name} missing. Run: python backend/fetch_data.py")
    return _load(name, path.stat().st_mtime)


def build_report(field_id: str, water: float, soil: float, income: float, include_candidates: bool = False) -> dict:
    """Shared by the API and backend/export_static.py."""
    field = next((f for f in load("fields.json") if f["id"] == field_id), None)
    if not field:
        raise HTTPException(404, f"Unknown field '{field_id}'")
    crops = load("crops.json")["crops"]
    fd = load("field_data.json")["fields"].get(field_id)
    if fd is None:
        raise HTTPException(503, f"No data for '{field_id}'. Run: python backend/fetch_data.py")

    series, soil_props = fd["series"], fd.get("soil_props") or {}
    risk = risk_score(series, soil_props)
    weights = {"water": water, "soil": soil, "income": income}
    rotations, meta = rank_rotations(crops, risk, series, soil_props, weights)
    report = {
        "field": {k: field[k] for k in ("id", "name", "lat", "lon") if k in field} | {"region": field.get("region")},
        "sample_data": fd.get("sample", False),
        "risk": risk,
        "series": {k: series.get(k, []) for k in ("ndvi", "lst", "soil", "rain", "tmax")},
        "soil_props": soil_props,
        "sources": fd.get("sources", {}),
        "rotations": rotations,
        "rotation_meta": meta,
        "water_cut": water_cut_simulation(rotations[0], crops) if rotations else [],
        "weights": weights,
    }
    if include_candidates:
        # static/offline mode: every valid rotation with its own water-cut table,
        # so the browser can re-rank them when the sliders move (same formula as scoring.py)
        everything, _ = rank_rotations(crops, risk, series, soil_props, weights, top=None)
        report["candidates"] = [r | {"water_cut": water_cut_simulation(r, crops)} for r in everything]
    return report


@app.get("/api/fields")
def list_fields():
    return load("fields.json")


@app.get("/api/fields/{field_id}/report")
def field_report(
    field_id: str,
    water: float = Query(0.4, ge=0, le=1),
    soil: float = Query(0.3, ge=0, le=1),
    income: float = Query(0.3, ge=0, le=1),
):
    return build_report(field_id, water, soil, income)


# Serve the frontend from the same server: http://localhost:8000/
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
