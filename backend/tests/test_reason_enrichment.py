from app.services.signals.reason_enrichment import enrich_high_correlation_reasons


def test_enrich_legacy_correlation_reason():
    reasons = [
        {
            "layer": "concentration",
            "rule": "high_correlation",
            "detail": "013470 与 011370 相关系数 0.94 超过 0.85，存在同源暴露，建议合并或减一只",
        }
    ]
    names = {
        "013470": "泰信低碳经济混合 C",
        "011370": "某配对基金 A",
    }
    enriched = enrich_high_correlation_reasons(reasons, "013470", names)
    assert enriched[0]["paired_fund_code"] == "011370"
    assert enriched[0]["paired_fund_name"] == "某配对基金 A"
    assert enriched[0]["correlation"] == 0.94


def test_enrich_keeps_existing_structured_fields():
    reasons = [
        {
            "layer": "concentration",
            "rule": "high_correlation",
            "detail": "already formatted",
            "paired_fund_code": "011840",
            "paired_fund_name": "已有名称",
            "correlation": 0.87,
        }
    ]
    enriched = enrich_high_correlation_reasons(reasons, "013470", {})
    assert enriched[0]["paired_fund_code"] == "011840"
    assert enriched[0]["paired_fund_name"] == "已有名称"
    assert enriched[0]["correlation"] == 0.87


def test_enrich_non_correlation_reason_unchanged():
    reasons = [{"layer": "rebalance", "rule": "category_underweight", "detail": "股票型低配"}]
    enriched = enrich_high_correlation_reasons(reasons, "013470", {})
    assert enriched == reasons
