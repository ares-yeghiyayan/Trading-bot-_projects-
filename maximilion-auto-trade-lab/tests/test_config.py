from maximilion_auto_trade_lab.config import AppConfig


def test_default_config_is_dry_run() -> None:
    assert AppConfig().dry_run is True


def test_default_config_is_paper_only() -> None:
    assert AppConfig().paper_only is True


def test_live_trading_is_false_by_default() -> None:
    assert AppConfig().live_trading_enabled is False


def test_market_actions_are_false_by_default() -> None:
    assert AppConfig().allow_market_orders is False
