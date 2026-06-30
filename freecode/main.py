import re
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from freecode import agent, assistance, model_manager, ollama_client, parser, planner, rag, skills
from freecode.config import ASSISTANCE_LEVELS, load_config, save_config

_SWITCH = re.compile(r"^(?:switch model to|model)\s+(\S+)$", re.I)
_ASSIST = re.compile(r"^assistance\s+(\w+)$", re.I)

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
    level = cfg.get("assistance_level", "full")
    console.print(f"Active model: [bold]{model}[/bold]   Assistance: [bold]{level}[/bold]")
    if skills.bootstrap_skills():
        console.print("[green]Created ~/.freecode/skills/ with an example skill.[/green]")
    if parser.load_skills():
        console.print("[green]Project skills active (.freeai)[/green]")
    task_loop(model)


def _build_index(cwd):
    if rag.EMBED_MODEL not in ollama_client.list_models():
        console.print(
            f"[yellow]{rag.EMBED_MODEL} not pulled. Run `aimodel pull {rag.EMBED_MODEL}` then "
            "`aiindex`. Continuing with @ mentions only.[/yellow]"
        )
        return False
    try:
        with console.status("[cyan]Indexing project...[/cyan]"):
            n = rag.embed_project(cwd)
        console.print(f"[green]Indexed {n} file(s).[/green]")
        return True
    except Exception as e:
        console.print(f"[yellow]Indexing failed: {e}. Continuing with @ mentions only.[/yellow]")
        return False


def _inject_retrieval(task, cwd):
    try:
        chunks = rag.search_relevant_chunks(task, cwd)
    except Exception as e:
        console.print(f"[dim]Retrieval skipped: {e}[/dim]")
        return task
    if not chunks:
        return task
    files = sorted({c["file"] for c in chunks})
    console.print(f"[blue]Retrieved context from: {', '.join(files)}[/blue]")
    blocks = "\n\n".join(
        f"### {c['file']} (lines {c['start']}-{c['end']})\n{c['content']}" for c in chunks
    )
    return (
        task
        + "\n\n## Automatically retrieved context (found by search, not referenced by the user)\n\n"
        + blocks
    )


def task_loop(model):
    cwd = Path.cwd()
    rag_on = rag.has_index(cwd)
    asked = rag_on
    level = load_config().get("assistance_level", "full")
    while True:
        task = console.input("\n[bold cyan]task>[/bold cyan] ").strip()
        if task.lower() in {"exit", "quit", ""}:
            console.print("Bye.")
            break
        if (m := _SWITCH.match(task)):
            model_manager.use(m.group(1))
            model = load_config().get("active_model") or model
            continue
        if (m := _ASSIST.match(task)):
            new = m.group(1).lower()
            if new not in ASSISTANCE_LEVELS:
                console.print(f"[red]Invalid level. Choose: {', '.join(ASSISTANCE_LEVELS)}.[/red]")
                continue
            level = new
            cfg = load_config()
            cfg["assistance_level"] = level
            save_config(cfg)
            console.print(f"[green]Assistance level is now {level}.[/green]")
            continue
        if not asked:
            asked = True
            if Confirm.ask(
                "Build a search index for this project? Enables automatic relevant-file "
                "detection for future tasks.",
                default=False,
            ):
                rag_on = _build_index(cwd)
        if rag_on:
            task = _inject_retrieval(task, cwd)
        task = parser.parse_mentions(task, model)
        with console.status("[cyan]Matching skills...[/cyan]"):
            matched, skill_prompt = skills.skills_for_task(task, model)
        if matched:
            console.print(f"[magenta]Skills active: {', '.join(matched)}[/magenta]")
        profile = assistance.get_assistance_profile(level)
        extra_system = "\n\n".join(p for p in (assistance.system_prefix(level), skill_prompt) if p)
        with console.status("[cyan]Planning...[/cyan]"):
            steps = planner.generate_plan(task, model, extra_system=extra_system)
        if not steps:
            console.print("[yellow]No plan produced. Try rephrasing.[/yellow]")
            continue
        body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        console.print(Panel(body, title="Plan", border_style="cyan"))
        if Confirm.ask("Approve this plan?", default=True):
            agent.run(steps, model, extra_system=extra_system,
                      compression=profile["compression_aggressiveness"])
        else:
            console.print("[dim]Refine your task and try again.[/dim]")
