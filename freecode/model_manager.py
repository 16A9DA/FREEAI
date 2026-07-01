import typer
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TransferSpeedColumn
from rich.prompt import Prompt
from rich.table import Table

from freecode import ollama_client, responsive, ui
from freecode.config import load_config, save_config

app = typer.Typer(help="Pull, list, use, remove local models.")
console = Console()


def _human(size):
    gb = size / 1e9
    return f"{gb:.1f} GB" if gb >= 1 else f"{size / 1e6:.0f} MB"


@app.command("list")
def list_cmd():
    """Show locally pulled models, split by chat vs embedding."""
    cfg = load_config()
    active = cfg.get("active_model")
    known_embed = cfg.get("known_embedding_models", [])
    models = ollama_client.list_models_detailed()
    chat_models = [m for m in models if not ollama_client.is_embedding_model(m["name"], known_embed)]
    embed_models = [m for m in models if ollama_client.is_embedding_model(m["name"], known_embed)]

    narrow = responsive.is_narrow()  # drop size column, keep name + active marker
    table = Table(title="Chat models")
    table.add_column("name", style="cyan", overflow="fold")
    if not narrow:
        table.add_column("size", justify="right")
    table.add_column("active", justify="center")
    for m in chat_models:
        marker = "*" if m["name"] == active else ""
        row = [m["name"]] if narrow else [m["name"], _human(m["size"])]
        table.add_row(*row, marker)
    console.print(table)

    if embed_models:
        etable = Table(title="Embedding models")
        etable.add_column("name", style="cyan", overflow="fold")
        if not narrow:
            etable.add_column("size", justify="right")
        for m in embed_models:
            etable.add_row(m["name"], *([] if narrow else [_human(m["size"])]))
        console.print(etable)


@app.command()
def pull(name: str = typer.Argument(None)):
    """Pull a model and stream download progress."""
    name = name or Prompt.ask("Model name")
    if ollama_client.is_model_pulled(name, ollama_client.list_models()):
        console.print(f"[yellow]{name} already pulled.[/yellow]")
    else:
        columns = (TextColumn("[bold]{task.description}"), BarColumn(), DownloadColumn(), TransferSpeedColumn())
        with Progress(*columns, console=console) as prog:
            task = prog.add_task(name, total=None)
            for chunk in ollama_client.pull_model(name):
                status, completed, total = chunk.get("status", ""), chunk.get("completed"), chunk.get("total")
                if total:
                    prog.update(task, total=total, completed=completed or 0, description=f"{name} {status}")
                else:
                    prog.update(task, description=f"{name} {status}")
        console.print(f"[green]Pulled {name}[/green]")
    cfg = load_config()
    if name not in cfg["pulled_models"]:
        cfg["pulled_models"].append(name)
    if ui.ask_yes_no(f"Set {name} as your default model?", default=True):
        cfg["active_model"] = name
    save_config(cfg)


@app.command()
def use(name: str):
    """Set the active model."""
    cfg = load_config()
    known_embed = cfg.get("known_embedding_models", [])
    if ollama_client.is_embedding_model(name, known_embed):
        console.print(f"[red]{name} is an embedding-only model and cannot be used for chat.[/red]")
        return
    if not ollama_client.is_model_pulled(name, cfg["pulled_models"]):
        console.print(f"[yellow]{name} is not pulled yet.[/yellow]")
        if Confirm.ask(f"Pull {name} now?", default=True):
            pull(name)
        return
    cfg["active_model"] = name
    save_config(cfg)
    console.print(f"[green]model → {name}[/green]")


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
        console.print("[yellow]That was your active model. Pick a new default with `freeai model use <name>`.[/yellow]")
    save_config(cfg)
    console.print(f"[green]Removed {name}[/green]")
