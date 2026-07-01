"""Command menu source + prompt_toolkit completer (slash menu, mode picker, model picker)."""
from prompt_toolkit.completion import Completer, Completion

from freecode import skills
from freecode.config import ASSISTANCE_LEVELS, load_config

_SUBCOMMANDS = [
    {"name": "model", "description": "Download, list, switch, and remove local models.", "args_hint": "list|pull|use|remove <name>"},
    {"name": "config", "description": "View or change settings.", "args_hint": "[--assistance] [--model] [--temperature] [--context]"},
    {"name": "history", "description": "Show past tasks and token usage.", "args_hint": ""},
    {"name": "clear", "description": "Erase the saved session memory.", "args_hint": "[--history]"},
    {"name": "index", "description": "Build or refresh the search index for the current project.", "args_hint": ""},
    {"name": "mode", "description": "Set assistance mode.", "args_hint": "low|full|ultra"},
]

_SESSION_COMMANDS = [
    {"name": "done", "description": "End the session early and show the token dashboard.", "args_hint": ""},
]


def get_available_commands():
    skill_cmds = [
        {"name": s["name"], "description": s["description"], "args_hint": ""}
        for s in skills.list_skills()
    ]
    return skill_cmds + _SUBCOMMANDS + _SESSION_COMMANDS


class CommandCompleter(Completer):
    """Live dropdown: `mode ` picks a level, `model `/`switch` picks a pulled model, `/` lists commands."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        low = text.lower()

        if low.startswith(("mode ", "assistance ")):
            prefix = text.split(" ", 1)[1]
            for lvl in ASSISTANCE_LEVELS:
                if lvl.startswith(prefix.lower()):
                    yield Completion(lvl, start_position=-len(prefix), display=lvl, display_meta="assistance mode")
            return

        if low.startswith(("model ", "switch model to ")):
            prefix = text.rsplit(" ", 1)[-1]
            for name in load_config().get("pulled_models", []):
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix), display=name, display_meta="model")
            return

        idx = text.rfind("/")
        if idx == -1 or (idx > 0 and not text[idx - 1].isspace()):
            return
        prefix = text[idx + 1:]
        if " " in prefix:
            return
        matches = [c for c in get_available_commands() if c["name"].startswith(prefix.lower())]
        for c in matches[:6]:
            hint = f" {c['args_hint']}" if c["args_hint"] else ""
            yield Completion(
                c["name"], start_position=-len(prefix),
                display=f"/{c['name']}{hint}", display_meta=c["description"][:60],
            )
