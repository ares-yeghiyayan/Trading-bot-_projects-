# Maximilion Auto Trade Lab

A research-only, mock-only trading decision scaffold.

This is not a trading bot. It does not place live trades. It is a GitHub portfolio project for demonstrating controlled trading-decision infrastructure with safe defaults.

## Safety Defaults

```env
DRY_RUN=true
PAPER_ONLY=true
LIVE_TRADING_ENABLED=false
ALLOW_MARKET_ORDERS=false
```

## Quickstart

```bash
cd maximilion-auto-trade-lab
python -m venv .venv
pip install -e ".[dev]"
python -m maximilion_auto_trade_lab.cli status
pytest
```

## Safety Boundary

- No broker order sending.
- No MT5 broker-write execution path.
- No live execution.
- No secrets committed.
- Mock-only by default.
