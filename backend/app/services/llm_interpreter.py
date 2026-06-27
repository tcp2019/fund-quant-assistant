"""AI-powered natural language signal interpretation for retail investors."""

from __future__ import annotations

import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是面向个人投资者的基金组合助手。用通俗易懂的中文解释量化信号的含义，"
    "帮助零售投资者理解应该做什么以及为什么。只用2-3句话，不要给出独立的投资建议，"
    "不要使用 Markdown 格式。"
)

SIGNAL_TYPE_NAME: dict[str, str] = {
    "reduce": "减仓",
    "add": "增配",
    "hold": "持有",
    "watch": "观察",
}

REASON_RULE_NAME: dict[str, str] = {
    "add": "增配",
    "reduce": "减配",
    "category_underweight": "大类低配",
    "category_overweight": "大类超配",
    "single_fund_concentration": "集中度",
    "high_correlation": "高相关",
    "no_action": "无需调整",
    "excess_return_1y": "超额收益",
    "sharpe_1y": "夏普比率",
    "max_drawdown_1y": "最大回撤",
    "purchase_limit_blocked": "限购受阻",
    "purchase_suspended": "暂停申购",
    "redemption_hard_to_rebuy": "卖出难买回",
    "performance_blocked_add": "业绩过滤",
    "performance_prioritized_reduce": "减配优先",
    "category_overcrowded": "持仓过多",
    "below_min_trade": "低于最小交易额",
    "consolidation_blocked_add": "类内暂停增配",
}


def _format_amount(value: float) -> str:
    if abs(value) >= 10000:
        return f"¥{abs(value) / 10000:.1f}万"
    return f"¥{abs(value):.0f}"


def _build_user_message(
    signal_dict: dict,
    total_value: float,
    weight_pct: float,
) -> str:
    signal_type = signal_dict.get("signal_type", "hold")
    fund_name = signal_dict.get("fund_name") or signal_dict.get("category_label") or "-"
    fund_code = signal_dict.get("fund_code") or ""
    score = signal_dict.get("score", 0.0)
    strength = signal_dict.get("strength", 0)
    suggested_amount = signal_dict.get("suggested_amount", 0.0)
    reasons: list[dict] = signal_dict.get("reasons", [])

    lines: list[str] = []
    if signal_type == "add":
        lines.append("信号类型：增配")
    elif signal_type == "reduce":
        lines.append("信号类型：减仓")
    elif signal_type == "watch":
        lines.append("信号类型：持续观察")
    else:
        lines.append("信号类型：继续持有")

    if fund_code:
        lines.append(f"基金名称：{fund_name}（{fund_code}）")
    else:
        lines.append(f"配置大类：{fund_name}")

    score_str = f"+{score:.1f}" if score > 0 else f"{score:.1f}"
    lines.append(f"综合评分：{score_str} / 强度：{strength}/5")

    if suggested_amount != 0:
        direction = "增配" if suggested_amount > 0 else "减仓"
        lines.append(f"建议{direction}：{_format_amount(suggested_amount)}")

    if weight_pct > 0:
        lines.append(f"当前权重：{weight_pct:.0f}%")
    if total_value > 0:
        lines.append(f"组合总市值：{_format_amount(total_value)}")

    if reasons:
        lines.append("")
        lines.append("触发原因：")
        for reason in reasons:
            layer = reason.get("layer", "")
            rule = reason.get("rule", "")
            detail = reason.get("detail", "")
            rule_label = REASON_RULE_NAME.get(rule, rule)

            extra = ""
            if rule == "high_correlation":
                paired_name = reason.get("paired_fund_name")
                correlation = reason.get("correlation")
                if paired_name and correlation is not None:
                    extra = f"（{paired_name}，相关系数{correlation:.2f}）"
            lines.append(f"- [{rule_label}] {detail}{extra}")

    lines.append("")
    lines.append(
        "请用2-3句通俗的中文解释这个信号对个人投资者的含义，"
        "说明为什么触发此信号以及建议如何应对。"
    )
    return "\n".join(lines)


def _build_messages(
    signal_dict: dict,
    total_value: float = 0.0,
    weight_pct: float = 0.0,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(signal_dict, total_value, weight_pct)},
    ]


async def interpret_signal(
    signal_dict: dict,
    *,
    api_key_override: str | None = None,
    total_value: float = 0.0,
    weight_pct: float = 0.0,
) -> str | None:
    """Generate a 2-3 sentence Chinese interpretation of a fund signal.

    Returns None if no API key is configured or the LLM call fails.
    """
    api_key = api_key_override or settings.llm_api_key
    if not api_key:
        return None

    messages = _build_messages(signal_dict, total_value, weight_pct)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": messages,
                    "max_tokens": 256,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return None
            content = choices[0].get("message", {}).get("content", "")
            return content.strip() if content else None
    except Exception:
        logger.warning("LLM interpretation failed", exc_info=True)
        return None
