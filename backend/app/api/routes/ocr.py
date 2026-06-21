import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import get_db
from app.db.models import OcrJob
from app.repositories import portfolio as repo
from app.schemas.ocr import (
    OcrConfirmRequest,
    OcrConfirmResponse,
    OcrUploadRequest,
    OcrUploadResponse,
    ParsedHoldingOut,
)
from app.schemas.portfolio import SnapshotCreate
from app.services.ocr.pipeline import parse_ocr_text, validate_holding

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


def _to_holding_out(row) -> ParsedHoldingOut:
    return ParsedHoldingOut(
        fund_code=row.fund_code,
        fund_name=row.fund_name,
        shares=row.shares,
        cost_price=row.cost_price,
        market_value=row.market_value,
        profit=row.profit,
        profit_rate=row.profit_rate,
        platform=row.platform,
        confidence=row.confidence,
    )


@router.post("/upload", response_model=OcrUploadResponse)
def upload(data: OcrUploadRequest, session: Session = Depends(get_db)):
    rows = parse_ocr_text(data.text, platform_hint=data.platform)
    warnings: list[str] = []
    holdings = []
    for row in rows:
        warnings.extend(validate_holding(row))
        holdings.append(_to_holding_out(row))

    job = OcrJob(
        status="parsed" if rows else "failed",
        parsed_json=json.dumps([h.model_dump() for h in holdings]),
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    return OcrUploadResponse(job_id=job.id, holdings=holdings, warnings=warnings)


@router.post("/{job_id}/confirm", response_model=OcrConfirmResponse, status_code=201)
def confirm(job_id: int, data: OcrConfirmRequest, session: Session = Depends(get_db)):
    job = session.get(OcrJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="OCR job not found")
    if job.status == "confirmed":
        raise HTTPException(status_code=400, detail="OCR job already confirmed")

    snap = repo.create_snapshot(
        session,
        SnapshotCreate(holdings=data.holdings, source="ocr", note=f"ocr_job:{job_id}"),
    )

    job.status = "confirmed"
    job.confirmed_at = datetime.utcnow()
    session.add(job)
    session.commit()

    return OcrConfirmResponse(snapshot_id=snap.id)
