import asyncio
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.api.deps import get_db
from app.config import settings
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
from app.services.fund_code_resolver import resolve_holdings_fund_codes
from app.services.ocr.pipeline import parse_ocr_text, run_paddle_ocr, validate_holding

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


def _to_holding_out(row, row_warnings: list[str] | None = None) -> ParsedHoldingOut:
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
        warnings=row_warnings or [],
    )


def _build_upload_response(
    text: str, platform_hint: str | None, session: Session
) -> OcrUploadResponse:
    rows = parse_ocr_text(text, platform_hint=platform_hint)
    code_warnings = resolve_holdings_fund_codes(session, rows)
    warnings: list[str] = list(code_warnings)
    holdings = []
    for row in rows:
        row_warnings = validate_holding(row)
        warnings.extend(row_warnings)
        holdings.append(_to_holding_out(row, row_warnings))

    job = OcrJob(
        status="parsed" if rows else "failed",
        parsed_json=json.dumps([h.model_dump() for h in holdings]),
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    return OcrUploadResponse(job_id=job.id, holdings=holdings, warnings=warnings)


@router.post("/upload", response_model=OcrUploadResponse)
async def upload(request: Request, session: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload_file = form.get("file")
        if upload_file is None or not hasattr(upload_file, "read"):
            raise HTTPException(status_code=422, detail="file is required for multipart upload")

        platform = form.get("platform")
        platform_hint = platform if isinstance(platform, str) and platform else None

        upload_path = Path(settings.upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)
        suffix = Path(getattr(upload_file, "filename", None) or "upload.png").suffix or ".png"
        dest = upload_path / f"{uuid4()}{suffix}"
        dest.write_bytes(await upload_file.read())

        try:
            # Paddle inference is CPU-heavy and must not run on the asyncio event loop.
            text = await asyncio.to_thread(run_paddle_ocr, str(dest))
        except ImportError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc

        return _build_upload_response(text, platform_hint, session)

    data = OcrUploadRequest.model_validate(await request.json())
    return _build_upload_response(data.text, data.platform, session)


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
