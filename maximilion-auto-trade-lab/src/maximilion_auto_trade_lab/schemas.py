"""Core Pydantic schemas for the research-only risk engine."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DecisionName = Literal[
    "NO_TRADE",
    "WAIT",
    "BUY_PULLBACK",
    "SELL_PULLBACK",
    "MARKET_BUY",
    "MARKET_SELL",
]
Side = Literal["BUY", "SELL", "NONE"]
ActionKind = Literal["PENDING", "MARKET", "NONE"]
BiasState = Literal["bullish", "bearish", "mixed"]
M1TriggerState = Literal["bullish", "bearish", "mixed", "none"]
NewsRiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
RouteName = Literal["FOREX", "GOLD", "NONE"]


class CandidateDecision(BaseModel):
    decision: DecisionName
    symbol: str
    side: Side
    action_kind: ActionKind
    entry: float | None = None
    sl: float | None = None
    tp: float | None = None
    lot: float = Field(default=0.01, gt=0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    timeframe_alignment: dict[str, str] = Field(default_factory=dict)
    risk_notes: list[str] = Field(default_factory=list)
    allow_review: bool = True


class MacroContext(BaseModel):
    symbol: str
    news_risk_level: NewsRiskLevel = "LOW"
    trading_allowed: bool = True
    notes: list[str] = Field(default_factory=list)


class TechnicalContext(BaseModel):
    symbol: str
    higher_timeframe_bias: BiasState = "mixed"
    execution_timeframe_bias: BiasState = "mixed"
    m1_trigger_state: M1TriggerState = "none"
    m1_only_signal: bool = False
    gold_vertical_spike: bool = False
    last_price: float | None = None
    spread_points: float = 0.0
    timeframe_alignment: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class SnapshotState(BaseModel):
    pending_jimi_exists: bool = False
    same_direction_position_exists: bool = False
    non_jimi_orders_exist: bool = False


class RiskReview(BaseModel):
    approved_for_paper_preview: bool
    final_decision: str
    block_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    normalized_lot: float
    risk_usd_estimate: float | None = None
    spread_ok: bool
    duplicate_snapshot_detected: bool
    active_snapshot_detected: bool
    magic: int | None
    route_name: RouteName
