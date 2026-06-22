"""Theme tagging for sector/theme exposure and search."""

from __future__ import annotations

THEME_RULES: list[tuple[str, list[str]]] = [
    ("storage_semiconductor", ["存储", "半导体", "芯片", "集成电路", "科创芯片"]),
    ("cpo_optics", ["CPO", "光模块", "通信设备", "光通信", "通信"]),
    ("ai_compute", ["人工智能", "算力", "AI", "机器人"]),
    ("new_energy", ["新能源", "光伏", "电池", "锂电", "碳中和"]),
    ("healthcare", ["医疗", "医药", "生物", "健康"]),
    ("consumer", ["消费", "白酒", "食品", "饮料"]),
    ("dividend", ["红利", "高股息", "股息"]),
    ("gold", ["黄金", "贵金属"]),
    ("qdii", ["QDII", "qdii", "海外", "全球"]),
]

THEME_LABELS: dict[str, str] = {
    "storage_semiconductor": "存储/半导体",
    "cpo_optics": "CPO/光通信",
    "ai_compute": "AI/算力",
    "new_energy": "新能源",
    "healthcare": "医药医疗",
    "consumer": "消费",
    "dividend": "红利",
    "gold": "黄金",
    "qdii": "QDII/海外",
}

THEME_SEARCH_ALIASES: dict[str, list[str]] = {
    "存储": ["存储", "半导体", "芯片"],
    "半导体": ["半导体", "芯片", "存储"],
    "cpo": ["CPO", "光模块", "通信设备", "光通信"],
    "光模块": ["光模块", "CPO", "光通信"],
    "ai": ["人工智能", "算力", "AI", "机器人"],
    "算力": ["算力", "人工智能", "AI"],
    "新能源": ["新能源", "光伏", "电池", "锂电"],
    "医药": ["医疗", "医药", "生物"],
    "消费": ["消费", "白酒", "食品"],
    "红利": ["红利", "高股息", "股息"],
}

THEME_SORT_FIELDS = ("return_1m", "return_1w", "return_1y")


def detect_themes(name: str, fund_type: str = "", extra_themes: list[str] | None = None) -> list[str]:
    text = f"{name}{fund_type}".upper()
    themes: list[str] = []
    for theme_id, keywords in THEME_RULES:
        for keyword in keywords:
            if keyword.upper() in text or keyword in f"{name}{fund_type}":
                themes.append(theme_id)
                break
    if extra_themes:
        for theme_id in extra_themes:
            if theme_id in THEME_LABELS and theme_id not in themes:
                themes.append(theme_id)
    return themes


def primary_theme(name: str, fund_type: str = "", extra_themes: list[str] | None = None) -> str | None:
    themes = detect_themes(name, fund_type, extra_themes)
    return themes[0] if themes else None


def theme_label(theme_id: str) -> str:
    return THEME_LABELS.get(theme_id, theme_id)


def theme_search_keywords(query: str) -> list[str] | None:
    normalized = query.strip().lower()
    if not normalized:
        return None
    if normalized in THEME_SEARCH_ALIASES:
        return THEME_SEARCH_ALIASES[normalized]
    for alias, keywords in THEME_SEARCH_ALIASES.items():
        if alias in normalized or normalized in alias:
            return keywords
    return None


def fund_matches_theme(name: str, fund_type: str, theme_id: str, extra_themes: list[str] | None = None) -> bool:
    return theme_id in detect_themes(name, fund_type, extra_themes)
