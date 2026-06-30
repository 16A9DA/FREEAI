import typer
from rich.console import Console
from rich.prompt import Confirm

from freecode import agent, ollama_client, parser, planner
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
    if parser.load_skills():
        console.print("[green]Project skills active (.freeai)[/green]")
    task_loop(model)


def task_loop(model):
    while True:
        task = console.input("\n[bold cyan]task>[/bold cyan] ").strip()
        if task.lower() in {"exit", "quit", ""}:
            console.print("Bye.")
            break
        task = parser.parse_mentions(task, model)
        steps = planner.generate_plan(task, model)
        if not steps:
            console.print("[yellow]No plan produced. Try rephrasing.[/yellow]")
            continue
        console.print("\n[bold]Plan[/bold]")
        for i, s in enumerate(steps, 1):
            console.print(f"  {i}. {s}")
        if Confirm.ask("Approve this plan?", default=True):
            agent.run(steps, model)
        else:
            console.print("[dim]Refine your task and try again.[/dim]")
