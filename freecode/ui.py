import difflib
from contextlib import contextmanager

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

console = Console()


STATE = {"model": "", "level": "", "tokens": 0, "editing": None}

# Categories the user approved for the whole session (memory only; resets each launch).
_ALLOW = set()


def confirm(question, category, default=False):
    """y/n confirm with 'a' = allow this category for rest of session."""
    if category in _ALLOW:
        return True
    ans = Prompt.ask(f"{question} [dim](y/n/a=allow all this session)[/dim]",
                     choices=["y", "n", "a"], default="y" if default else "n")
    if ans == "a":
        _ALLOW.add(category)
        return True
    return ans == "y"


def side_by_side(path, old, new):
    """Rich two-column table: old left, new right, changed rows tinted red/green."""
    table = Table(title=f"diff: {path}", expand=True)
    table.add_column("old", ratio=1, overflow="fold")
    table.add_column("new", ratio=1, overflow="fold")
    old_lines, new_lines = old.splitlines(), new.splitlines()
    sm = difflib.SequenceMatcher(None, old_lines, new_lines)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for a, b in zip(old_lines[i1:i2], new_lines[j1:j2]):
                table.add_row(Text(a, style="dim"), Text(b, style="dim"))
        else:
            left, right = old_lines[i1:i2], new_lines[j1:j2]
            for k in range(max(len(left), len(right))):
                a = Text(left[k], style="red") if k < len(left) else Text("")
                b = Text(right[k], style="green") if k < len(right) else Text("")
                table.add_row(a, b)
    return table


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


def demo():
    t = side_by_side("f.py", "a\nb\nc", "a\nB\nc")
    assert [c.header for c in t.columns] == ["old", "new"]
    _ALLOW.clear()
    _ALLOW.add("shell")
    assert confirm("run?", "shell") is True  # pre-allowed skips prompt
    set_context("m", "full")
    add_tokens(5)
    assert "tokens: 5" in bottom_toolbar()
    print("ok")


if __name__ == "__main__":
    demo()
