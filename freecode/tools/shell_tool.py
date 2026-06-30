import re
import subprocess

from rich.console import Console
from rich.prompt import Confirm

console = Console()

DESTRUCTIVE = [
    "rm", "rmdir", "del", "format", "mkfs", "dd",
    "truncate", "chmod 777", "sudo rm",
]


def _is_destructive(command):
    return any(re.search(rf"\b{re.escape(kw)}\b", command) for kw in DESTRUCTIVE)


def run_command(command):
    if _is_destructive(command):
        console.print(f"[red]Destructive command:[/red] {command}")
        if not Confirm.ask("Run anyway?", default=False):
            return {"exit_code": None, "stdout": "", "stderr": "Cancelled by user"}

    # ponytail: reads stdout live, stderr after exit. Can deadlock if a command
    # floods stderr past the pipe buffer; swap to select/threads if that bites.
    proc = subprocess.Popen(
        command, shell=True, cwd=".", text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    out_lines = []
    for line in proc.stdout:
        console.print(line, end="")
        out_lines.append(line)
    err = proc.stderr.read()
    proc.wait()
    return {
        "exit_code": proc.returncode,
        "stdout": "".join(out_lines),
        "stderr": err,
    }
