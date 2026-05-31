#!/usr/bin/env python3
"""
server.py
─────────
Local web UI for converting SAP Experience Garage interview .docx transcripts
to the canonical bronze JSON schema.

Wraps the existing ``convert_interview.py`` CLI (called as a subprocess so the
converter itself stays untouched) behind a small FastAPI app, and serves a
single-page front-end from ``static/index.html``.

Run (from inside ``recommendation_engine/``):

    uvicorn tools.server:app --reload

Then open http://127.0.0.1:8000/ in a browser.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ──────────────────────────────────────────────────────────────────────────────
# Paths (all resolved relative to this file so the working directory doesn't matter)
# ──────────────────────────────────────────────────────────────────────────────

TOOLS_DIR = Path(__file__).resolve().parent
CONVERTER = TOOLS_DIR / "convert_interview.py"
TRANSCRIPTS_DIR = TOOLS_DIR / "transcripts"
JSON_OUT_DIR = TRANSCRIPTS_DIR / "json_out"
STATIC_DIR = TOOLS_DIR / "static"

TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
JSON_OUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="SAP ExG — Interview Transcript Converter")


def _first_turns(record: dict, limit: int = 3) -> list[dict]:
    """Flatten the first ``limit`` speaker turns across all blocks for preview."""
    turns: list[dict] = []
    for block in record.get("blocks", []):
        for turn in block.get("turns", []):
            turns.append({"block": block.get("name", ""), **turn})
            if len(turns) >= limit:
                return turns
    return turns


def _convert_one(upload: UploadFile, raw: bytes) -> dict:
    """Save one upload, run the converter subprocess, and build a result dict."""
    filename = Path(upload.filename or "").name  # strip any path components

    if not filename.lower().endswith(".docx"):
        return {
            "filename": filename or "(unnamed)",
            "success": False,
            "error": "Not a .docx file.",
        }

    docx_path = TRANSCRIPTS_DIR / filename
    out_path = JSON_OUT_DIR / (Path(filename).stem + ".json")

    try:
        docx_path.write_bytes(raw)
    except OSError as exc:
        return {"filename": filename, "success": False, "error": f"Could not save file: {exc}"}

    # Call the existing CLI converter as a subprocess — convert_interview.py untouched.
    proc = subprocess.run(
        [sys.executable, str(CONVERTER), str(docx_path), "--out", str(out_path)],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0 or not out_path.exists():
        return {
            "filename": filename,
            "success": False,
            "error": (proc.stderr or proc.stdout or "Converter failed.").strip(),
        }

    try:
        record = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"filename": filename, "success": False, "error": f"Could not read output JSON: {exc}"}

    return {
        "filename": filename,
        "success": True,
        "error": None,
        "json_filename": out_path.name,
        "stats": record.get("stats", {}),
        "participant": record.get("metadata", {}).get("participant", {}),
        "preview_turns": _first_turns(record, 3),
    }


@app.post("/convert")
async def convert(files: list[UploadFile] = File(...)) -> JSONResponse:
    """Accept one or more .docx uploads, convert each, return per-file results."""
    results = []
    for upload in files:
        raw = await upload.read()
        results.append(_convert_one(upload, raw))
    return JSONResponse({"results": results})


@app.get("/download/{json_filename}")
def download(json_filename: str) -> FileResponse:
    """Serve a converted .json from json_out/ as a download."""
    safe = Path(json_filename).name  # prevent path traversal
    path = JSON_OUT_DIR / safe
    if not path.exists():
        return JSONResponse({"error": "Not found."}, status_code=404)
    return FileResponse(path, media_type="application/json", filename=safe)


@app.get("/")
def index() -> FileResponse:
    """Serve the single-page front-end."""
    return FileResponse(STATIC_DIR / "index.html")


# Serve any other static assets (kept after the routes above so "/" maps to index.html).
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
