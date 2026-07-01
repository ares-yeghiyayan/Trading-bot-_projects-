"""Small CLI for the research-only scaffold."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from maximilion_auto_trade_lab.config import load_config

app = typer.Typer(help="Research-only mock trading decision scaffold.")
console = Console()


@app.command()
def status() -> None:
    config = load_config()
    table = Table(title="Maximilion Auto Trade Lab")
    table.add_column("Field")
    table.add_column("Value")
    for key, value in config.safety_summary().items():
        table.add_row(key, str(value))
    console.print(table)


@app.command("validate-config")
def validate_config() -> None:
    config = load_config()
    if not config.dry_run or not config.paper_only:
        raise typer.Exit(1)
    if config.live_trading_enabled or config.allow_market_orders:
        raise typer.Exit(1)
    console.print("Configuration is safe: dry-run, paper-only, no live execution.")


if __name__ == "__main__":
    app()
