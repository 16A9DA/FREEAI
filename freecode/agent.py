import inspect
import json

from rich.console import Console
from rich.table import Table

from freecode import defaults, ollama_client, parser, responsive, ui
from freecode.tools import browser_tool, compress, file_tools, git_tool, shell_tool, web_tool

console = Console()

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
    "retrieve_original": compress.retrieve_original,
}

MAX_ITERS = 8

_TOOL_SPEC = "\n".join(
    f"- {name}{inspect.signature(fn)}" for name, fn in TOOLS.items()
)

AGENT_SYSTEM = (
    "You are freeai, a coding agent executing a plan one step at a time.\n\n"
    f"{defaults.CAVEMAN_RULES}\n"
    f"{defaults.HEADROOM_INSTRUCTIONS}\n"
    f"{defaults.PONYTAIL_LADDER}\n"
    "You may call ONLY these tools (use the exact name and argument keys):\n"
    f"{_TOOL_SPEC}\n"
    "To call a tool, respond with ONLY a JSON object: "
    '{"tool": "<name>", "args": {<arguments>}}. Do not invent tool names. '
    "After a tool result is given, continue or finish. When the current step "
    'is complete, respond with ONLY {"done": true}. Output JSON only, no prose.'
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


def run(steps, model, extra_system="", compression="moderate", known_embedding_models=()):
    system = parser.with_skills(AGENT_SYSTEM)
    if extra_system:
        system = extra_system + "\n\n" + system
    history = [{"role": "system", "content": system}]
    step_usage = []  # [(label, prompt_tokens, completion_tokens)]
    total = 0
    warned = False
    for i, step in enumerate(steps, 1):
        console.print(f"\n[bold]Step {i}/{len(steps)}[/bold] {step}")
        history.append({"role": "user", "content": f"Execute step {i}: {step}"})
        prompt_tok = completion_tok = 0
        for _ in range(MAX_ITERS):
            with console.status(f"[cyan]Working[/cyan] · {model} · tokens: {total:,}"):
                reply, usage = ollama_client.chat_with_usage(model, history, known_embedding_models)
            turn_tokens = usage["prompt_tokens"] + usage["completion_tokens"]
            prompt_tok += usage["prompt_tokens"]
            completion_tok += usage["completion_tokens"]
            total += turn_tokens
            ui.add_tokens(turn_tokens)
            history.append({"role": "assistant", "content": reply})
            call = _parse_call(reply)
            if call is None:
                console.print("[yellow]No valid JSON from model; moving on.[/yellow]")
                break
            if call.get("done"):
                console.print("[green]✓ Step done.[/green]")
                break
            name, args = call.get("tool"), call.get("args", {})
            fn = TOOLS.get(name)
            if fn is None:
                result = f"Error: unknown tool '{name}'"
                console.print(f"[red]✗ {result}[/red]")
            else:
                console.print(f"[cyan]call[/cyan] {name}({args})")
                try:
                    result = fn(**args)
                    console.print(f"[green]✓ {name}[/green]")
                except Exception as e:
                    result = f"Error: {e}"
                    console.print(f"[red]✗ {name}: {e}[/red]")
            result = compress.compress_output(result, compression)
            history.append({"role": "user", "content": f"Tool result: {result}"})
        else:
            console.print("[yellow]Step hit iteration cap.[/yellow]")
        step_usage.append((f"step {i}: {step[:40]}", prompt_tok, completion_tok))
        if not warned and len(steps) <= 3 and total > 3000:
            console.print("[yellow]Token usage high for this task's size — consider a "
                          "smaller model or lower assistance level.[/yellow]")
            warned = True
    _print_session_summary(step_usage)
    return step_usage


def _print_session_summary(step_usage):
    if not step_usage:
        return
    narrow = responsive.is_narrow()  # drop prompt/completion split, total only
    table = Table(title="Session token usage")
    table.add_column("step", overflow="fold")
    if not narrow:
        table.add_column("prompt", justify="right")
        table.add_column("completion", justify="right")
    table.add_column("total", justify="right")
    peak_idx = max(range(len(step_usage)), key=lambda i: step_usage[i][1] + step_usage[i][2])
    tp = tc = 0
    for idx, (label, p, c) in enumerate(step_usage):
        tp += p
        tc += c
        style = "bold yellow" if idx == peak_idx else None
        cols = [label] if narrow else [label, f"{p:,}", f"{c:,}"]
        table.add_row(*cols, f"{p + c:,}", style=style)
    total_cols = ["total"] if narrow else ["total", f"{tp:,}", f"{tc:,}"]
    table.add_row(*total_cols, f"{tp + tc:,}", style="bold")
    console.print(table)
    peak_label, pp, pc = step_usage[peak_idx]
    console.print(f"[yellow]peak usage — {peak_label} ({pp + pc:,} tok)[/yellow]")
