from ddgs import DDGS
from rich.console import Console
from rich.table import Table

console = Console()


def web_search(query, max_results=5):
    with DDGS() as ddgs:
        hits = ddgs.text(query, max_results=max_results)
    results = [
        {"title": h.get("title", ""), "url": h.get("href", ""), "snippet": h.get("body", "")}
        for h in hits
    ]
    table = Table(title=f"search: {query}")
    table.add_column("title", style="cyan")
    table.add_column("url", style="blue", overflow="fold")
    table.add_column("snippet", overflow="fold")
    for r in results:
        table.add_row(r["title"], r["url"], r["snippet"][:120])
    console.print(table)
    return results
