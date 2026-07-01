from rich.console import Console

console = Console()


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
