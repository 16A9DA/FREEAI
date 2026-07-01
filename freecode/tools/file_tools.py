import os
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from freecode import ui
from freecode.ui import expandable

console = Console()


def read_file(path):
    p = Path.cwd() / path
    if not p.is_file():
        return f"Error: no file at {path}"
    return p.read_text()


def _show_diff(path, old, new, force=False):
    if old is None:
        expandable(f"[green]+ new file: {path}[/green]", lambda: console.print(new), force=force)
        return
    if old == new:
        return
    expandable(f"diff: {path}", lambda: console.print(ui.side_by_side(path, old, new)), force=force)


def write_file(path, content):
    p = Path.cwd() / path
    ui.set_editing(path)
    try:
        if p.exists():
            old = p.read_text()
            _show_diff(path, old, content)
            if not ui.confirm(f"Overwrite existing {path}?", "overwrite"):
                return f"Cancelled: {path} not overwritten"
        else:
            _show_diff(path, None, content)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Wrote {path}"
    finally:
        ui.set_editing(None)


def create_file(path, content):
    p = Path.cwd() / path
    if p.exists():
        return f"Error: {path} already exists"
    ui.set_editing(path)
    try:
        _show_diff(path, None, content)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Created {path}"
    finally:
        ui.set_editing(None)


def delete_file(path):
    p = Path.cwd() / path
    if not p.exists():
        return f"Error: no file at {path}"
    ui.set_editing(path)
    try:
        _show_diff(path, p.read_text(errors="replace"), "", force=True)
        if not Confirm.ask(f"Delete {path}?", default=False):
            return f"Cancelled: {path} not deleted"
        p.unlink()
        return f"Deleted {path}"
    finally:
        ui.set_editing(None)


def search_in_files(query, directory="."):
    root = Path.cwd() / directory
    matches = []
    for dirpath, _, files in os.walk(root):
        for name in files:
            fp = Path(dirpath) / name
            try:
                lines = fp.read_text().splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(lines, 1):
                if query in line:
                    rel = fp.relative_to(Path.cwd())
                    matches.append((str(rel), n, line.strip()))
    table = Table(title=f"search: {query}")
    table.add_column("file", style="cyan")
    table.add_column("line", justify="right")
    table.add_column("match")
    for rel, n, line in matches:
        table.add_row(rel, str(n), line)
    console.print(table)
    if not matches:
        return f"No matches for '{query}'"
    return "\n".join(f"{rel}:{n}: {line}" for rel, n, line in matches)
