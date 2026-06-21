import re

from app.services.ocr.parsers.base import ParsedHolding, extract_float, extract_fund_code


def parse_alipay_text(text: str) -> list[ParsedHolding]:
    blocks = re.split(r"\n\s*\n", text.strip())
    results: list[ParsedHolding] = []
    for block in blocks:
        code = extract_fund_code(block)
        if not code:
            continue
        name_match = re.search(r"([\u4e00-\u9fffA-Za-z0-9]+)\s+" + code, block)
        name = name_match.group(1) if name_match else ""
        shares = extract_float([r"持有份额\s*([\d.]+)", r"份额\s*([\d.]+)"], block) or 0.0
        cost = extract_float([r"成本价\s*([\d.]+)"], block) or 0.0
        mv = extract_float([r"持有市值\s*([\d.]+)", r"市值\s*([\d.]+)"], block) or 0.0
        profit = extract_float([r"持有收益\s*\+?([\d.]+)"], block) or 0.0
        rate = extract_float([r"收益率\s*\+?([\d.]+)%"], block) or 0.0
        results.append(
            ParsedHolding(
                fund_code=code,
                fund_name=name,
                shares=shares,
                cost_price=cost,
                market_value=mv,
                profit=profit,
                profit_rate=rate / 100,
                platform="alipay",
            )
        )
    return results
