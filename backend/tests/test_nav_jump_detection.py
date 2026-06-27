from app.services.data_sync import detect_nav_jump


def test_detect_normal_navs():
    navs = [
        {"date": "2026-01-01", "nav": 1.00},
        {"date": "2026-01-02", "nav": 1.01},
        {"date": "2026-01-03", "nav": 0.99},
    ]
    anomalies = detect_nav_jump(navs)
    assert len(anomalies) == 0


def test_detect_nav_halving_from_split():
    navs = [
        {"date": "2026-01-01", "nav": 2.00},
        {"date": "2026-01-02", "nav": 1.00},
    ]
    anomalies = detect_nav_jump(navs)
    assert len(anomalies) == 1
    assert anomalies[0]["date"] == "2026-01-02"
    assert abs(anomalies[0]["change_pct"] - 50.0) < 0.01
    assert "拆分" in anomalies[0]["likely_reason"]


def test_detect_nav_spike_anomaly():
    navs = [
        {"date": "2026-01-01", "nav": 1.00},
        {"date": "2026-01-02", "nav": 1.30},
    ]
    anomalies = detect_nav_jump(navs)
    assert len(anomalies) == 1
    assert anomalies[0]["change_pct"] > 15


def test_skip_zero_nav():
    navs = [
        {"date": "2026-01-01", "nav": 0.00},
        {"date": "2026-01-02", "nav": 1.00},
    ]
    anomalies = detect_nav_jump(navs)
    assert len(anomalies) == 0


def test_empty_navs():
    anomalies = detect_nav_jump([])
    assert len(anomalies) == 0
