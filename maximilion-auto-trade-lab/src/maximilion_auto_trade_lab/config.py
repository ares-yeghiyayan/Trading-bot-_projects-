"""Safe default configuration."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    app_env: str = "dev"
    dry_run: bool = True
    paper_only: bool = True
    live_trading_enabled: bool = False
    allow_market_orders: bool = False
    kill_switch: bool = False
    market_data_provider: str = "mock"
    decision_provider: str = "mock"
    executor_provider: str = "mock"
    default_lot: float = Field(default=0.01, gt=0)
    max_lot: float = Field(default=0.01, gt=0)

    def safety_summary(self) -> dict[str, object]:
        return {
            "dry_run": self.dry_run,
            "paper_only": self.paper_only,
            "live_trading_enabled": self.live_trading_enabled,
            "allow_market_orders": self.allow_market_orders,
            "market_data_provider": self.market_data_provider,
            "decision_provider": self.decision_provider,
            "executor_provider": self.executor_provider,
        }


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def load_config() -> AppConfig:
    return AppConfig(
        app_env=os.getenv("APP_ENV", "dev"),
        dry_run=_env_bool("DRY_RUN", True),
        paper_only=_env_bool("PAPER_ONLY", True),
        live_trading_enabled=_env_bool("LIVE_TRADING_ENABLED", False),
        allow_market_orders=_env_bool("ALLOW_MARKET_ORDERS", False),
        kill_switch=_env_bool("KILL_SWITCH", False),
        market_data_provider=os.getenv("MARKET_DATA_PROVIDER", "mock"),
        decision_provider=os.getenv("DECISION_PROVIDER", "mock"),
        executor_provider=os.getenv("EXECUTOR_PROVIDER", "mock"),
        default_lot=float(os.getenv("DEFAULT_LOT", "0.01")),
        max_lot=float(os.getenv("MAX_LOT", "0.01")),
    )
