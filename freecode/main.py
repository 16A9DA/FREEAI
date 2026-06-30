import re

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from freecode import agent, model_manager, ollama_client, parser, planner, skills
from freecode.config import load_config

_SWITCH = re.compile(r"^(?:switch model to|model)\s+(\S+)$", re.I)

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
    if skills.bootstrap_skills():
        console.print("[green]Created ~/.freecode/skills/ with an example skill.[/green]")
    if parser.load_skills():
        console.print("[green]Project skills active (.freeai)[/green]")
    task_loop(model)


def task_loop(model):
    while True:
        task = console.input("\n[bold cyan]task>[/bold cyan] ").strip()
        if task.lower() in {"exit", "quit", ""}:
            console.print("Bye.")
            break
        if (m := _SWITCH.match(task)):
            model_manager.use(m.group(1))
            model = load_config().get("active_model") or model
            continue
        task = parser.parse_mentions(task, model)
        with console.status("[cyan]Matching skills...[/cyan]"):
            matched, skill_prompt = skills.skills_for_task(task, model)
        if matched:
            console.print(f"[magenta]Skills active: {', '.join(matched)}[/magenta]")
        with console.status("[cyan]Planning...[/cyan]"):
            steps = planner.generate_plan(task, model, extra_system=skill_prompt)
        if not steps:
            console.print("[yellow]No plan produced. Try rephrasing.[/yellow]")
            continue
        body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        console.print(Panel(body, title="Plan", border_style="cyan"))
        if Confirm.ask("Approve this plan?", default=True):
            agent.run(steps, model, extra_system=skill_prompt)
        else:
            console.print("[dim]Refine your task and try again.[/dim]")
