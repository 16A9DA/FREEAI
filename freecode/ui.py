import difflib
from contextlib import contextmanager

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.console import Console
from rich.table import Table
from rich.text import Text

from freecode import responsive

console = Console()


def select(prompt, options, horizontal=True, default=0):
    idx = [default]

    def render():
        parts = [("bold", prompt + ("   " if horizontal else "\n"))]
        for i, opt in enumerate(options):
            hot = i == idx[0]
            if horizontal:
                parts.append(("reverse" if hot else "class:dim", f" {opt} "))
                parts.append(("", "  "))
            else:
                parts.append(("reverse" if hot else "class:dim",
                              f"{'> ' if hot else '  '}{opt}"))
                parts.append(("", "\n"))
        return parts

    kb = KeyBindings()
    prev, nxt = ("left", "right") if horizontal else ("up", "down")

    @kb.add(prev)
    def _(e):
        idx[0] = (idx[0] - 1) % len(options)

    @kb.add(nxt)
    def _(e):
        idx[0] = (idx[0] + 1) % len(options)

    @kb.add("enter")
    def _(e):
        e.app.exit(result=idx[0])

    @kb.add("c-c")
    def _(e):
        e.app.exit(result=default)

    app = Application(
        layout=Layout(HSplit([Window(
            FormattedTextControl(render),
            height=1 if horizontal else len(options) + 1,
        )])),
        key_bindings=kb,
    )
    return app.run()


def ask_yes_no(question, default=False):
    """Horizontal yes/no picker. Returns bool."""
    return select(question, ["yes", "no"], default=0 if default else 1) == 0


STATE = {"model": "", "level": "", "tokens": 0, "editing": None}

_ALLOW = set()


def confirm(question, category, default=False):
    """y/n confirm with 'a' = allow this category for rest of session."""
    if category in _ALLOW:
        return True
    choice = select(question, ["yes", "no", "allow all this session"],
                    default=0 if default else 1)
    if choice == 2:
        _ALLOW.add(category)
        return True
    return choice == 0


def _unified(path, old, new):
    """Single-column diff for narrow terminals: -/+ lines stacked, so text stays
    readable instead of two columns squeezed too thin to read."""
    table = Table(title=f"diff: {path}", expand=True, show_header=False)
    table.add_column("diff", overflow="fold")
    for line in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm=""):
        if line.startswith(("+++", "---")):
            continue
        if line.startswith("+"):
            table.add_row(Text(line, style="green"))
        elif line.startswith("-"):
            table.add_row(Text(line, style="red"))
        elif line.startswith("@@"):
            table.add_row(Text(line, style="cyan"))
        else:
            table.add_row(Text(line, style="dim"))
    return table


def side_by_side(path, old, new):
    """Two-column diff on wide terminals, stacked unified diff when narrow."""
    if responsive.is_narrow():
        return _unified(path, old, new)
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
    narrow = responsive.is_narrow()  # drop level + thousands separator when tight
    if STATE["editing"]:
        left = f"editing: {STATE['editing']}"
    elif narrow:
        left = STATE["model"]
    else:
        left = f"{STATE['model']} · {STATE['level']}"
    tokens = f"{STATE['tokens']}" if narrow else f"{STATE['tokens']:,}"
    return f" {left}    tokens: {tokens} "


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
