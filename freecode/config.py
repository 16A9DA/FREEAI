import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

CONFIG_PATH = Path.home() / ".freecode" / "config.json"
DEFAULTS = {"active_model": None, "pulled_models": [], "settings": {}}

app = typer.Typer(help="Show and set config values.")
console = Console()


def load_config():
    if CONFIG_PATH.exists():
        return {**DEFAULTS, **json.loads(CONFIG_PATH.read_text())}
    return {k: (v.copy() if isinstance(v, (list, dict)) else v) for k, v in DEFAULTS.items()}


def save_config(data):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


@app.callback(invoke_without_command=True)
def main(
    model: str = typer.Option(None, help="Set active model."),
    temperature: float = typer.Option(None, help="Set sampling temperature."),
    context: int = typer.Option(None, help="Set context window size."),
):
    cfg = load_config()
    changed = False
    if model is not None:
        cfg["active_model"] = model
        changed = True
    if temperature is not None:
        cfg["settings"]["temperature"] = temperature
        changed = True
    if context is not None:
        cfg["settings"]["context"] = context
        changed = True
    if changed:
        save_config(cfg)
        console.print("[green]Config updated.[/green]")
    table = Table(title="Config")
    table.add_column("key", style="cyan")
    table.add_column("value")
    table.add_row("active_model", str(cfg.get("active_model")))
    table.add_row("pulled_models", ", ".join(cfg.get("pulled_models", [])) or "-")
    for k, v in cfg.get("settings", {}).items():
        table.add_row(f"settings.{k}", str(v))
    console.print(table)
