import re
from pathlib import Path

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

from freecode import (
    agent, assistance, clear, commands, config, history, model_manager,
    ollama_client, parser, planner, rag, skills, ui,
)
from freecode.config import ASSISTANCE_LEVELS, load_config, save_config

GITHUB_URL = "https://github.com/16A9DA/FREEAI"

_SWITCH = re.compile(r"^switch model to\s+(\S+)$", re.I)
_ASSIST = re.compile(r"^(?:assistance|mode)\s+(\w+)$", re.I)
_HISTORY_FILE = str(Path.home() / ".freecode" / "prompt_history")

app = typer.Typer(help="freeai local AI coding assistant.")
console = Console()

LOGO = r"""
 _____ ____  _____ _____    _    ___
|  ___|  _ \| ____| ____|  / \  |_ _|
| |_  | |_) |  _| |  _|   / _ \  | |
|  _| |  _ <| |___| |___ / ___ \ | |
|_|   |_| \_\_____|_____/_/   \_\___|
"""

app.add_typer(model_manager.app, name="model")
app.command("config")(config.main)
app.command("history")(history.main)
app.command("clear")(clear.main)
app.command("index")(rag.main)


_COMMANDS = [
    ("(no command)", "Open the welcome screen and start the task prompt."),
    ("help", "Show this command list."),
    ("model list|pull|use|remove", "Download, list, switch, and remove local models."),
    ("config", "View or change settings (--assistance, --model, --temperature, --context)."),
    ("history", "Show past tasks."),
    ("clear", "Erase the saved session memory."),
    ("index", "Build or refresh the search index for the current project."),
]


def _print_help():
    console.print(LOGO, style="white")
    console.print("freeai is a local AI coding assistant that runs entirely on your machine via Ollama.")
    console.print("Describe a task, approve the plan, and watch it run step by step.\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Command")
    table.add_column("Description")
    for name, desc in _COMMANDS:
        table.add_row(f"freeai {name}".strip(), desc)
    console.print(table)
    console.print(f"\n{GITHUB_URL}")


@app.command("help")
def help_cmd():
    """List every freeai command."""
    _print_help()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, help_: bool = typer.Option(False, "-help", help="List every freeai command.")):
    if help_:
        _print_help()
        raise typer.Exit()
    if ctx.invoked_subcommand is not None:
        return
    if not ollama_client.check_running():
        console.print(
            "[red]Ollama not running at localhost:11434. Start it with `ollama serve`.[/red]"
        )
        raise typer.Exit(1)
    cfg = load_config()
    model = cfg.get("active_model")
    console.print(LOGO, style="white")
    if not model:
        console.print("[yellow]No active model set. Run `freeai model pull <name>` to get one.[/yellow]")
        raise typer.Exit(0)
    pulled = cfg.get("pulled_models", [])
    if not ollama_client.is_model_pulled(model, pulled):
        console.print(
            f"[red]Configured active model '{model}' is not among pulled models: "
            f"{', '.join(pulled) or '(none)'}.[/red]"
        )
        choices = [p for p in pulled if not ollama_client.is_embedding_model(p, cfg.get("known_embedding_models", []))]
        if not choices:
            console.print("[yellow]No chat model pulled. Run `freeai model pull <name>`.[/yellow]")
            raise typer.Exit(1)
        model = Prompt.ask("Pick a model to use", choices=choices)
        cfg["active_model"] = model
        save_config(cfg)
    level = cfg.get("assistance_level", "full")
    console.print(f"Active model: [bold]{model}[/bold]   Assistance: [bold]{level}[/bold]")
    console.print("[dim]Defaults: headroom (compresses tool output) · caveman (terse replies) · "
                  "ponytail (minimal code)[/dim]")
    console.print("[dim]Type `freeai -help` to list all commands.[/dim]")
    if skills.bootstrap_skills():
        console.print("[green]Created ~/.freecode/skills/ with an example skill.[/green]")
    if parser.load_skills():
        console.print("[green]Project skills active (.freeai)[/green]")
    task_loop(model)


def _build_index(cwd):
    if not ollama_client.is_model_pulled(rag.EMBED_MODEL, ollama_client.list_models()):
        console.print(
            f"[yellow]{rag.EMBED_MODEL} not pulled. Run `freeai model pull {rag.EMBED_MODEL}` then "
            "`freeai index`. Continuing with @ mentions only.[/yellow]"
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
    table = Table(title="Retrieved context (headroom-compressed)")
    table.add_column("file", style="cyan")
    table.add_column("lines", justify="right")
    table.add_column("type")
    table.add_column("saved", justify="right")
    for c in chunks:
        saved = (c["raw_len"] - len(c["content"])) // 4  # ~4 chars per token
        table.add_row(c["file"], f"{c['start']}-{c['end']}", c.get("type", "-"),
                      f"{c['ratio']:.0%} (~{saved} tok)")
    console.print(table)
    blocks = "\n\n".join(
        f"### {c['file']} (lines {c['start']}-{c['end']})\n{c['content']}" for c in chunks
    )
    return (
        task
        + "\n\n## Automatically retrieved context (found by search, not referenced by the user)\n\n"
        + blocks
    )


def _run_builtin(cmd):
    """Run a built-in command typed at the task prompt. Returns True if handled."""
    parts = cmd.split()
    if not parts:
        return False
    name, rest = parts[0].lower(), parts[1:]
    if name == "help":
        _print_help()
    elif name == "history":
        history.main()
    elif name == "clear":
        clear.main(history="--history" in rest)
    elif name == "model":
        sub = rest[0].lower() if rest else "list"
        if sub == "list":
            model_manager.list_cmd()
        elif sub in {"pull", "use", "remove"} and len(rest) > 1:
            getattr(model_manager, sub)(rest[1])
        else:
            model_manager.use(rest[0])
    else:
        return False
    return True


def task_loop(model):
    cwd = Path.cwd()
    rag_on = rag.has_index(cwd)
    asked = rag_on
    level = load_config().get("assistance_level", "full")
    ui.set_context(model, level)
    kb = KeyBindings()

    @kb.add("s-right")
    def _accept_suggestion(event):
        buf = event.current_buffer
        if buf.suggestion:
            buf.insert_text(buf.suggestion.text)

    Path(_HISTORY_FILE).parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(
        completer=commands.CommandCompleter(), complete_while_typing=True,
        auto_suggest=AutoSuggestFromHistory(), history=FileHistory(_HISTORY_FILE),
        key_bindings=kb, bottom_toolbar=ui.bottom_toolbar,
    )
    while True:
        task = session.prompt("task> ").strip()
        if task.lower() in {"exit", "quit", "", "/done"}:
            console.print("Bye.")
            break
        # Built-in commands run directly: no plan, no approval gate.
        cmd = task.lstrip("/").strip()
        if cmd.split(" ", 1)[0].lower() == "index":
            asked = True
            rag_on = _build_index(cwd)
            continue
        if _run_builtin(cmd):
            model = load_config().get("active_model") or model
            ui.set_context(model, level)
            continue
        if (m := _SWITCH.match(task)):
            model_manager.use(m.group(1))
            model = load_config().get("active_model") or model
            ui.set_context(model, level)
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
            ui.set_context(model, level)
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
        with ui.phase("Learning"):
            if rag_on:
                task = _inject_retrieval(task, cwd)
            task = parser.parse_mentions(task, model)
            matched, skill_prompt = skills.skills_for_task(task, model)
        if matched:
            console.print(f"[magenta]Skills active: {', '.join(matched)}[/magenta]")
        profile = assistance.get_assistance_profile(level)
        extra_system = "\n\n".join(p for p in (assistance.system_prefix(level), skill_prompt) if p)
        with ui.phase("Thinking"):
            steps = planner.generate_plan(task, model, extra_system=extra_system)
        if not steps:
            console.print("[yellow]No plan produced. Try rephrasing.[/yellow]")
            continue
        body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        ui.expandable("Plan ready", lambda: console.print(Panel(body, title="Plan", border_style="cyan")))
        if ui.confirm("Approve this plan?", "plan", default=True):
            known_embed = load_config().get("known_embedding_models", [])
            step_usage = agent.run(steps, model, extra_system=extra_system,
                                    compression=profile["compression_aggressiveness"],
                                    known_embedding_models=known_embed)
            history.append_session(task, step_usage)
        else:
            console.print("[dim]Refine your task and try again.[/dim]")
