import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

HISTORY_PATH = Path.home() / ".freecode" / "history.json"

app = typer.Typer(help="Show past tasks.")
console = Console()


def load_history():
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text())
    return []


@app.callback(invoke_without_command=True)
def main():
    entries = load_history()
    if not entries:
        console.print("No history yet.")
        return
    table = Table(title="Task history")
    table.add_column("time", style="dim")
    table.add_column("task")
    table.add_column("status")
    for e in entries:
        table.add_row(e.get("timestamp", "-"), e.get("task", "-"), e.get("status", "-"))
    console.print(table)
