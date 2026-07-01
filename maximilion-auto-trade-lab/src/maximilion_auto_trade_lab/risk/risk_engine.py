"""Deterministic research-only risk engine."""

from __future__ import annotations

from maximilion_auto_trade_lab.config import AppConfig
from maximilion_auto_trade_lab.constants import max_spread_for_symbol, route_symbol
from maximilion_auto_trade_lab.risk.rules import (
    rule_allow_review_false,
    rule_duplicate_pending_snapshot,
    rule_gold_vertical_spike,
    rule_high_news_risk,
    rule_higher_timeframe_conflict,
    rule_lot_limit,
    rule_m1_only_signal,
    rule_market_actions_disabled,
    rule_missing_sl,
    rule_missing_tp,
    rule_no_trade_or_wait,
    rule_paper_only_gate,
    rule_pending_entry_required,
    rule_same_direction_position_snapshot,
    rule_spread_limit,
    rule_unknown_symbol_route,
    rule_usdjpy_intervention_zone,
)
from maximilion_auto_trade_lab.schemas import (
    CandidateDecision,
    MacroContext,
    RiskReview,
    SnapshotState,
    TechnicalContext,
)


def review_candidate(
    candidate: CandidateDecision,
    macro: MacroContext,
    technical: TechnicalContext,
    snapshot: SnapshotState,
    config: AppConfig,
) -> RiskReview:
    route_name, magic = route_symbol(candidate.symbol)

    rule_results = [
        rule_unknown_symbol_route(candidate),
        rule_no_trade_or_wait(candidate),
        rule_allow_review_false(candidate),
        rule_market_actions_disabled(candidate, config),
        rule_missing_sl(candidate),
        rule_missing_tp(candidate),
        rule_pending_entry_required(candidate),
        rule_lot_limit(candidate, config),
        rule_spread_limit(candidate, technical),
        rule_high_news_risk(macro),
        rule_higher_timeframe_conflict(candidate, technical),
        rule_m1_only_signal(technical),
        rule_duplicate_pending_snapshot(snapshot),
        rule_same_direction_position_snapshot(snapshot),
        rule_gold_vertical_spike(candidate, technical),
        rule_usdjpy_intervention_zone(candidate, technical),
    ]

    block_reasons = [reason for blocked, reason in rule_results if blocked and reason]
    approved = len(block_reasons) == 0

    warnings = []
    _, paper_warning = rule_paper_only_gate()
    if paper_warning:
        warnings.append(paper_warning)

    if snapshot.non_jimi_orders_exist:
        warnings.append("Non-Jimi snapshots exist; they are reported only and never modified.")

    return RiskReview(
        approved_for_paper_preview=approved,
        final_decision=candidate.decision if approved else "WAIT",
        block_reasons=block_reasons,
        warnings=warnings,
        normalized_lot=min(candidate.lot, config.max_lot),
        risk_usd_estimate=None,
        spread_ok=technical.spread_points <= max_spread_for_symbol(candidate.symbol),
        duplicate_snapshot_detected=snapshot.pending_jimi_exists,
        active_snapshot_detected=snapshot.same_direction_position_exists,
        magic=magic,
        route_name=route_name,
    )
