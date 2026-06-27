import re

_CORRELATION_VALUE = re.compile(r"相关系数\s+([\d.]+)")
_FUND_CODE = re.compile(r"\d{6}")


def enrich_high_correlation_reasons(
    reasons: list[dict],
    fund_code: str,
    name_by_code: dict[str, str | None],
) -> list[dict]:
    """Fill paired fund metadata for legacy reasons_json rows."""
    enriched: list[dict] = []
    for reason in reasons:
        if reason.get("rule") != "high_correlation":
            enriched.append(reason)
            continue

        item = dict(reason)
        detail = item.get("detail") or ""

        if item.get("correlation") is None:
            match = _CORRELATION_VALUE.search(detail)
            if match:
                item["correlation"] = round(float(match.group(1)), 4)

        if not item.get("paired_fund_code"):
            for code in _FUND_CODE.findall(detail):
                if code != fund_code:
                    item["paired_fund_code"] = code
                    break

        paired_code = item.get("paired_fund_code")
        if paired_code and not item.get("paired_fund_name"):
            item["paired_fund_name"] = name_by_code.get(paired_code)

        enriched.append(item)
    return enriched
