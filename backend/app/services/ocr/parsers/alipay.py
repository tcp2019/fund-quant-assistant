import re

from app.services.ocr.parsers.base import (
    MONEY,
    ParsedHolding,
    extract_float,
    extract_fund_code,
    parse_money,
    strip_fund_name,
)

_FUND_KIND = (
    r"(?:混合|债券|ETF|指数|股票|联接|精选|主题|成长|配置|量化|产业|科技|通信|能源|光伏|电池|芯片|半导体|机器人|红利|"
    r"原油|油气|传媒|工业|制造|升级|信息|创新|全球|海外|纳斯达克|创业板|科创板|智能|资源|人工智能|低碳|金属|"
    r"算力|添益|智远|优选|增强|研究|数字经济|有色|东方红|新能源|恒丰|低波动|碳|兴选|均衡|高端|装备|"
    r"5G|A500|材料|设备|恒生|港股|制造|信息|低碳|有色金属|红利|电池|芯片|资源|科技|全球|"
    r"研究|优选|保险|保单|設票|黄金)"
)
_FUND_NAME = (
    rf"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z()（）\-·0-9]*{_FUND_KIND}[\u4e00-\u9fffA-Za-z()（）\-·0-9]*"
)
_SKIP_NAME_PARTS = ("余额宝", "保险", "保单", "账户安全", "法律文件", "蚂蚁财富")
_FIELD_SEP = r"\|?"
_WEIGHT_RE = re.compile(
    rf"(?P<name>{_FUND_NAME})"
    r"(?P<tags>[\u4e00-\u9fffA-Za-z¥，,、\s》]*)"
    rf"(?P<mv>[+-]?{MONEY}){_FIELD_SEP}"
    rf"(?P<yesterday>[+-]?{MONEY}){_FIELD_SEP}"
    rf"(?P<holding>[+-]?{MONEY}){_FIELD_SEP}"
    rf"(?P<cumulative>[+-]?{MONEY}){_FIELD_SEP}"
    r"(?:占比|占地|\d比)(?P<weight>[\d.]+%?)"
    r"(?:[^\d%+-]*?)?(?P<rate>[+-]?[\d.]+%?)",
    re.IGNORECASE,
)


def _normalize_list_text(text: str) -> str:
    normalized = text.replace("\n", "").strip()
    normalized = re.sub(
        r"(?<![,\d])(\d{1,2})\.(\d{3})\.(\d{2})(?=\.\d{2}|[+-]|占比|占地|\d比|$)",
        r"\1,\2.\3",
        normalized,
    )
    normalized = re.sub(
        rf"([+-]?{MONEY})(\.\d{{2}})(?=[+-]|占比|占地|\d比)",
        r"\1|\2",
        normalized,
    )
    normalized = re.sub(r"(\d,\d{3})(\d{3}\.\d{2})", r"\1.\2|", normalized)
    normalized = re.sub(
        r"占比(\d+)\.(\d{2})(\d+)\.(\d{2})%",
        r"占比\1.\2%+\3.\4%",
        normalized,
    )
    normalized = re.sub(r"(\d)比([\d.]+%)", r"占比\2", normalized)
    normalized = re.sub(
        rf"(?<=[\d%|])(?={_FUND_NAME})",
        "\n",
        normalized,
    )
    return normalized


def _parse_rate(raw: str) -> float:
    cleaned = raw.strip().replace(",", "").replace("%", "")
    if not cleaned or cleaned in {"+", "-"}:
        return 0.0
    value = float(cleaned)
    if abs(value) >= 100 and "." not in raw.replace("%", ""):
        value /= 100
    return value / 100


def _parse_weight(raw: str) -> float:
    cleaned = raw.strip().replace(",", "").replace("%", "")
    if not cleaned:
        return 0.0
    value = float(cleaned)
    if value >= 100 and "." not in raw.replace("%", ""):
        value /= 100
    return value / 100


def _parse_alipay_detail_text(text: str) -> list[ParsedHolding]:
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


_MERGED_LINE_RE = re.compile(
    r"^\s*(?:\d+[\s.:：、]*)?"
    rf"(?P<name>{_FUND_NAME})\s*"
    r"\(?(?P<code>\d{6})\)?"
    r"\s*\|?\s*"
    rf"(?P<mv>[+-]?{MONEY})"
    r"\s*\|?\s*"
    r"(?P<rate>[+-]?[\d.]+%?)"
    r"(?:\s+.*)?$"
)


def _parse_alipay_tab_export(text: str) -> list[ParsedHolding]:
    """Parse tab-separated exports: 序号 | 名称 | 代码 | 市值 | 收益率 | (可选赛道)."""
    if "\t" not in text:
        return []

    results: list[ParsedHolding] = []
    seen_codes: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(
            ("=", "-", "【", "序号", "基金完整", "备注", "全部", "基金持仓")
        ):
            continue
        if any(part in line for part in _SKIP_NAME_PARTS):
            continue

        parts = [part.strip() for part in line.split("\t")]
        if len(parts) < 5:
            continue

        code_idx = next(
            (index for index, part in enumerate(parts) if re.fullmatch(r"\d{6}", part)),
            None,
        )
        if code_idx is None or code_idx < 1 or code_idx + 2 >= len(parts):
            continue

        code = parts[code_idx]
        if code in seen_codes:
            continue

        name = strip_fund_name(parts[code_idx - 1])
        if not name or any(part in name for part in _SKIP_NAME_PARTS):
            continue

        market_value = parse_money(parts[code_idx + 1])
        if market_value <= 0:
            continue

        profit_rate = _parse_rate(parts[code_idx + 2])
        profit = round(market_value * profit_rate / (1 + profit_rate), 2) if profit_rate else 0.0
        implied_cost = round(market_value - profit, 2) if profit else 0.0

        results.append(
            ParsedHolding(
                fund_code=code,
                fund_name=name,
                shares=0.0,
                cost_price=implied_cost if implied_cost > 0 else 0.0,
                market_value=market_value,
                profit=profit,
                profit_rate=profit_rate,
                platform="alipay",
                confidence=0.92,
            )
        )
        seen_codes.add(code)

    return results


def _parse_alipay_merged_text(text: str) -> list[ParsedHolding]:
    """Parse exported holdings like: 基金名称 012422 42036.78 +90.70%"""
    results: list[ParsedHolding] = []
    seen_codes: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("=", "-", "【", "序号", "基金", "备注", "全部", "基金持仓")):
            continue
        if any(part in line for part in _SKIP_NAME_PARTS):
            continue

        match = _MERGED_LINE_RE.match(line)
        if not match:
            continue

        code = match.group("code")
        if code in seen_codes:
            continue

        name = strip_fund_name(match.group("name"))
        if not name or any(part in name for part in _SKIP_NAME_PARTS):
            continue

        market_value = parse_money(match.group("mv"))
        if market_value <= 0:
            continue

        profit_rate = _parse_rate(match.group("rate"))
        profit = round(market_value * profit_rate / (1 + profit_rate), 2) if profit_rate else 0.0
        implied_cost = round(market_value - profit, 2) if profit else 0.0

        results.append(
            ParsedHolding(
                fund_code=code,
                fund_name=name,
                shares=0.0,
                cost_price=implied_cost if implied_cost > 0 else 0.0,
                market_value=market_value,
                profit=profit,
                profit_rate=profit_rate,
                platform="alipay",
                confidence=0.9,
            )
        )
        seen_codes.add(code)

    return results


def _parse_alipay_list_text(text: str) -> list[ParsedHolding]:
    normalized = _normalize_list_text(text)
    results: list[ParsedHolding] = []
    seen_names: set[str] = set()

    for block in normalized.split("\n"):
        block = block.strip()
        if not block or any(part in block for part in _SKIP_NAME_PARTS):
            continue

        match = _WEIGHT_RE.search(block)
        if not match:
            continue

        name = strip_fund_name(match.group("name"))
        if not name or name in seen_names:
            continue
        if any(part in name for part in _SKIP_NAME_PARTS):
            continue

        market_value = parse_money(match.group("mv"))
        profit = parse_money(match.group("holding"))
        profit_rate = _parse_rate(match.group("rate"))
        if market_value <= 0:
            continue
        code = extract_fund_code(block) or ""

        implied_cost = market_value - profit if market_value > 0 else 0.0
        results.append(
            ParsedHolding(
                fund_code=code,
                fund_name=name,
                shares=0.0,
                cost_price=round(implied_cost, 2) if implied_cost > 0 else 0.0,
                market_value=market_value,
                profit=profit,
                profit_rate=profit_rate,
                platform="alipay",
                confidence=0.75 if not code else 0.85,
            )
        )
        seen_names.add(name)

    return results


def _looks_like_alipay_detail(text: str) -> bool:
    return bool(re.search(r"持有(?:份额|市值)|成本价", text))


def parse_alipay_text(text: str) -> list[ParsedHolding]:
    tab_rows = _parse_alipay_tab_export(text)
    if tab_rows:
        return tab_rows

    merged_rows = _parse_alipay_merged_text(text)
    if merged_rows:
        return merged_rows

    blocks = re.split(r"\n\s*\n", text.strip())
    if len(blocks) > 1 or _looks_like_alipay_detail(text):
        detail_rows = _parse_alipay_detail_text(text)
        if detail_rows:
            return detail_rows

    if "占比" in text or "占地" in text or re.search(r"\d比[\d.]+%", text):
        list_rows = _parse_alipay_list_text(text)
        if list_rows:
            return list_rows

    return []
