"""Core Pydantic schemas for the mock-only scaffold."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DecisionName = Literal["NO_TRADE", "WAIT", "BUY_PULLBACK", "SELL_PULLBACK"]
Side = Literal["BUY", "SELL", "NONE"]
ActionKind = Literal["PENDING", "MARKET", "NONE"]


class CandidateDecision(BaseModel):
    decision: DecisionName = "WAIT"
    symbol: str
    side: Side = "NONE"
    action_kind: ActionKind = "NONE"
    entry: float | None = None
    sl: float | None = None
    tp: float | None = None
    lot: float = 0.01
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class RiskReview(BaseModel):
    approved_for_paper_preview: bool = False
    final_decision: str = "WAIT"
    block_reasons: list[str] = Field(default_factory=list)
    normalized_lot: float = 0.01
