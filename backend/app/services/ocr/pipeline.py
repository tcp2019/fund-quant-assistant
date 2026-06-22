import os
import threading

from app.services.ocr.parsers.alipay import parse_alipay_text
from app.services.ocr.parsers.base import ParsedHolding
from app.services.ocr.parsers.licaitong import parse_licaitong_text
from app.services.ocr.parsers.tiantian import parse_tiantian_text

# PaddlePaddle is not thread-safe; concurrent init/inference can SIGSEGV on macOS.
_ocr_engine = None
_ocr_lock = threading.Lock()


def _configure_paddle_env() -> None:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")


def _create_paddle_ocr_engine():
    _configure_paddle_env()
    from paddleocr import PaddleOCR

    return PaddleOCR(lang="ch")


def extract_text_from_ocr_result(result) -> str:
    """Support PaddleOCR 3.x OCRResult objects and legacy 2.x list format."""
    lines: list[str] = []
    if not result:
        return ""

    for page in result:
        if page is None:
            continue

        texts = None
        if isinstance(page, dict):
            texts = page.get("rec_texts")
        elif hasattr(page, "get"):
            texts = page.get("rec_texts")
        elif hasattr(page, "rec_texts"):
            texts = page.rec_texts

        if texts:
            lines.extend(str(text) for text in texts if text)
            continue

        if isinstance(page, list):
            if (
                len(page) == 2
                and isinstance(page[1], (tuple, list))
                and page[1]
                and isinstance(page[1][0], str)
            ):
                lines.append(str(page[1][0]))
                continue
            for line in page:
                if (
                    isinstance(line, (list, tuple))
                    and len(line) > 1
                    and isinstance(line[1], (tuple, list))
                    and line[1]
                ):
                    lines.append(str(line[1][0]))

    return "\n".join(lines)


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
    global _ocr_engine
    try:
        with _ocr_lock:
            if _ocr_engine is None:
                _ocr_engine = _create_paddle_ocr_engine()
            # PaddleOCR 3.x: ocr() no longer accepts cls=; results use rec_texts on OCRResult.
            result = _ocr_engine.ocr(image_path)
    except ImportError as exc:
        raise ImportError(
            "PaddleOCR is not installed. Use text upload mode or install OCR extras: "
            "pip install 'fund-quant-assistant[ocr]'"
        ) from exc

    return extract_text_from_ocr_result(result)


def validate_holding(row: ParsedHolding) -> list[str]:
    warnings: list[str] = []
    label = row.fund_code or row.fund_name or "未知基金"
    if row.market_value <= 0:
        warnings.append(f"{label}: 市值无效")
    if not row.fund_code:
        warnings.append(f"{label}: 未识别基金代码，请手动补充")
    if row.shares <= 0:
        warnings.append(f"{label}: 份额未识别，请手动补充或忽略")
    elif row.cost_price > 0:
        implied_nav = row.market_value / row.shares
        if abs(implied_nav - row.cost_price) / row.cost_price > 0.5:
            warnings.append(f"{label}: 市值/份额与成本价偏差较大，请核对")
    return warnings
