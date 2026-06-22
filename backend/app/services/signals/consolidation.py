from __future__ import annotations

from collections import defaultdict

from app.services.signals.rebalance import CATEGORY_LABELS


def _count_high_correlation_pairs(corr_matrix: dict | None, correlation_max: float) -> int:
    if corr_matrix is None:
        return 0
    labels = corr_matrix.get("labels") or []
    matrix = corr_matrix.get("matrix") or []
    count = 0
    n = len(labels)
    for i in range(n):
        for j in range(i + 1, n):
            if float(matrix[i][j]) > correlation_max:
                count += 1
    return count


def compute_consolidation_signals(
    fund_categories: dict[str, str],
    *,
    max_funds_per_category: int,
    corr_matrix: dict | None = None,
    correlation_max: float = 0.85,
) -> list[dict]:
    by_category: dict[str, list[str]] = defaultdict(list)
    for code, category in fund_categories.items():
        by_category[category].append(code)

    high_corr_pairs = _count_high_correlation_pairs(corr_matrix, correlation_max)
    signals: list[dict] = []

    for category in sorted(by_category):
        codes = by_category[category]
        if len(codes) <= max_funds_per_category:
            continue
        label = CATEGORY_LABELS.get(category, category)
        detail = (
            f"{label}持仓 {len(codes)} 只，超过建议上限 {max_funds_per_category} 只，"
            f"建议合并为核心持仓"
        )
        if high_corr_pairs > 0:
            detail += f"；组合内另有 {high_corr_pairs} 对高相关基金"
        signals.append(
            {
                "category": category,
                "signal_type": "watch",
                "fund_count": len(codes),
                "detail": detail,
            }
        )

    return signals
