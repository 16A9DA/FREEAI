import typer
from rich.console import Console

from freecode import ollama_client
from freecode.config import load_config

app = typer.Typer(help="freeai local AI coding assistant.")
console = Console()

LOGO = r"""
 _____ ____  _____ _____    _    ___
|  ___|  _ \| ____| ____|  / \  |_ _|
| |_  | |_) |  _| |  _|   / _ \  | |
|  _| |  _ <| |___| |___ / ___ \ | |
|_|   |_| \_\_____|_____/_/   \_\___|
"""


@app.callback(invoke_without_command=True)
def main():
    if not ollama_client.check_running():
        console.print(
            "[red]Ollama not running at localhost:11434. Start it with `ollama serve`.[/red]"
        )
        raise typer.Exit(1)
    cfg = load_config()
    model = cfg.get("active_model")
    console.print(LOGO, style="white")
    if not model:
        console.print("[yellow]No active model set. Run `aimodel` to pull and pick one.[/yellow]")
        raise typer.Exit(0)
    console.print(f"Active model: [bold]{model}[/bold]")
    task_loop(model)


def task_loop(model):
    while True:
        task = console.input("\n[bold cyan]task>[/bold cyan] ").strip()
        if task.lower() in {"exit", "quit", ""}:
            console.print("Bye.")
            break
        console.print("[dim]Plan generation and the agent loop land in Day 3.[/dim]")
