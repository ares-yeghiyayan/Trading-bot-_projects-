from maximilion_auto_trade_lab.constants import (
    FOREX_MAGIC,
    GOLD_MAGIC,
    is_forex_symbol,
    is_gold_symbol,
    route_symbol,
)


def test_forex_routes_to_forex() -> None:
    assert route_symbol("GBPUSD") == ("FOREX", FOREX_MAGIC)


def test_gold_routes_to_gold() -> None:
    assert route_symbol("XAUUSD") == ("GOLD", GOLD_MAGIC)


def test_gold_does_not_route_to_forex() -> None:
    assert not is_forex_symbol("XAUUSD")


def test_forex_does_not_route_to_gold() -> None:
    assert not is_gold_symbol("EURUSD")
