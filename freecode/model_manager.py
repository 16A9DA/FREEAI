import typer
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TransferSpeedColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from freecode import ollama_client
from freecode.config import load_config, save_config

app = typer.Typer(help="Pull, list, use, remove local models.")
console = Console()


def _human(size):
    gb = size / 1e9
    return f"{gb:.1f} GB" if gb >= 1 else f"{size / 1e6:.0f} MB"


@app.command("list")
def list_cmd():
    """Show locally pulled models."""
    cfg = load_config()
    active = cfg.get("active_model")
    table = Table(title="Local models")
    table.add_column("name", style="cyan")
    table.add_column("size", justify="right")
    table.add_column("active", justify="center")
    for m in ollama_client.list_models_detailed():
        table.add_row(m["name"], _human(m["size"]), "*" if m["name"] == active else "")
    console.print(table)


@app.command()
def pull(name: str = typer.Argument(None)):
    """Pull a model and stream download progress."""
    name = name or Prompt.ask("Model name")
    columns = (TextColumn("[bold]{task.description}"), BarColumn(), DownloadColumn(), TransferSpeedColumn())
    with Progress(*columns, console=console) as prog:
        task = prog.add_task(name, total=None)
        for chunk in ollama_client.pull_model(name):
            status, completed, total = chunk.get("status", ""), chunk.get("completed"), chunk.get("total")
            if total:
                prog.update(task, total=total, completed=completed or 0, description=f"{name} {status}")
            else:
                prog.update(task, description=f"{name} {status}")
    cfg = load_config()
    if name not in cfg["pulled_models"]:
        cfg["pulled_models"].append(name)
    save_config(cfg)
    console.print(f"[green]Pulled {name}[/green]")


@app.command()
def use(name: str):
    """Set the active model."""
    cfg = load_config()
    cfg["active_model"] = name
    save_config(cfg)
    console.print(f"[green]Active model is now {name}[/green]")


@app.command()
def remove(name: str):
    """Delete a local model."""
    if not Confirm.ask(f"Delete {name}?", default=False):
        console.print("Cancelled.")
        return
    ollama_client.delete_model(name)
    cfg = load_config()
    if name in cfg["pulled_models"]:
        cfg["pulled_models"].remove(name)
    if cfg.get("active_model") == name:
        cfg["active_model"] = None
    save_config(cfg)
    console.print(f"[green]Removed {name}[/green]")
