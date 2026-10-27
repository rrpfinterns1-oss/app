from carbon_explorer.fmt import MINUS, input_pct, num, pct, signed, signed_pct, signed_usd, usd


def test_num():
    assert num(2060410) == "2,060,410"
    assert num(762351.7) == "762,351.7"
    assert num(-73440) == f"{MINUS}73,440"
    assert num(0.0) == "0"


def test_signed():
    assert signed(73440) == "+73,440"
    assert signed(-6) == f"{MINUS}6"
    assert signed(0) == "0"


def test_percentages():
    assert pct(0.7054) == "70.5%"
    assert pct(None) == "n/a"
    assert signed_pct(-0.0356434) == f"{MINUS}3.6%"
    assert signed_pct(0.0) == "0.0%"
    assert input_pct(50.0) == "50%"
    assert input_pct(12.5) == "12.5%"


def test_usd():
    assert usd(44916938) == "$44,916,938"
    assert usd(21.8, 2) == "$21.80"
    assert usd(None) == "n/a"
    assert signed_usd(-3637620.39) == f"{MINUS}$3,637,620"
    assert signed_usd(1200) == "+$1,200"
