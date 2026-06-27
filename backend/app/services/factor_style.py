"""Style factor classification for Chinese mutual funds."""

SIZE_LARGE_KEYWORDS = {"大盘", "蓝筹", "沪深300", "上证50", "中证100", "A50", "龙头"}
SIZE_SMALL_KEYWORDS = {"中小盘", "创业板", "科创板", "中证500", "中证1000", "国证2000", "小盘"}

STYLE_VALUE_KEYWORDS = {"价值", "红利", "低波", "高股息", "股息"}
STYLE_GROWTH_KEYWORDS = {"成长", "创新", "科技", "新兴", "未来", "新经济"}


def classify_fund_style(name: str, fund_type: str = "stock") -> dict:
    if fund_type not in ("stock", "mixed", "qdii", ""):
        return {"size": "balanced", "style": "balanced"}

    size = "balanced"
    for kw in SIZE_LARGE_KEYWORDS:
        if kw in name:
            size = "large_cap"
            break
    if size == "balanced":
        for kw in SIZE_SMALL_KEYWORDS:
            if kw in name:
                size = "small_cap"
                break

    style = "balanced"
    for kw in STYLE_VALUE_KEYWORDS:
        if kw in name:
            style = "value"
            break
    if style == "balanced":
        for kw in STYLE_GROWTH_KEYWORDS:
            if kw in name:
                style = "growth"
                break

    return {"size": size, "style": style}


def compute_portfolio_style(session) -> dict:
    from collections import Counter
    from app.db.models import Holding
    from app.repositories.portfolio import get_latest_snapshot
    from sqlmodel import select

    snap = get_latest_snapshot(session)
    if not snap:
        return {"size_exposure": {}, "style_exposure": {}, "snapshot_id": None}

    holdings = session.exec(
        select(Holding).where(Holding.snapshot_id == snap.id)
    ).all()

    if not holdings:
        return {"size_exposure": {}, "style_exposure": {}, "snapshot_id": snap.id}

    total_value = sum(h.market_value for h in holdings)
    size_weight = Counter()
    style_weight = Counter()

    for h in holdings:
        s = classify_fund_style(h.fund_name, "stock")
        w = h.market_value / total_value * 100 if total_value else 0
        size_weight[s["size"]] += w
        style_weight[s["style"]] += w

    return {
        "size_exposure": {k: round(v, 2) for k, v in size_weight.items()},
        "style_exposure": {k: round(v, 2) for k, v in style_weight.items()},
        "snapshot_id": snap.id,
    }
