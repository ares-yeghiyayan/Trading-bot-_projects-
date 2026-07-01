# Forex Pairs

## Project

`forex-pairs`

## Script

- [`jimi_forex_one_cell_executor.py`](jimi_forex_one_cell_executor.py)

## Purpose

A Jupyter Notebook / Python one-cell executor for MetaTrader 5 focused on selected forex pairs.

## Current Scope

- selected forex symbols
- MT5 connection check
- command parsing from `JIMI_COMMANDS`
- order validation
- spread checks in pips
- pending/market order support
- old signal reconciliation
- Jimi-managed pending order and position display

## Symbols

- `GBPUSD`
- `EURUSD`
- `USDJPY`
- `AUDUSD`
- `USDCAD`
- `USDCHF`

## Safety Notes

This project is code storage and development work only.

It is not financial advice and not a performance claim.

Before running:

1. Use a demo account first.
2. Set `DRY_RUN=True` while testing.
3. Keep `ALLOW_REAL_ACCOUNT=False` unless you fully understand the risk.
4. Do not commit broker credentials or account secrets.
