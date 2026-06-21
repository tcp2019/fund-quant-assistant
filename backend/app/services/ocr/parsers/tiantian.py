import re

from app.services.ocr.parsers.base import ParsedHolding


def parse_tiantian_text(text: str) -> list[ParsedHolding]:
    m = re.search(
        r"(\d{6})\s+([\u4e00-\u9fff\w]+).*?"
        r"份额[:：]?\s*([\d.]+).*?"
        r"成本[:：]?\s*([\d.]+).*?"
        r"市值[:：]?\s*([\d.]+).*?"
        r"收益[:：]?\s*([\d.]+).*?"
        r"收益率[:：]?\s*([\d.]+)%",
        text,
        re.DOTALL,
    )
    if m:
        return [
            ParsedHolding(
                fund_code=m.group(1),
                fund_name=m.group(2),
                shares=float(m.group(3)),
                cost_price=float(m.group(4)),
                market_value=float(m.group(5)),
                profit=float(m.group(6)),
                profit_rate=float(m.group(7)) / 100,
                platform="tiantian",
            )
        ]
    return []
