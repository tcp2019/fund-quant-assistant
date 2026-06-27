import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_db
from app.db.models import Holding, SignalRecord
from app.repositories.portfolio import get_latest_snapshot
from app.schemas.signals import InterpretOut, InterpretRequest, SignalOut, SignalsListOut
from app.services.fund_recommendations import recommend_funds
from app.services.llm_interpreter import interpret_signal
from app.services.signals.reason_enrichment import enrich_high_correlation_reasons

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
        if record.fund_code:
            reasons = enrich_high_correlation_reasons(
                reasons, record.fund_code, name_by_code
            )
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
                interpretation=record.interpretation,
                created_at=record.created_at,
                candidates=candidates,
            )
        )

    return SignalsListOut(snapshot_id=snap.id, signals=signals)


@router.post("/{signal_id}/interpret", response_model=InterpretOut)
async def interpret_signal_endpoint(
    signal_id: int,
    body: InterpretRequest = InterpretRequest(),
    session: Session = Depends(get_db),
):
    record = session.get(SignalRecord, signal_id)
    if not record:
        raise HTTPException(status_code=404, detail="Signal not found")

    if record.interpretation:
        return InterpretOut(
            signal_id=signal_id,
            interpretation=record.interpretation,
            cached=True,
        )

    snap = get_latest_snapshot(session)
    total_value = 0.0
    weight_pct = 0.0
    if snap:
        holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
        total_value = sum(h.market_value for h in holdings)
        if total_value > 0 and record.fund_code:
            fund_mv = sum(h.market_value for h in holdings if h.fund_code == record.fund_code)
            weight_pct = fund_mv / total_value * 100

    reasons = _parse_reasons(record.reasons_json)
    name_by_code: dict[str, str] = {}
    if snap:
        holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
        name_by_code = {h.fund_code: h.fund_name for h in holdings}
    if record.fund_code:
        reasons = enrich_high_correlation_reasons(reasons, record.fund_code, name_by_code)

    signal_dict = {
        "signal_type": record.signal_type,
        "fund_code": record.fund_code,
        "fund_name": name_by_code.get(record.fund_code) if record.fund_code else None,
        "score": record.score,
        "strength": record.strength,
        "suggested_amount": record.suggested_amount,
        "reasons": reasons,
    }

    interpretation = await interpret_signal(
        signal_dict,
        api_key_override=body.api_key,
        total_value=total_value,
        weight_pct=weight_pct,
    )

    if interpretation:
        record.interpretation = interpretation
        session.add(record)
        session.commit()

    return InterpretOut(
        signal_id=signal_id,
        interpretation=interpretation,
        cached=False,
    )
