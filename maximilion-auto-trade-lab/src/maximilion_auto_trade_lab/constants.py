"""Static symbol routing and safety constants."""

from __future__ import annotations

from typing import Literal

RouteName = Literal["FOREX", "GOLD", "NONE"]

FOREX_SYMBOLS = frozenset(
    {
        "GBPUSD",
        "EURUSD",
        "USDJPY",
        "AUDUSD",
        "USDCAD",
        "USDCHF",
    }
)

GOLD_SYMBOLS = frozenset(
    {
        "XAUUSD",
        "XAUUSDM",
        "XAUUSD.",
        "GOLD",
    }
)

FOREX_MAGIC = 260630
GOLD_MAGIC = 26063099

USDJPY_INTERVENTION_MIN = 162.80
USDJPY_INTERVENTION_MAX = 163.50

DEFAULT_LOT = 0.01
MAX_LOT = 0.01

MAX_SPREAD_FOREX_POINTS = 25.0
MAX_SPREAD_GOLD_POINTS = 80.0


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def route_symbol(symbol: str) -> tuple[RouteName, int | None]:
    normalized = normalize_symbol(symbol)
    if normalized in FOREX_SYMBOLS:
        return "FOREX", FOREX_MAGIC
    if normalized in GOLD_SYMBOLS:
        return "GOLD", GOLD_MAGIC
    return "NONE", None


def is_forex_symbol(symbol: str) -> bool:
    return route_symbol(symbol)[0] == "FOREX"


def is_gold_symbol(symbol: str) -> bool:
    return route_symbol(symbol)[0] == "GOLD"


def max_spread_for_symbol(symbol: str) -> float:
    route_name, _ = route_symbol(symbol)
    if route_name == "FOREX":
        return MAX_SPREAD_FOREX_POINTS
    if route_name == "GOLD":
        return MAX_SPREAD_GOLD_POINTS
    return float("inf")
