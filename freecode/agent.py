import json

from rich.console import Console

from freecode import ollama_client
from freecode.tools import browser_tool, file_tools, git_tool, shell_tool, web_tool

console = Console()

# Tool registry: name -> callable. Filled by tool modules in Day 4+.
TOOLS = {
    "read_file": file_tools.read_file,
    "write_file": file_tools.write_file,
    "create_file": file_tools.create_file,
    "delete_file": file_tools.delete_file,
    "search_in_files": file_tools.search_in_files,
    "run_command": shell_tool.run_command,
    "git_status": git_tool.git_status,
    "git_diff": git_tool.git_diff,
    "git_add": git_tool.git_add,
    "git_commit": git_tool.git_commit,
    "git_push": git_tool.git_push,
    "git_log": git_tool.git_log,
    "web_search": web_tool.web_search,
    "fetch_page": browser_tool.fetch_page,
}

MAX_ITERS = 8

AGENT_SYSTEM = (
    "You are freeai, a coding agent executing a plan one step at a time. "
    "You may call tools. To call a tool, respond with ONLY a JSON object: "
    '{"tool": "<name>", "args": {<arguments>}}. After a tool result is given, '
    'continue or finish. When the current step is complete, respond with ONLY '
    '{"done": true}. Output JSON only, no prose.'
)


def _parse_call(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None
        return None


def run(steps, model):
    history = [{"role": "system", "content": AGENT_SYSTEM}]
    for i, step in enumerate(steps, 1):
        console.print(f"\n[bold]Step {i}/{len(steps)}[/bold] {step}")
        history.append({"role": "user", "content": f"Execute step {i}: {step}"})
        for _ in range(MAX_ITERS):
            reply = "".join(ollama_client.chat(model, history, stream=False))
            history.append({"role": "assistant", "content": reply})
            call = _parse_call(reply)
            if call is None:
                console.print("[yellow]No valid JSON from model; moving on.[/yellow]")
                break
            if call.get("done"):
                console.print("[green]Step done.[/green]")
                break
            name, args = call.get("tool"), call.get("args", {})
            fn = TOOLS.get(name)
            if fn is None:
                result = f"Error: unknown tool '{name}'"
                console.print(f"[red]{result}[/red]")
            else:
                console.print(f"[cyan]call[/cyan] {name}({args})")
                try:
                    result = fn(**args)
                except Exception as e:
                    result = f"Error: {e}"
            history.append({"role": "user", "content": f"Tool result: {result}"})
        else:
            console.print("[yellow]Step hit iteration cap.[/yellow]")
