import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.db.models import Holding, SignalRecord
from app.repositories.portfolio import get_latest_snapshot
from app.schemas.signals import SignalOut, SignalsListOut
from app.services.fund_recommendations import recommend_funds

router = APIRouter(prefix="/api/signals", tags=["signals"])


def _parse_reasons(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


@router.get("", response_model=SignalsListOut)
def list_signals(session: Session = Depends(get_db)):
    snap = get_latest_snapshot(session)
    if snap is None:
        return SignalsListOut(snapshot_id=None, signals=[])

    records = session.exec(
        select(SignalRecord)
        .where(SignalRecord.snapshot_id == snap.id)
        .order_by(SignalRecord.score.desc())
    ).all()

    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    name_by_code = {holding.fund_code: holding.fund_name for holding in holdings}
    held_codes = {holding.fund_code for holding in holdings if holding.fund_code}

    signals: list[SignalOut] = []
    for record in records:
        reasons = _parse_reasons(record.reasons_json)
        category = None
        category_label = None
        if not record.fund_code:
            for reason in reasons:
                category = reason.get("category")
                category_label = reason.get("category_label")
                if category:
                    break

        candidates = []
        if not record.fund_code and record.signal_type == "add" and category:
            candidates = recommend_funds(session, category, held_codes, limit=3)

        signals.append(
            SignalOut(
                id=record.id,
                snapshot_id=record.snapshot_id,
                fund_code=record.fund_code,
                fund_name=name_by_code.get(record.fund_code) if record.fund_code else None,
                category=category,
                category_label=category_label,
                signal_type=record.signal_type,
                score=record.score,
                strength=record.strength,
                reasons=reasons,
                suggested_amount=record.suggested_amount,
                created_at=record.created_at,
                candidates=candidates,
            )
        )

    return SignalsListOut(snapshot_id=snap.id, signals=signals)
