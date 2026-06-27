from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from app.api.deps import get_db
from app.db.models import PortfolioSnapshot, SignalRecord
from app.repositories.portfolio import build_overview, get_latest_snapshot
from app.services.theme_heat import rank_hot_themes

router = APIRouter(prefix="/api/report", tags=["report"])

WEEKLY_TEMPLATE = """# 基金组合周报

> 本报告由量化规则自动生成，仅供个人参考，**不构成投资建议**。

---

## 组合概览

{overview_section}

## 本周信号

{signals_section}

## 大类配置

{allocation_section}

## 热点主题

{themes_section}

## 风险指标

{risk_section}

---

*报告生成时间：{generated_at}*
"""


@router.get("/weekly", response_class=PlainTextResponse)
def weekly_report(
    snapshot_id: int | None = Query(None),
    session: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    if snapshot_id is not None:
        snap = session.get(PortfolioSnapshot, snapshot_id)
    else:
        snap = get_latest_snapshot(session)

    if snap is None:
        return WEEKLY_TEMPLATE.format(
            overview_section="> 暂无数据，请先导入持仓并同步数据。",
            signals_section="> 暂无信号数据。",
            allocation_section="> 暂无配置数据。",
            themes_section="> 暂无热点数据。",
            risk_section="> 暂无风险数据。",
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )

    try:
        overview = build_overview(session)
    except Exception:
        overview = None

    if overview and overview.holdings:
        overview_section = (
            f"- **快照：** #{overview.snapshot_id}\n"
            f"- **总市值：** ¥{overview.total_value:,.0f}\n"
            f"- **总盈亏：** ¥{overview.total_profit:,.0f}"
            f"（{overview.total_profit_rate * 100:.2f}%）\n"
            f"- **持仓基金数：** {len(overview.holdings)} 只\n"
            f"- **净值截至：** {overview.data_as_of_date or '未知'}"
        )
    else:
        overview_section = "> 暂无组合数据。"

    try:
        signal_records = session.exec(
            select(SignalRecord).where(SignalRecord.snapshot_id == snap.id)
        ).all()
        add_count = sum(1 for s in signal_records if s.signal_type == "add")
        reduce_count = sum(1 for s in signal_records if s.signal_type == "reduce")
        watch_count = sum(1 for s in signal_records if s.signal_type == "watch")
        signals_section = (
            f"- **增配信号：** {add_count} 条\n"
            f"- **减仓信号：** {reduce_count} 条\n"
            f"- **观察信号：** {watch_count} 条"
        )
    except Exception:
        signals_section = "> 暂无信号数据。"

    if overview and overview.category_allocation:
        allocation_section = "\n".join(
            f"- {a.label}: {a.weight_pct:.1f}%"
            for a in overview.category_allocation
        )
    else:
        allocation_section = "> 暂无配置数据。"

    try:
        themes = rank_hot_themes(session, limit=5)
        if themes:
            themes_section = "\n".join(
                f"- {t.label}: 近1月中位数 {t.return_1m_median:.2f}%"
                for t in themes[:5]
            )
        else:
            themes_section = "> 暂无热点数据。"
    except Exception:
        themes_section = "> 暂无热点数据。"

    try:
        from app.services.analysis import compute_risk
        risk = compute_risk(session)
        vol = risk.get('volatility')
        sharpe = risk.get('sharpe')
        max_dd = risk.get('max_dd')
        risk_section = (
            f"- **组合波动率：** {vol:.4f}\n" if vol is not None else "- **组合波动率：** N/A\n"
        ) + (
            f"- **夏普比率：** {sharpe:.4f}\n" if sharpe is not None else "- **夏普比率：** N/A\n"
        ) + (
            f"- **最大回撤：** {max_dd:.4f}" if max_dd is not None else "- **最大回撤：** N/A"
        )
    except Exception:
        risk_section = "> 暂无风险数据。"

    return WEEKLY_TEMPLATE.format(
        overview_section=overview_section,
        signals_section=signals_section,
        allocation_section=allocation_section,
        themes_section=themes_section,
        risk_section=risk_section,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
