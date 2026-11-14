"""Export the API as static JSON into frontend/api/ so the frontend folder alone works
(offline, Netlify Drop, GitHub Pages). app.js falls back to these files when the live API fails.

Writes:
    frontend/api/fields.json
    frontend/api/fields/<id>/report.json   (default slider values + all candidate rotations,
                                             so the browser can re-rank when sliders move)
Run from the project root after backend/fetch_data.py:
    backend\\.venv\\Scripts\\python backend/export_static.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.main import ROOT, build_report, load  # noqa: E402

DEFAULT = {"water": 0.4, "soil": 0.3, "income": 0.3}   # same as the sliders in index.html
OUT = ROOT / "frontend" / "api"


def main():
    fields = load("fields.json")
    (OUT / "fields").mkdir(parents=True, exist_ok=True)
    (OUT / "fields.json").write_text(json.dumps(fields, ensure_ascii=False), encoding="utf-8")
    for f in fields:
        rep = build_report(f["id"], **DEFAULT, include_candidates=True)
        path = OUT / "fields" / f["id"] / "report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}  sample={rep['sample_data']}  candidates={len(rep['candidates'])}")
    print(f"done: {len(fields)} fields -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
