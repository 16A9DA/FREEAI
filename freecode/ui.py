"""Shared UI: collapse/expand, 4-state phase spinner, and the ambient status bar."""
from contextlib import contextmanager

from rich.console import Console

console = Console()

# Ambient session state shown in the bottom status bar and spinner labels.
STATE = {"model": "", "level": "", "tokens": 0, "editing": None}


def set_context(model, level):
    STATE["model"], STATE["level"] = model, level


def add_tokens(n):
    STATE["tokens"] += n


def set_editing(path):
    STATE["editing"] = path


def bottom_toolbar():
    left = f"editing: {STATE['editing']}" if STATE["editing"] else f"{STATE['model']} · {STATE['level']}"
    return f" {left}    tokens: {STATE['tokens']:,} "


@contextmanager
def phase(label):
    """One animated spinner; label is one of Learning / Thinking / Planning / Working."""
    with console.status(f"[cyan]{label}[/cyan]"):
        yield


def expandable(label, render_body, force=False):
    if force:
        render_body()
        return
    console.print(f"{label} [dim]— press e + enter to expand[/dim]")
    try:
        resp = input()
    except EOFError:
        resp = ""
    if resp.strip().lower() == "e":
        render_body()
