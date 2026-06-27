"""AI-powered natural language signal interpretation for retail investors."""

from __future__ import annotations

import logging
import re

import ipaddress
from urllib.parse import urlparse

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


def _normalize_base_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    # ponytail: DeepSeek official base is without /v1; old UI default misled users
    if "api.deepseek.com" in base and base.endswith("/v1"):
        return base[:-3]
    return base


def _completions_url(base_url: str) -> str:
    base = _normalize_base_url(base_url)
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


_BLOCKED_LLM_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


def _llm_base_url_error(base_url: str) -> str | None:
    """Reject loopback/private literal hosts; ponytail: no DNS resolve."""
    parsed = urlparse(base_url if "://" in base_url else f"https://{base_url}")
    if parsed.scheme not in ("http", "https"):
        return "接口地址须为 http 或 https"
    host = (parsed.hostname or "").lower()
    if not host or host in _BLOCKED_LLM_HOSTS:
        return "接口地址不可用"
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return "接口地址不可用"
    except ValueError:
        pass
    return None


def _chat_payload(base_url: str, *, model: str, messages: list, max_tokens: int) -> dict:
    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    if "deepseek" in base_url.lower():
        payload["thinking"] = {"type": "disabled"}
    return payload


def _extract_message_content(choice: dict) -> str | None:
    message = choice.get("message", {}) or {}
    content = (message.get("content") or "").strip()
    if content:
        return content
    # ponytail: V4 thinking mode puts text in reasoning_content when content is empty
    reasoning = (message.get("reasoning_content") or "").strip()
    return reasoning or None


async def _chat_completion(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    max_tokens: int = 256,
) -> str | None:
    if err := _llm_base_url_error(base_url):
        raise ValueError(err)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            _completions_url(base_url),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=_chat_payload(
                base_url, model=model, messages=messages, max_tokens=max_tokens
            ),
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        return _extract_message_content(choices[0])


async def interpret_signal(
    signal_dict: dict,
    *,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
    model_override: str | None = None,
    total_value: float = 0.0,
    weight_pct: float = 0.0,
) -> str | None:
    """Generate a 2-3 sentence Chinese interpretation of a fund signal.

    Returns None if no API key is configured or the LLM call fails.
    """
    api_key = api_key_override or settings.llm_api_key
    if not api_key:
        return None

    base_url = base_url_override or settings.llm_base_url
    model = model_override or settings.llm_model
    messages = _build_messages(signal_dict, total_value, weight_pct)

    try:
        return await _chat_completion(
            messages,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    except Exception:
        logger.warning("LLM interpretation failed", exc_info=True)
        return None


async def test_llm_connection(
    *,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
    model_override: str | None = None,
) -> tuple[bool, str | None]:
    """Ping the LLM API. Returns (ok, error_message)."""
    api_key = api_key_override or settings.llm_api_key
    if not api_key:
        return False, "未配置 API Key"

    base_url = base_url_override or settings.llm_base_url
    model = model_override or settings.llm_model
    if url_err := _llm_base_url_error(base_url):
        return False, url_err
    messages = [{"role": "user", "content": "回复：连接成功"}]

    try:
        content = await _chat_completion(
            messages,
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=16,
        )
        if content:
            return True, None
        return False, "模型返回为空（若使用 DeepSeek V4，请确认接口地址为 https://api.deepseek.com）"
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 401:
            return False, "API Key 无效或已过期"
        if status == 404:
            return False, "接口地址或模型名称不正确"
        return False, f"请求失败（HTTP {status}）"
    except httpx.TimeoutException:
        return False, "连接超时，请检查网络或接口地址"
    except Exception:
        logger.warning("LLM connection test failed", exc_info=True)
        return False, "连接失败，请检查 Key、接口地址与模型"
