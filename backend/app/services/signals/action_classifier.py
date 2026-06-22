"""Classify raw signal records into actionable types (mirrors frontend signalActionType)."""

from __future__ import annotations

PURCHASE_LIMIT_WATCH_RULES = frozenset(
    {"redemption_hard_to_rebuy", "purchase_limit_blocked", "purchase_suspended"}
)
PURCHASE_LIMIT_ADD_BLOCK_RULES = frozenset({"purchase_limit_blocked", "purchase_suspended"})


def _performance_blocked_add(reasons: list[dict]) -> bool:
    return any(reason.get("rule") == "performance_blocked_add" for reason in reasons)


def _consolidation_blocked_add(reasons: list[dict]) -> bool:
    return any(reason.get("rule") == "consolidation_blocked_add" for reason in reasons)


def _add_blocked_by_quality(reasons: list[dict]) -> bool:
    return _performance_blocked_add(reasons) or _consolidation_blocked_add(reasons)


def _protected_by_purchase_limit(reasons: list[dict]) -> bool:
    return any(
        reason.get("layer") == "purchase_limit"
        and reason.get("rule") in PURCHASE_LIMIT_WATCH_RULES
        for reason in reasons
    )


def _rebalance_rules(reasons: list[dict]) -> set[str]:
    return {
        reason.get("rule", "")
        for reason in reasons
        if reason.get("layer") == "rebalance"
    }


def classify_signal_action(
    signal_type: str,
    reasons: list[dict],
    suggested_amount: float,
    score: float,
) -> str:
    if _protected_by_purchase_limit(reasons):
        return "watch"

    if signal_type != "hold":
        if signal_type == "add" and _add_blocked_by_quality(reasons):
            return "watch"
        return signal_type

    rebalance = _rebalance_rules(reasons)
    if (
        suggested_amount > 0
        and score > 0
        and rebalance & {"add", "category_underweight"}
    ):
        if _add_blocked_by_quality(reasons):
            return "watch"
        blocked = any(
            reason.get("layer") == "purchase_limit"
            and reason.get("rule") in PURCHASE_LIMIT_ADD_BLOCK_RULES
            for reason in reasons
        )
        return "watch" if blocked else "add"

    if (
        suggested_amount < 0
        and score < 0
        and rebalance & {"reduce", "category_overweight"}
    ):
        return "reduce"

    return signal_type
