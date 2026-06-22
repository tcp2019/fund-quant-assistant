import json

from sqlmodel import Session

from app.db.models import Holding, PortfolioSnapshot, SignalRecord
from app.db.session import engine
from app.services.fund_catalog import load_catalog_fixture
from app.services.fund_rankings import load_rank_fixture
from app.services.opportunities import build_opportunities, summarize_reason


def test_summarize_reason():
    reasons = [{"layer": "rebalance", "rule": "category_underweight", "detail": "股票型低配"}]
    assert "大类低配" in summarize_reason(reasons) or "category_underweight" in summarize_reason(reasons)


def test_build_opportunities_partitions_actions():
    with Session(engine) as session:
        snap = PortfolioSnapshot(source="test")
        session.add(snap)
        session.commit()
        session.refresh(snap)

        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110011",
                fund_name="测试基金A",
                shares=100,
                cost_price=10.0,
                market_value=5000,
            )
        )
        session.add(
            SignalRecord(
                snapshot_id=snap.id,
                fund_code="110011",
                signal_type="reduce",
                score=-25.0,
                strength=4,
                suggested_amount=-3000.0,
                reasons_json=json.dumps(
                    [{"layer": "rebalance", "rule": "reduce", "detail": "集中度偏高"}]
                ),
            )
        )
        session.add(
            SignalRecord(
                snapshot_id=snap.id,
                fund_code="",
                signal_type="add",
                score=30.0,
                strength=4,
                suggested_amount=10000.0,
                reasons_json=json.dumps(
                    [
                        {
                            "layer": "rebalance",
                            "rule": "category_underweight",
                            "detail": "股票型低配",
                            "category": "stock",
                            "category_label": "股票型",
                        }
                    ]
                ),
            )
        )
        session.commit()

        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")

        out = build_opportunities(session, sell_limit=5, buy_limit=5, explore_limit=5, theme_limit=3)
        assert out.snapshot_id == snap.id
        assert len(out.sell_actions) == 1
        assert out.sell_actions[0].action == "sell"
        assert out.sell_actions[0].fund_code == "110011"
        assert len(out.explore_actions) >= 1
