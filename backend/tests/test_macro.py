from app.services.macro import classify_environment


def test_rising_yields_tight():
    assert classify_environment(3.5, 2.8, 2.0) == "tight"


def test_falling_yields_loose():
    assert classify_environment(2.5, 3.0, 1.0) == "loose"


def test_stable_neutral():
    assert classify_environment(2.85, 2.80, 1.5) == "neutral"


def test_small_change_neutral():
    assert classify_environment(2.85, 2.70, 1.6) == "neutral"
