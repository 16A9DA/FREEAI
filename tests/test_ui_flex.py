"""Guard: diff view flexes with terminal width. Narrow stacks a single-column
unified diff so text stays readable; wide keeps two columns."""
from rich.console import Console

import freecode.ui as ui
from freecode import responsive


def _render(width):
    responsive.get_terminal_width = lambda: width
    con = Console(width=width, record=True)
    con.print(ui.side_by_side("x.py", "a\nb\nc", "a\nB\nc"))
    return con.export_text()


def test_narrow_stacks_unified():
    out = _render(50)
    assert "-b" in out and "+B" in out  # unified -/+ markers present


def test_wide_two_columns():
    out = _render(120)
    assert "old" in out and "new" in out  # two-column headers present


if __name__ == "__main__":
    test_narrow_stacks_unified()
    test_wide_two_columns()
    print("ok")
