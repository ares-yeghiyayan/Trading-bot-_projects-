# Gold — 1/7/2026

## Project

`gold-1-7-2026`

## Script

- [`jimi_gold_one_cell_executor.py`](jimi_gold_one_cell_executor.py)

## Purpose

A Jupyter Notebook / Python one-cell executor for MetaTrader 5 focused only on Gold/XAUUSD-style symbols.

## Current Scope

- Gold/XAUUSD only
- MT5 connection check
- command parsing from `JIMI_COMMANDS`
- order validation
- spread and SL/TP distance checks
- pending/market order support
- old signal reconciliation
- Jimi-managed pending order and position display

## Safety Notes

This project is code storage and development work only.

It is not financial advice, not a signal service, not a guarantee of execution quality, and not a performance claim.

Before running:

1. Use a demo account first.
2. Set `DRY_RUN=True` while testing.
3. Keep `ALLOW_REAL_ACCOUNT=False` unless you fully understand the risk.
4. Do not commit broker credentials or account secrets.
