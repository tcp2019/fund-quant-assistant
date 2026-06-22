from __future__ import annotations

import json

from sqlmodel import Session, select

from app.db.models import Holding, SignalRecord
from app.repositories.portfolio import build_overview, get_latest_snapshot
from app.schemas.funds import FundCandidateOut
from app.schemas.opportunities import ActionItemOut, HotThemeOut, OpportunitiesOut
from app.services.fund_recommendations import recommend_funds, recommend_funds_by_theme
from app.services.signals.action_classifier import classify_signal_action
from app.services.theme_heat import THEME_TO_CATEGORY, rank_hot_themes

REASON_RULE_LABELS: dict[str, str] = {
    "add": "增配",
    "reduce": "减配",
    "category_underweight": "大类低配",
    "category_overweight": "大类超配",
    "single_fund_concentration": "集中度",
    "performance_blocked_add": "业绩过滤",
    "purchase_limit_blocked": "限购受阻",
    "purchase_suspended": "暂停申购",
    "redemption_hard_to_rebuy": "卖出难买回",
}


def _parse_reasons(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def summarize_reason(reasons: list[dict], max_length: int = 80) -> str:
    if not reasons:
        return "—"
    first = reasons[0]
    rule = first.get("rule", "")
    label = REASON_RULE_LABELS.get(rule, rule)
    detail = first.get("detail", "")
    text = f"{label} · {detail}" if detail else label
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}…"


def _extract_category(reasons: list[dict]) -> tuple[str | None, str | None]:
    for reason in reasons:
        category = reason.get("category")
        if category:
            return category, reason.get("category_label")
    return None, None


def _underweight_categories(records: list[SignalRecord]) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in records:
        reasons = _parse_reasons(record.reasons_json)
        for reason in reasons:
            if reason.get("rule") == "category_underweight" and reason.get("category"):
                result[reason["category"]] = reason.get("category_label") or reason["category"]
    return result


def build_opportunities(
    session: Session,
    *,
    sell_limit: int = 5,
    buy_limit: int = 5,
    explore_limit: int = 5,
    theme_limit: int = 5,
) -> OpportunitiesOut:
    snap = get_latest_snapshot(session)
    if snap is None:
        return OpportunitiesOut(
            snapshot_id=None,
            sell_actions=[],
            buy_actions=[],
            explore_actions=[],
            hot_themes=[],
        )

    records = session.exec(
        select(SignalRecord)
        .where(SignalRecord.snapshot_id == snap.id)
        .order_by(SignalRecord.score.desc())
    ).all()
    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    name_by_code = {h.fund_code: h.fund_name for h in holdings}
    held_codes = {h.fund_code for h in holdings if h.fund_code}
    underweight = _underweight_categories(records)

    overview = build_overview(session)
    theme_weight = {
        item.theme: item.weight_pct for item in (overview.theme_allocation or [])
    }

    sell_actions: list[ActionItemOut] = []
    buy_actions: list[ActionItemOut] = []
    explore_actions: list[ActionItemOut] = []

    for record in records:
        reasons = _parse_reasons(record.reasons_json)
        action_type = classify_signal_action(
            record.signal_type, reasons, record.suggested_amount, record.score
        )
        category, category_label = _extract_category(reasons)

        if action_type == "reduce" and record.suggested_amount < 0 and record.fund_code:
            sell_actions.append(
                ActionItemOut(
                    action="sell",
                    fund_code=record.fund_code,
                    fund_name=name_by_code.get(record.fund_code),
                    category=category,
                    category_label=category_label,
                    suggested_amount=record.suggested_amount,
                    score=record.score,
                    strength=record.strength,
                    reason_summary=summarize_reason(reasons),
                    signal_id=record.id,
                )
            )
        elif action_type == "add" and record.suggested_amount > 0 and record.fund_code:
            buy_actions.append(
                ActionItemOut(
                    action="add_holding",
                    fund_code=record.fund_code,
                    fund_name=name_by_code.get(record.fund_code),
                    category=category,
                    category_label=category_label,
                    suggested_amount=record.suggested_amount,
                    score=record.score,
                    strength=record.strength,
                    reason_summary=summarize_reason(reasons),
                    signal_id=record.id,
                )
            )
        elif (
            action_type == "add"
            and record.suggested_amount > 0
            and not record.fund_code
            and category
        ):
            candidates = recommend_funds(session, category, held_codes, limit=3)
            explore_actions.append(
                ActionItemOut(
                    action="explore",
                    fund_code="",
                    fund_name=None,
                    category=category,
                    category_label=category_label,
                    suggested_amount=record.suggested_amount,
                    score=record.score,
                    strength=record.strength,
                    reason_summary=summarize_reason(reasons),
                    signal_id=record.id,
                    candidates=candidates,
                )
            )

    sell_actions.sort(key=lambda item: (abs(item.suggested_amount), abs(item.score)), reverse=True)
    buy_actions.sort(key=lambda item: item.suggested_amount, reverse=True)
    explore_actions.sort(key=lambda item: abs(item.suggested_amount), reverse=True)

    hot_rows = rank_hot_themes(session, limit=theme_limit)
    hot_themes: list[HotThemeOut] = []
    for row in hot_rows:
        mapped_category = THEME_TO_CATEGORY.get(row.theme, "stock")
        aligned = mapped_category in underweight
        candidates = recommend_funds_by_theme(session, row.theme, held_codes, limit=3)
        hot_themes.append(
            HotThemeOut(
                theme=row.theme,
                label=row.label,
                heat_score=row.heat_score,
                return_1m_median=row.return_1m_median,
                portfolio_weight_pct=theme_weight.get(row.theme, 0.0),
                aligned_gap=aligned,
                aligned_category_label=underweight.get(mapped_category) if aligned else None,
                candidates=candidates,
            )
        )

    return OpportunitiesOut(
        snapshot_id=snap.id,
        data_as_of_date=overview.data_as_of_date,
        sell_actions=sell_actions[:sell_limit],
        buy_actions=buy_actions[:buy_limit],
        explore_actions=explore_actions[:explore_limit],
        hot_themes=hot_themes,
    )
