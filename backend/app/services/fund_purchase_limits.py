from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.db.models import FundMetadata

# akshare uses 1e10~1e11 for effectively unlimited daily purchase amounts.
UNLIMITED_DAILY_THRESHOLD = 100_000_000.0
# Only apply purchase-limit protection when daily cap is very low (hard to rebuy).
PURCHASE_LIMIT_PROTECTION_MAX = 500.0

PURCHASE_SUSPENDED_KEYWORDS = ("暂停申购", "封闭期", "停止申购")


def normalize_daily_limit(raw: float | None) -> float | None:
    if raw is None:
        return None
    if raw <= 0:
        return 0.0
    if raw >= UNLIMITED_DAILY_THRESHOLD:
        return None
    return raw


def is_purchase_suspended(status: str) -> bool:
    normalized = (status or "").strip()
    return any(keyword in normalized for keyword in PURCHASE_SUSPENDED_KEYWORDS)


def is_restrictive_daily_limit(limit: float | None) -> bool:
    normalized = normalize_daily_limit(limit)
    return (
        normalized is not None
        and 0 < normalized <= PURCHASE_LIMIT_PROTECTION_MAX
    )


def parse_purchase_record(row: dict[str, Any]) -> dict[str, Any]:
    raw_limit = row.get("daily_purchase_limit")
    return {
        "purchase_status": str(row.get("purchase_status") or ""),
        "purchase_min_amount": row.get("purchase_min_amount"),
        "daily_purchase_limit": normalize_daily_limit(raw_limit),
        "daily_purchase_limit_raw": raw_limit,
    }


def _has_rebalance_add_reason(reasons: list[dict]) -> bool:
    return any(
        reason.get("layer") == "rebalance"
        and reason.get("rule") in {"add", "category_underweight"}
        for reason in reasons
    )


def _has_performance_reduce_reason(reasons: list[dict]) -> bool:
    return any(
        reason.get("layer") == "performance"
        and reason.get("rule")
        in {"excess_return_1y", "max_drawdown_1y", "sharpe_1y"}
        for reason in reasons
    )


def _format_limit_amount(limit: float) -> str:
    if limit == int(limit):
        return f"{int(limit)}"
    return f"{limit:.2f}"


def apply_purchase_limits_to_signal(
    signal: dict[str, Any],
    purchase_info: dict[str, Any] | None,
) -> dict[str, Any]:
    if not signal.get("fund_code"):
        return signal

    updated = deepcopy(signal)
    reasons = list(updated.get("reasons") or [])
    status = (purchase_info or {}).get("purchase_status", "")
    daily_limit = (purchase_info or {}).get("daily_purchase_limit")
    suggested = float(updated.get("suggested_amount") or 0)

    if updated.get("signal_type") in {"reduce", "watch"} and purchase_info:
        if (
            updated.get("signal_type") == "reduce"
            and is_restrictive_daily_limit(daily_limit)
            and not _has_performance_reduce_reason(reasons)
        ):
            updated["signal_type"] = "watch"
            updated["suggested_amount"] = 0.0
            limit_text = _format_limit_amount(daily_limit or 0)
            reasons.append(
                {
                    "layer": "purchase_limit",
                    "rule": "redemption_hard_to_rebuy",
                    "detail": (
                        f"申购状态「{status or '限大额'}」，日累计限购 ¥{limit_text}，"
                        "卖出后难以买回，暂不建议为再平衡减仓"
                    ),
                }
            )
            updated["reasons"] = reasons
        return updated

    actionable_add = updated.get("signal_type") == "add" or (
        suggested > 0 and _has_rebalance_add_reason(reasons)
    )
    if not actionable_add or not purchase_info:
        return updated

    if is_purchase_suspended(status):
        updated["signal_type"] = "watch"
        updated["suggested_amount"] = 0.0
        reasons.append(
            {
                "layer": "purchase_limit",
                "rule": "purchase_suspended",
                "detail": f"当前申购状态为「{status}」，暂无法增配",
            }
        )
        updated["reasons"] = reasons
        return updated

    if not is_restrictive_daily_limit(daily_limit):
        return updated

    limit_value = daily_limit or 0.0
    if suggested <= limit_value:
        return updated

    gap = suggested - limit_value
    updated["signal_type"] = "watch"
    updated["suggested_amount"] = round(limit_value, 2)
    reasons.append(
        {
            "layer": "purchase_limit",
            "rule": "purchase_limit_blocked",
            "detail": (
                f"日累计限购 ¥{_format_limit_amount(limit_value)}（{status or '限大额'}），"
                f"理论缺口 ¥{_format_limit_amount(gap)}，今日最多可买 ¥{_format_limit_amount(limit_value)}"
            ),
        }
    )
    updated["reasons"] = reasons
    return updated


def apply_purchase_limits_to_signals(
    signals: list[dict[str, Any]],
    purchase_info_by_code: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        apply_purchase_limits_to_signal(
            signal,
            purchase_info_by_code.get(signal.get("fund_code", "")),
        )
        for signal in signals
    ]


def purchase_info_from_metadata(meta: FundMetadata | None) -> dict[str, Any] | None:
    if meta is None:
        return None
    return parse_purchase_record(
        {
            "purchase_status": meta.purchase_status,
            "purchase_min_amount": meta.purchase_min_amount,
            "daily_purchase_limit": meta.daily_purchase_limit,
        }
    )
