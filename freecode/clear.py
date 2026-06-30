import typer
from rich.console import Console
from rich.prompt import Confirm

from freecode.history import HISTORY_PATH

SESSION_PATH = HISTORY_PATH.parent / "session.json"

app = typer.Typer(help="Wipe session memory.")
console = Console()


@app.callback(invoke_without_command=True)
def main(history: bool = typer.Option(False, "--history", help="Also clear task history.")):
    if SESSION_PATH.exists():
        SESSION_PATH.unlink()
    console.print("[green]Session memory cleared.[/green]")
    if history and HISTORY_PATH.exists():
        if Confirm.ask("Also delete task history?", default=False):
            HISTORY_PATH.unlink()
            console.print("[green]History cleared.[/green]")
