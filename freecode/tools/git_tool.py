from git import Repo
from git.exc import GitError, InvalidGitRepositoryError
from rich.console import Console
from rich.table import Table

from freecode import ui

console = Console()


def _repo():
    return Repo(".", search_parent_directories=True)


def git_status():
    try:
        return _repo().git.status()
    except InvalidGitRepositoryError:
        return "Error: not a git repo"


def git_diff(filepath=None):
    try:
        return _repo().git.diff(filepath) if filepath else _repo().git.diff()
    except (InvalidGitRepositoryError, GitError) as e:
        return f"Error: {e}"


def git_add(paths=None):
    try:
        repo = _repo()
        if paths:
            repo.git.add(paths)
            return f"Staged {paths}"
        repo.git.add(A=True)
        return "Staged all changes"
    except (InvalidGitRepositoryError, GitError) as e:
        return f"Error: {e}"


def git_commit(message):
    try:
        repo = _repo()
        repo.git.add(A=True)
        repo.index.commit(message)
        return f"Committed: {message}"
    except (InvalidGitRepositoryError, GitError) as e:
        return f"Error: {e}"


def git_push():
    try:
        repo = _repo()
        remote = repo.remote()
        branch = repo.active_branch
    except (InvalidGitRepositoryError, GitError, ValueError) as e:
        return f"Error: {e}"
    console.print(f"[yellow]Push[/yellow] {branch} -> {remote.name} ({remote.url})")
    if not ui.ask_yes_no("Push?", default=False):
        return "Cancelled: not pushed"
    try:
        remote.push()
        return f"Pushed {branch} to {remote.name}"
    except GitError as e:
        return f"Error: {e}"


def git_log(n=10):
    try:
        repo = _repo()
        commits = list(repo.iter_commits(max_count=n))
    except (InvalidGitRepositoryError, GitError) as e:
        return f"Error: {e}"
    table = Table(title=f"last {len(commits)} commits")
    table.add_column("hash", style="yellow")
    table.add_column("author", style="cyan")
    table.add_column("date")
    table.add_column("message", overflow="fold")
    for c in commits:
        table.add_row(
            c.hexsha[:7],
            c.author.name,
            c.committed_datetime.strftime("%Y-%m-%d %H:%M"),
            str(c.summary),
        )
    console.print(table)
    return "\n".join(f"{c.hexsha[:7]} {c.summary}" for c in commits)
