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


def append_session(task, step_usage):
    import datetime
    entries = load_history()
    total = sum(p + c for _, p, c in step_usage)
    entries.append({
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "task": task,
        "status": "done",
        "total_tokens": total,
        "steps": [{"step": s, "prompt_tokens": p, "completion_tokens": c} for s, p, c in step_usage],
    })
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(entries, indent=2))


@app.callback(invoke_without_command=True)
def main():
    entries = load_history()
    if not entries:
        console.print("No history yet.")
        return
    table = Table(title="Task history")
    table.add_column("time", style="dim")
    table.add_column("task", overflow="fold")
    table.add_column("status")
    table.add_column("tokens", justify="right")
    for e in entries:
        tokens = e.get("total_tokens")
        table.add_row(e.get("timestamp", "-"), e.get("task", "-"), e.get("status", "-"),
                       f"{tokens:,}" if tokens is not None else "-")
    console.print(table)
