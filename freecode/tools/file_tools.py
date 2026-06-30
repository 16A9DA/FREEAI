import os
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

console = Console()


def read_file(path):
    p = Path.cwd() / path
    if not p.is_file():
        return f"Error: no file at {path}"
    return p.read_text()


def write_file(path, content):
    p = Path.cwd() / path
    if p.exists():
        if not Confirm.ask(f"Overwrite existing {path}?", default=False):
            return f"Cancelled: {path} not overwritten"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Wrote {path}"


def create_file(path, content):
    p = Path.cwd() / path
    if p.exists():
        return f"Error: {path} already exists"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Created {path}"


def delete_file(path):
    p = Path.cwd() / path
    if not p.exists():
        return f"Error: no file at {path}"
    if not Confirm.ask(f"Delete {path}?", default=False):
        return f"Cancelled: {path} not deleted"
    p.unlink()
    return f"Deleted {path}"


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
