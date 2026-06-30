import json
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TransferSpeedColumn
from rich.prompt import Confirm, Prompt

OLLAMA = "http://localhost:11434"
CONFIG_PATH = Path.home() / ".freecode" / "config.json"
DEFAULTS = {"active_model": None, "pulled_models": []}

STARTER_MODELS = [
    {"name": "qwen2.5-coder:7b", "size": "~4.7 GB", "use": "main coding model"},
    {"name": "llama3.2:3b", "size": "~2.0 GB", "use": "lightweight fast model"},
    {"name": "deepseek-r1:7b", "size": "~4.7 GB", "use": "reasoning model"},
]

console = Console()


def load_config():
    if CONFIG_PATH.exists():
        return {**DEFAULTS, **json.loads(CONFIG_PATH.read_text())}
    return {k: (v.copy() if isinstance(v, list) else v) for k, v in DEFAULTS.items()}


def save_config(data):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def check_ollama():
    try:
        httpx.get(OLLAMA, timeout=2.0)
        return True
    except httpx.HTTPError:
        return False


def parse_chunk(line):
    """One /api/pull JSON line -> (status, completed, total). Bytes None if absent."""
    data = json.loads(line)
    return data.get("status", ""), data.get("completed"), data.get("total")


def pull_model(name):
    with httpx.stream("POST", f"{OLLAMA}/api/pull", json={"name": name}, timeout=None) as r:
        r.raise_for_status()
        columns = (
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        )
        with Progress(*columns, console=console) as prog:
            task = prog.add_task(name, total=None)
            for line in r.iter_lines():
                if not line:
                    continue
                status, completed, total = parse_chunk(line)
                if total:
                    prog.update(task, total=total, completed=completed or 0, description=f"{name} {status}")
                else:
                    prog.update(task, description=f"{name} {status}")


def choose_models():
    console.print("[bold]Starter models[/bold]")
    for i, m in enumerate(STARTER_MODELS, 1):
        console.print(f"  {i}. {m['name']}  {m['size']}  {m['use']}")
    console.print("  a. all")
    raw = Prompt.ask("Pick numbers (comma separated) or 'a'")
    if raw.strip().lower() == "a":
        return list(STARTER_MODELS)
    picks = []
    for tok in raw.replace(",", " ").split():
        if tok.isdigit() and 1 <= int(tok) <= len(STARTER_MODELS):
            picks.append(STARTER_MODELS[int(tok) - 1])
    return picks


def main():
    if not check_ollama():
        console.print("[red]Ollama not running at localhost:11434. Start it with `ollama serve`.[/red]")
        sys.exit(1)
    cfg = load_config()
    picks = choose_models()
    if not picks:
        console.print("Nothing picked.")
        return
    for m in picks:
        name = m["name"]
        try:
            pull_model(name)
        except httpx.HTTPError as e:
            console.print(f"[red]Pull failed for {name}: {e}[/red]")
            continue
        if name not in cfg["pulled_models"]:
            cfg["pulled_models"].append(name)
        save_config(cfg)  # persist after each model finishes
        if Confirm.ask(f"Set {name} as your default model?", default=False):
            cfg["active_model"] = name
            save_config(cfg)
    console.print(f"[green]Done. Active model: {cfg['active_model']}[/green]")


if __name__ == "__main__":
    main()
