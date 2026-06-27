"""Resolve standard fund codes from fund names using the local catalog."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlmodel import Session, select

from app.db.models import FundCatalog
from app.services.fund_catalog import ensure_catalog, get_catalog_entry
from app.services.ocr.parsers.base import ParsedHolding

_MIN_MATCH_SCORE = 0.65
_GOOD_MATCH_SCORE = 0.72


def _norm_name(name: str) -> str:
    cleaned = re.sub(r"\s+", "", name.strip())
    for char in "()（）-·":
        cleaned = cleaned.replace(char, "")
    return cleaned


def _share_suffix(name: str) -> str | None:
    match = re.search(r"([A-E])$", _norm_name(name))
    return match.group(1) if match else None


def _name_core(name: str) -> str:
    cleaned = _norm_name(name)
    cleaned = re.sub(
        r"(混合|股票|债券|指数|发起式|发起|联接|链接|ETF|QDII|FOF|LOF|[A-E])",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned[:8] if len(cleaned) >= 8 else cleaned


def score_fund_name(imported: str, official: str) -> float:
    ratio = SequenceMatcher(None, _norm_name(imported), _norm_name(official)).ratio()
    suffix = _share_suffix(imported)
    if suffix and suffix in _norm_name(official):
        ratio += 0.05
    return ratio


def best_catalog_match(fund_name: str, catalog: list[FundCatalog]) -> tuple[FundCatalog | None, float]:
    core = _name_core(fund_name)
    if len(core) < 3:
        return None, 0.0

    needle = core[:6]
    candidates = [row for row in catalog if needle in _norm_name(row.name)]
    if not candidates:
        candidates = catalog

    best: FundCatalog | None = None
    best_score = 0.0
    for row in candidates:
        score = score_fund_name(fund_name, row.name)
        if score > best_score:
            best = row
            best_score = score

    if best_score < _MIN_MATCH_SCORE:
        return None, best_score
    return best, best_score


def imported_code_matches_name(session: Session, code: str, fund_name: str) -> bool:
    if not code or not fund_name:
        return False
    entry = get_catalog_entry(session, code.zfill(6))
    if entry is None:
        return False
    if score_fund_name(fund_name, entry.name) < _GOOD_MATCH_SCORE:
        return False
    imported_suffix = _share_suffix(fund_name)
    official_suffix = _share_suffix(entry.name)
    if imported_suffix and official_suffix and imported_suffix != official_suffix:
        return False
    return True


def resolve_fund_code_by_name(session: Session, fund_name: str) -> tuple[str | None, str | None, float]:
    ensure_catalog(session)
    catalog = list(session.exec(select(FundCatalog)).all())
    match, score = best_catalog_match(fund_name, catalog)
    if match is None:
        return None, None, score
    return match.code, match.name, score


def resolve_holdings_fund_codes(session: Session, holdings: list[ParsedHolding]) -> list[str]:
    """Replace unreliable imported codes using fund names. Returns global warnings."""
    if not holdings:
        return []

    ensure_catalog(session)
    catalog = list(session.exec(select(FundCatalog)).all())
    warnings: list[str] = []

    for holding in holdings:
        if not holding.fund_name:
            continue

        if holding.fund_code and imported_code_matches_name(
            session, holding.fund_code, holding.fund_name
        ):
            holding.fund_code = holding.fund_code.zfill(6)
            continue

        match, score = best_catalog_match(holding.fund_name, catalog)
        if match is None:
            warnings.append(f"{holding.fund_name}: 未能按名称匹配标准基金代码，请手动补充")
            continue

        old_code = holding.fund_code or "-"
        if old_code != match.code:
            holding.fund_code = match.code
            if old_code != "-":
                warnings.append(
                    f"{holding.fund_name}: 代码 {old_code} → {match.code}（支付宝代码不可靠，已按名称匹配）"
                )
            else:
                warnings.append(f"{holding.fund_name}: 已匹配代码 {match.code}")

        if score < _GOOD_MATCH_SCORE:
            warnings.append(
                f"{holding.fund_name}: 匹配置信度偏低 ({score:.0%})，请核对代码 {match.code}"
            )

    return warnings


def fix_snapshot_holdings_codes(session: Session, snapshot_id: int) -> dict:
    from app.db.models import Holding

    holdings = list(
        session.exec(select(Holding).where(Holding.snapshot_id == snapshot_id)).all()
    )
    if not holdings:
        return {"updated": 0, "warnings": []}

    parsed = [
        ParsedHolding(
            fund_code=holding.fund_code,
            fund_name=holding.fund_name,
            shares=holding.shares,
            cost_price=holding.cost_price,
            market_value=holding.market_value,
            profit=holding.profit,
            profit_rate=holding.profit_rate,
            platform=holding.platform,
        )
        for holding in holdings
    ]
    warnings = resolve_holdings_fund_codes(session, parsed)
    for holding, resolved in zip(holdings, parsed, strict=True):
        holding.fund_code = resolved.fund_code
        session.add(holding)
    session.commit()
    return {"updated": len(holdings), "warnings": warnings}
