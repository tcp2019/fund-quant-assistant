import re
from dataclasses import dataclass


@dataclass
class ParsedHolding:
    fund_code: str
    fund_name: str
    shares: float
    cost_price: float
    market_value: float
    profit: float
    profit_rate: float
    platform: str
    confidence: float = 1.0


def extract_fund_code(text: str) -> str | None:
    m = re.search(r"\b(\d{6})\b", text)
    return m.group(1) if m else None


def extract_float(label_patterns: list[str], text: str) -> float | None:
    for pat in label_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", ""))
    return None
