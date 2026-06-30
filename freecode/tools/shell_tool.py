
import subprocess
import threading
import shlex
import os
import time
from rich.console import Console
from rich.prompt import Confirm

console = Console()

# ── Destructive keywords ────────────────────────────────────────
# Any command containing these requires user confirmation.
DESTRUCTIVE = {
    "rm ", "rm -", "rmdir", "del ",
    "format", "mkfs", "dd ", "truncate",
    "chmod 777", "sudo rm", "> /dev",
    "drop table", "drop database",
}

# ── Server / long-running command patterns ──────────────────────
# These never return on their own — spawn as background process.
SERVER_PATTERNS = {
    "http.server",
    "flask run",
    "uvicorn",
    "gunicorn",
    "django",
    "manage.py runserver",
    "npm run dev",
    "npm start",
    "yarn dev",
    "yarn start",
    "vite",
    "next dev",
    "nodemon",
    "live-server",
    "serve ",
    "php -S",
    "ruby -run",
    "rails server",
    "rails s",
}

# Registry of background processes so the agent can stop them later
_background_procs: dict[str, subprocess.Popen] = {}


def _is_destructive(command: str) -> bool:
    low = command.lower()
    return any(kw in low for kw in DESTRUCTIVE)


def _is_server(command: str) -> bool:
    low = command.lower()
    return any(pattern in low for pattern in SERVER_PATTERNS)


def _infer_port(command: str) -> int:
    """
    Best-effort port detection from the command string.
    Falls back to 8000 for http.server, 5000 for flask/uvicorn, 3000 otherwise.
    """
    import re
    # explicit --port or -p flag
    match = re.search(r'(?:--port|-p)\s+(\d+)', command)
    if match:
        return int(match.group(1))

    low = command.lower()
    if "http.server" in low:
        # python -m http.server [PORT]
        nums = re.findall(r'\b(\d{4,5})\b', command)
        return int(nums[-1]) if nums else 8000
    if any(x in low for x in ("flask", "uvicorn", "gunicorn")):
        return 5000
    if any(x in low for x in ("next", "vite", "nodemon", "npm", "yarn")):
        return 3000
    return 8000


def run_command(command: str, cwd: str | None = None) -> dict:
    """
    Execute a shell command from the agent loop.

    Returns a dict the agent feeds back into context:
      {
        "status":  "ok" | "error" | "cancelled" | "background",
        "output":  str,
        "exit_code": int | None,
      }
    """
    cwd = cwd or os.getcwd()

    # ── Destructive guard ───────────────────────────────────────
    if _is_destructive(command):
        console.print(f"\n[bold red]Destructive command:[/bold red] {command}")
        if not Confirm.ask("Run it?", default=False):
            return {"status": "cancelled", "output": "User cancelled.", "exit_code": None}

    # ── Server / long-running ───────────────────────────────────
    if _is_server(command):
        return _run_server(command, cwd)

    # ── Normal command ──────────────────────────────────────────
    return _run_normal(command, cwd)


def _run_normal(command: str, cwd: str) -> dict:
    """Run command, stream output line by line, return when done."""
    try:
        proc = subprocess.Popen(
            shlex.split(command),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        lines = []
        for line in proc.stdout:
            line = line.rstrip()
            console.print(f"[dim]{line}[/dim]")
            lines.append(line)

        proc.wait()
        output = "\n".join(lines)

        if proc.returncode != 0:
            return {"status": "error", "output": output, "exit_code": proc.returncode}
        return {"status": "ok", "output": output, "exit_code": 0}

    except FileNotFoundError:
        msg = f"Command not found: {command.split()[0]}"
        console.print(f"[red]{msg}[/red]")
        return {"status": "error", "output": msg, "exit_code": 127}

    except Exception as e:
        return {"status": "error", "output": str(e), "exit_code": 1}


def _run_server(command: str, cwd: str) -> dict:
    """
    Spawn a server command in the background.

    Returns immediately with the local URL rather than blocking.
    The process keeps running until stop_server() is called or
    freeai exits.
    """
    port = _infer_port(command)
    url  = f"http://localhost:{port}"

    try:
        proc = subprocess.Popen(
            shlex.split(command),
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        msg = f"Command not found: {command.split()[0]}"
        console.print(f"[red]{msg}[/red]")
        return {"status": "error", "output": msg, "exit_code": 127}

    # Give it a moment to bind the port
    time.sleep(1.2)

    if proc.poll() is not None:
        # Process already exited — something went wrong
        return {
            "status": "error",
            "output": f"Server exited immediately. Check the command: {command}",
            "exit_code": proc.returncode,
        }

    # Register so it can be stopped later
    key = command.split()[0]
    _background_procs[key] = proc

    console.print(f"[green]Server running →[/green] [bold]{url}[/bold]")
    console.print(f"[dim]Stop with: freeai stop-server[/dim]")

    return {
        "status": "background",
        "output": f"Server started at {url}",
        "url": url,
        "pid": proc.pid,
        "exit_code": None,
    }


def stop_server(name: str | None = None) -> dict:
    """
    Stop a background server process.
    If name is None, stop all running background processes.
    """
    if not _background_procs:
        return {"status": "ok", "output": "No servers running."}

    targets = (
        {name: _background_procs[name]}
        if name and name in _background_procs
        else dict(_background_procs)
    )

    stopped = []
    for key, proc in targets.items():
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        del _background_procs[key]
        stopped.append(key)

    msg = f"Stopped: {', '.join(stopped)}"
    console.print(f"[yellow]{msg}[/yellow]")
    return {"status": "ok", "output": msg}