import re
from dataclasses import dataclass

MONEY = r"(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2}"


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


def parse_money(raw: str) -> float:
    cleaned = raw.replace(",", "").replace("|", "").strip()
    if not cleaned:
        return 0.0
    return float(cleaned)


def strip_fund_name(name: str) -> str:
    cleaned = re.sub(
        r"(?:基会|进阶|定投|旺财|细财|理财|稳健|呼财|球财|瑞财|陳财|器财|珅财|深财|理时|王财|萍财|"
        r"进价理|对|挥对|大会|其会|旺会|苏会|玉会|县会|从会|黄会|石他|讲阶|券商|财险|开|)+$",
        "",
        name,
    )
    cleaned = re.sub(r"\d+$", "", cleaned)
    return cleaned.strip()


def extract_fund_code(text: str) -> str | None:
    # Avoid matching the tail of comma-separated amounts like 6,217730.00.
    m = re.search(r"(?<![,\d.])(\d{6})(?![.\d])", text)
    return m.group(1) if m else None


def extract_float(label_patterns: list[str], text: str) -> float | None:
    for pat in label_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", ""))
    return None
