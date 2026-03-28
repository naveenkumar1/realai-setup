"""
FastAPI application — upload Rent Roll + T12 PDFs, receive generated Word report.

Local:  POST /generate-report  → returns .docx as direct download
Lambda: POST /generate-report  → uploads .docx to S3, returns presigned URL
GET  /health → health check
"""
import os
import sys
import uuid
import tempfile
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask
from mangum import Mangum

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extractors import RentRollExtractor, T12Extractor
from src.generators import NarrativeGenerator, FullReportGenerator
from src.main import _build_occupancy_analysis, _build_financial_analysis, _build_collections_analysis

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "property_config.yaml"
S3_BUCKET   = os.environ.get("REPORT_S3_BUCKET", "")
IS_LAMBDA   = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


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
    return {"status": "ok", "runtime": "lambda" if IS_LAMBDA else "local"}


@app.post("/generate-report")
async def generate_report(
    rent_roll:  UploadFile = File(..., description="Rent Roll PDF"),
    financials: UploadFile = File(..., description="T12 Financials PDF"),
):
    for f in (rent_roll, financials):
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{f.filename} is not a PDF.")

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        rr_path  = tmp_dir / f"rent_roll_{uuid.uuid4().hex}.pdf"
        fin_path = tmp_dir / f"financials_{uuid.uuid4().hex}.pdf"
        out_path = tmp_dir / "report.docx"

        for upload, dest in ((rent_roll, rr_path), (financials, fin_path)):
            with open(dest, "wb") as fh:
                shutil.copyfileobj(upload.file, fh)

        rr  = RentRollExtractor(str(rr_path)).extract()
        t12 = T12Extractor(str(fin_path)).extract()

        occ = _build_occupancy_analysis(rr)
        fin = _build_financial_analysis(t12)
        col = _build_collections_analysis(rr)

        cfg = _load_config()
        ng  = NarrativeGenerator(config=cfg)
        gen = FullReportGenerator(rr, t12, occ, fin, col, ng, config_path=str(CONFIG_PATH))
        gen.generate(str(out_path))

        safe_name     = rr.property_name.replace(" ", "_").replace("/", "-")
        download_name = f"{safe_name}_Monthly_Analysis_Report.docx"

        if IS_LAMBDA and S3_BUCKET:
            return _s3_response(out_path, download_name, tmp_dir)
        else:
            return FileResponse(
                path=str(out_path),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=download_name,
                background=BackgroundTask(shutil.rmtree, str(tmp_dir), True),
            )

    except HTTPException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


def _s3_response(out_path: Path, download_name: str, tmp_dir: Path) -> JSONResponse:
    """Upload docx to S3 and return a presigned download URL (valid 15 min)."""
    import boto3
    s3_key = f"reports/{uuid.uuid4().hex}/{download_name}"
    s3     = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))

    s3.upload_file(
        str(out_path),
        S3_BUCKET,
        s3_key,
        ExtraArgs={
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "ContentDisposition": f'attachment; filename="{download_name}"',
        },
    )
    shutil.rmtree(str(tmp_dir), ignore_errors=True)

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=900,   # 15 minutes
    )
    return JSONResponse({"download_url": url, "expires_in_seconds": 900})


# Lambda handler
handler = Mangum(app, lifespan="off")
