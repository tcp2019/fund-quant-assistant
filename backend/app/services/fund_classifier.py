CATEGORY_RULES = [
    ("债券", "bond"),
    ("货币", "money"),
    ("QDII", "qdii"),
    ("黄金", "gold"),
    ("混合", "stock"),
    ("股票", "stock"),
    ("指数", "stock"),
]


def classify_fund(name: str, fund_type: str = "") -> str:
    text = name + fund_type
    for keyword, cat in CATEGORY_RULES:
        if keyword in text:
            return cat
    return "other"
