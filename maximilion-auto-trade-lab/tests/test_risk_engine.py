from maximilion_auto_trade_lab.config import AppConfig
from maximilion_auto_trade_lab.risk.risk_engine import review_candidate
from maximilion_auto_trade_lab.schemas import (
    CandidateDecision,
    MacroContext,
    SnapshotState,
    TechnicalContext,
)


def test_no_trade_is_blocked() -> None:
    review = review_candidate(
        make_candidate(decision="NO_TRADE", side="NONE", action_kind="NONE"),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert not review.approved_for_paper_preview
    assert "Candidate decision is NO_TRADE or WAIT." in review.block_reasons


def test_wait_is_blocked() -> None:
    review = review_candidate(
        make_candidate(decision="WAIT", side="NONE", action_kind="NONE"),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert not review.approved_for_paper_preview
    assert "Candidate decision is NO_TRADE or WAIT." in review.block_reasons


def test_allow_review_false_is_blocked() -> None:
    review = review_candidate(
        make_candidate(allow_review=False),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert not review.approved_for_paper_preview
    assert "Candidate is not allowed for risk review." in review.block_reasons


def test_market_action_blocked_by_default() -> None:
    review = review_candidate(
        make_candidate(decision="MARKET_SELL", action_kind="MARKET"),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert not review.approved_for_paper_preview
    assert "Market actions are disabled." in review.block_reasons


def test_missing_sl_is_blocked() -> None:
    review = review_candidate(
        make_candidate(sl=None),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert "Stop loss is required." in review.block_reasons


def test_missing_tp_is_blocked() -> None:
    review = review_candidate(
        make_candidate(tp=None),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert "Take profit is required." in review.block_reasons


def test_pending_without_entry_is_blocked() -> None:
    review = review_candidate(
        make_candidate(entry=None),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert "Pending action requires an entry price." in review.block_reasons


def test_lot_above_max_is_blocked() -> None:
    review = review_candidate(
        make_candidate(lot=0.02),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert "Candidate lot exceeds maximum allowed lot." in review.block_reasons
    assert review.normalized_lot == 0.01


def test_high_news_risk_is_blocked() -> None:
    review = review_candidate(
        make_candidate(),
        make_macro(news_risk_level="HIGH"),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert "High news risk blocks review." in review.block_reasons


def test_trading_not_allowed_is_blocked() -> None:
    review = review_candidate(
        make_candidate(),
        make_macro(trading_allowed=False),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert "Macro context says trading is not allowed." in review.block_reasons


def test_buy_against_bearish_higher_timeframe_is_blocked() -> None:
    review = review_candidate(
        make_candidate(decision="BUY_PULLBACK", side="BUY"),
        make_macro(),
        make_technical(higher_timeframe_bias="bearish"),
        make_snapshot(),
        AppConfig(),
    )

    assert "BUY conflicts with bearish higher-timeframe bias." in review.block_reasons


def test_sell_against_bullish_higher_timeframe_is_blocked() -> None:
    review = review_candidate(
        make_candidate(decision="SELL_PULLBACK", side="SELL"),
        make_macro(),
        make_technical(higher_timeframe_bias="bullish"),
        make_snapshot(),
        AppConfig(),
    )

    assert "SELL conflicts with bullish higher-timeframe bias." in review.block_reasons


def test_m1_only_signal_is_blocked() -> None:
    review = review_candidate(
        make_candidate(),
        make_macro(),
        make_technical(m1_only_signal=True),
        make_snapshot(),
        AppConfig(),
    )

    assert "M1-only signal is not enough for review approval." in review.block_reasons


def test_duplicate_pending_is_blocked() -> None:
    review = review_candidate(
        make_candidate(),
        make_macro(),
        make_technical(),
        make_snapshot(pending_jimi_exists=True),
        AppConfig(),
    )

    assert review.duplicate_snapshot_detected
    assert "Duplicate Jimi pending snapshot detected." in review.block_reasons


def test_same_direction_position_is_blocked() -> None:
    review = review_candidate(
        make_candidate(),
        make_macro(),
        make_technical(),
        make_snapshot(same_direction_position_exists=True),
        AppConfig(),
    )

    assert review.active_snapshot_detected
    assert "Same-direction active position snapshot detected." in review.block_reasons


def test_gold_vertical_spike_is_blocked() -> None:
    review = review_candidate(
        make_candidate(symbol="XAUUSD", decision="BUY_PULLBACK", side="BUY"),
        make_macro(symbol="XAUUSD"),
        make_technical(symbol="XAUUSD", gold_vertical_spike=True),
        make_snapshot(),
        AppConfig(),
    )

    assert "Gold vertical spike blocks review." in review.block_reasons
    assert review.route_name == "GOLD"


def test_usdjpy_buy_in_intervention_zone_is_blocked() -> None:
    review = review_candidate(
        make_candidate(symbol="USDJPY", decision="BUY_PULLBACK", side="BUY"),
        make_macro(symbol="USDJPY"),
        make_technical(symbol="USDJPY", last_price=163.0),
        make_snapshot(),
        AppConfig(),
    )

    assert "USDJPY BUY is blocked in the intervention risk zone." in review.block_reasons


def test_unknown_symbol_is_blocked() -> None:
    review = review_candidate(
        make_candidate(symbol="BTCUSD"),
        make_macro(symbol="BTCUSD"),
        make_technical(symbol="BTCUSD"),
        make_snapshot(),
        AppConfig(),
    )

    assert "Unknown symbol route." in review.block_reasons
    assert review.route_name == "NONE"
    assert review.magic is None


def test_clean_sell_pullback_can_be_approved_for_paper_preview() -> None:
    review = review_candidate(
        make_candidate(),
        make_macro(),
        make_technical(),
        make_snapshot(),
        AppConfig(),
    )

    assert review.approved_for_paper_preview
    assert review.final_decision == "SELL_PULLBACK"
    assert review.block_reasons == []
    assert review.route_name == "FOREX"
    assert review.magic == 260630


def test_non_jimi_orders_create_warning_not_block() -> None:
    review = review_candidate(
        make_candidate(),
        make_macro(),
        make_technical(),
        make_snapshot(non_jimi_orders_exist=True),
        AppConfig(),
    )

    assert review.approved_for_paper_preview
    assert "Non-Jimi snapshots exist; they are reported only and never modified." in review.warnings


def make_candidate(
    decision: str = "SELL_PULLBACK",
    symbol: str = "GBPUSD",
    side: str = "SELL",
    action_kind: str = "PENDING",
    entry: float | None = 1.2500,
    sl: float | None = 1.2530,
    tp: float | None = 1.2440,
    lot: float = 0.01,
    allow_review: bool = True,
) -> CandidateDecision:
    return CandidateDecision(
        decision=decision,
        symbol=symbol,
        side=side,
        action_kind=action_kind,
        entry=entry,
        sl=sl,
        tp=tp,
        lot=lot,
        confidence=0.70,
        rationale=["Deterministic test candidate."],
        blockers=[],
        timeframe_alignment={"H4": "bearish", "H1": "bearish"},
        risk_notes=[],
        allow_review=allow_review,
    )


def make_macro(
    symbol: str = "GBPUSD",
    news_risk_level: str = "LOW",
    trading_allowed: bool = True,
) -> MacroContext:
    return MacroContext(
        symbol=symbol,
        news_risk_level=news_risk_level,
        trading_allowed=trading_allowed,
        notes=[],
    )


def make_technical(
    symbol: str = "GBPUSD",
    higher_timeframe_bias: str = "bearish",
    execution_timeframe_bias: str = "bearish",
    m1_trigger_state: str = "none",
    m1_only_signal: bool = False,
    gold_vertical_spike: bool = False,
    last_price: float | None = 1.25,
    spread_points: float = 12.0,
) -> TechnicalContext:
    return TechnicalContext(
        symbol=symbol,
        higher_timeframe_bias=higher_timeframe_bias,
        execution_timeframe_bias=execution_timeframe_bias,
        m1_trigger_state=m1_trigger_state,
        m1_only_signal=m1_only_signal,
        gold_vertical_spike=gold_vertical_spike,
        last_price=last_price,
        spread_points=spread_points,
        timeframe_alignment={"H4": higher_timeframe_bias, "H1": execution_timeframe_bias},
        notes=[],
    )


def make_snapshot(
    pending_jimi_exists: bool = False,
    same_direction_position_exists: bool = False,
    non_jimi_orders_exist: bool = False,
) -> SnapshotState:
    return SnapshotState(
        pending_jimi_exists=pending_jimi_exists,
        same_direction_position_exists=same_direction_position_exists,
        non_jimi_orders_exist=non_jimi_orders_exist,
    )
