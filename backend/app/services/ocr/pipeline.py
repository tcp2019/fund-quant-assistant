from app.services.ocr.parsers.alipay import parse_alipay_text
from app.services.ocr.parsers.base import ParsedHolding
from app.services.ocr.parsers.licaitong import parse_licaitong_text
from app.services.ocr.parsers.tiantian import parse_tiantian_text


def parse_ocr_text(text: str, platform_hint: str | None = None) -> list[ParsedHolding]:
    parsers = {
        "alipay": parse_alipay_text,
        "tiantian": parse_tiantian_text,
        "licaitong": parse_licaitong_text,
    }
    if platform_hint and platform_hint in parsers:
        return parsers[platform_hint](text)

    for _name, fn in parsers.items():
        rows = fn(text)
        if rows:
            return rows
    return []


def run_paddle_ocr(image_path: str) -> str:
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise ImportError(
            "PaddleOCR is not installed. Use text upload mode or install OCR extras: "
            "pip install 'fund-quant-assistant[ocr]'"
        ) from exc

    ocr = PaddleOCR(use_angle_cls=True, lang="ch")
    result = ocr.ocr(image_path, cls=True)
    lines: list[str] = []
    for page in result or []:
        if not page:
            continue
        for line in page:
            if line and len(line) > 1 and line[1]:
                lines.append(line[1][0])
    return "\n".join(lines)


def validate_holding(row: ParsedHolding) -> list[str]:
    warnings: list[str] = []
    if row.shares <= 0 or row.market_value <= 0:
        warnings.append(f"{row.fund_code}: 份额或市值无效")
    implied_nav = row.market_value / row.shares if row.shares else 0
    if row.cost_price > 0 and abs(implied_nav - row.cost_price) / row.cost_price > 0.5:
        warnings.append(f"{row.fund_code}: 市值/份额与成本价偏差较大，请核对")
    return warnings
