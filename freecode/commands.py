from prompt_toolkit.completion import Completer, Completion

from freecode import skills

_SUBCOMMANDS = [
    {"name": "model", "description": "Download, list, switch, and remove local models.", "args_hint": "list|pull|use|remove <name>"},
    {"name": "config", "description": "View or change settings.", "args_hint": "[--assistance] [--model] [--temperature] [--context]"},
    {"name": "history", "description": "Show past tasks and token usage.", "args_hint": ""},
    {"name": "clear", "description": "Erase the saved session memory.", "args_hint": "[--history]"},
    {"name": "index", "description": "Build or refresh the search index for the current project.", "args_hint": ""},
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


class SlashCompleter(Completer):
    """Live '/' popup: matches anywhere in the input, shows up to 6, truncated one-liners."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        idx = text.rfind("/")
        if idx == -1 or (idx > 0 and not text[idx - 1].isspace()):
            return
        prefix = text[idx + 1:]
        if " " in prefix:
            return  # command already confirmed, popup disappears
        matches = [c for c in get_available_commands() if c["name"].startswith(prefix.lower())]
        for c in matches[:6]:
            desc = c["description"][:60]
            hint = f" {c['args_hint']}" if c["args_hint"] else ""
            yield Completion(
                c["name"], start_position=-len(prefix),
                display=f"/{c['name']}{hint}", display_meta=desc,
            )
