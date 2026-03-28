"""
FastAPI application — upload Rent Roll + T12 PDFs, receive generated Word report.

Endpoints:
  POST /generate-report   — upload both PDFs, returns .docx download
  GET  /health            — health check
"""
import os
import sys
import uuid
import tempfile
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

# Ensure project root is on sys.path so 'src' resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extractors import RentRollExtractor, T12Extractor
from src.generators import NarrativeGenerator, FullReportGenerator
from src.main import _build_occupancy_analysis, _build_financial_analysis, _build_collections_analysis

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "property_config.yaml"


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


app = FastAPI(
    title="Monthly Analysis Report Generator",
    description="Upload Rent Roll and T12 Financial PDFs to generate a Word report.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate-report")
async def generate_report(
    rent_roll: UploadFile = File(..., description="Rent Roll PDF"),
    financials: UploadFile = File(..., description="T12 Financials PDF"),
):
    # Validate file types
    for f in (rent_roll, financials):
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{f.filename} is not a PDF.")

    # Work inside a temp directory — cleaned up after response is sent
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        rr_path  = tmp_dir / f"rent_roll_{uuid.uuid4().hex}.pdf"
        fin_path = tmp_dir / f"financials_{uuid.uuid4().hex}.pdf"
        out_path = tmp_dir / "report.docx"

        # Save uploads to disk
        for upload, dest in ((rent_roll, rr_path), (financials, fin_path)):
            with open(dest, "wb") as fh:
                shutil.copyfileobj(upload.file, fh)

        # Extract
        rr  = RentRollExtractor(str(rr_path)).extract()
        t12 = T12Extractor(str(fin_path)).extract()

        # Analyse
        occ = _build_occupancy_analysis(rr)
        fin = _build_financial_analysis(t12)
        col = _build_collections_analysis(rr)

        # Generate narratives + report
        cfg = _load_config()
        ng  = NarrativeGenerator(config=cfg)
        gen = FullReportGenerator(rr, t12, occ, fin, col, ng, config_path=str(CONFIG_PATH))
        gen.generate(str(out_path))

        # Build a clean download filename
        safe_name = rr.property_name.replace(" ", "_").replace("/", "-")
        download_name = f"{safe_name}_Monthly_Analysis_Report.docx"

        return FileResponse(
            path=str(out_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=download_name,
            background=_cleanup(tmp_dir),
        )

    except HTTPException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── background cleanup ────────────────────────────────────────────────────────
from starlette.background import BackgroundTask

def _cleanup(path: Path) -> BackgroundTask:
    return BackgroundTask(shutil.rmtree, str(path), True)
