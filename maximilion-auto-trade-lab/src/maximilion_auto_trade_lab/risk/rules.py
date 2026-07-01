"""Pure risk rules for research-only candidate review."""

from __future__ import annotations

from maximilion_auto_trade_lab.config import AppConfig
from maximilion_auto_trade_lab.constants import (
    USDJPY_INTERVENTION_MAX,
    USDJPY_INTERVENTION_MIN,
    max_spread_for_symbol,
    normalize_symbol,
    route_symbol,
)
from maximilion_auto_trade_lab.schemas import (
    CandidateDecision,
    MacroContext,
    SnapshotState,
    TechnicalContext,
)


def rule_unknown_symbol_route(candidate: CandidateDecision) -> tuple[bool, str | None]:
    route_name, _ = route_symbol(candidate.symbol)
    if route_name == "NONE":
        return True, "Unknown symbol route."
    return False, None


def rule_no_trade_or_wait(candidate: CandidateDecision) -> tuple[bool, str | None]:
    if candidate.decision in {"NO_TRADE", "WAIT"}:
        return True, "Candidate decision is NO_TRADE or WAIT."
    return False, None


def rule_allow_review_false(candidate: CandidateDecision) -> tuple[bool, str | None]:
    if not candidate.allow_review:
        return True, "Candidate is not allowed for risk review."
    return False, None


def rule_market_actions_disabled(
    candidate: CandidateDecision,
    config: AppConfig,
) -> tuple[bool, str | None]:
    if candidate.action_kind == "MARKET" and not config.allow_market_orders:
        return True, "Market actions are disabled."
    return False, None


def rule_missing_sl(candidate: CandidateDecision) -> tuple[bool, str | None]:
    if _needs_action(candidate) and candidate.sl is None:
        return True, "Stop loss is required."
    return False, None


def rule_missing_tp(candidate: CandidateDecision) -> tuple[bool, str | None]:
    if _needs_action(candidate) and candidate.tp is None:
        return True, "Take profit is required."
    return False, None


def rule_pending_entry_required(candidate: CandidateDecision) -> tuple[bool, str | None]:
    if candidate.action_kind == "PENDING" and candidate.entry is None:
        return True, "Pending action requires an entry price."
    return False, None


def rule_lot_limit(
    candidate: CandidateDecision,
    config: AppConfig,
) -> tuple[bool, str | None]:
    if candidate.lot > config.max_lot:
        return True, "Candidate lot exceeds maximum allowed lot."
    return False, None


def rule_spread_limit(
    candidate: CandidateDecision,
    technical: TechnicalContext,
) -> tuple[bool, str | None]:
    route_name, _ = route_symbol(candidate.symbol)
    if route_name == "NONE":
        return False, None

    max_spread = max_spread_for_symbol(candidate.symbol)
    if technical.spread_points > max_spread:
        return True, "Spread exceeds maximum allowed spread."
    return False, None


def rule_high_news_risk(macro: MacroContext) -> tuple[bool, str | None]:
    if macro.news_risk_level == "HIGH":
        return True, "High news risk blocks review."
    if not macro.trading_allowed:
        return True, "Macro context says trading is not allowed."
    return False, None


def rule_higher_timeframe_conflict(
    candidate: CandidateDecision,
    technical: TechnicalContext,
) -> tuple[bool, str | None]:
    if candidate.side == "BUY":
        if technical.higher_timeframe_bias == "bearish":
            return True, "BUY conflicts with bearish higher-timeframe bias."
        if technical.execution_timeframe_bias == "bearish":
            return True, "BUY conflicts with bearish execution-timeframe bias."

    if candidate.side == "SELL":
        if technical.higher_timeframe_bias == "bullish":
            return True, "SELL conflicts with bullish higher-timeframe bias."
        if technical.execution_timeframe_bias == "bullish":
            return True, "SELL conflicts with bullish execution-timeframe bias."

    return False, None


def rule_m1_only_signal(technical: TechnicalContext) -> tuple[bool, str | None]:
    if technical.m1_only_signal:
        return True, "M1-only signal is not enough for review approval."
    return False, None


def rule_duplicate_pending_snapshot(snapshot: SnapshotState) -> tuple[bool, str | None]:
    if snapshot.pending_jimi_exists:
        return True, "Duplicate Jimi pending snapshot detected."
    return False, None


def rule_same_direction_position_snapshot(snapshot: SnapshotState) -> tuple[bool, str | None]:
    if snapshot.same_direction_position_exists:
        return True, "Same-direction active position snapshot detected."
    return False, None


def rule_gold_vertical_spike(
    candidate: CandidateDecision,
    technical: TechnicalContext,
) -> tuple[bool, str | None]:
    route_name, _ = route_symbol(candidate.symbol)
    if route_name == "GOLD" and technical.gold_vertical_spike:
        return True, "Gold vertical spike blocks review."
    return False, None


def rule_usdjpy_intervention_zone(
    candidate: CandidateDecision,
    technical: TechnicalContext,
) -> tuple[bool, str | None]:
    symbol = normalize_symbol(candidate.symbol)
    if symbol != "USDJPY" or candidate.side != "BUY" or technical.last_price is None:
        return False, None

    if USDJPY_INTERVENTION_MIN <= technical.last_price <= USDJPY_INTERVENTION_MAX:
        return True, "USDJPY BUY is blocked in the intervention risk zone."
    return False, None


def rule_paper_only_gate() -> tuple[bool, str | None]:
    return False, "Paper preview only; no live execution approval."


def _needs_action(candidate: CandidateDecision) -> bool:
    return candidate.action_kind in {"PENDING", "MARKET"} and candidate.side in {"BUY", "SELL"}
