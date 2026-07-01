import re
from pathlib import Path

from freecode import ollama_client, parser

PLAN_SYSTEM = (
    "You are a planning assistant for a coding task. Respond with a numbered "
    "step-by-step plan only, one step per line like '1. ...'. No code, no "
    "explanations, no preamble, no closing remarks.\n"
    "Grammar: caveman ultra. Drop articles and filler. Fragments over full "
    "sentences. Under six words per step, lowercase, no trailing period "
    "(e.g. 'list models', not 'Retrieve the current models available.').\n"
    "Every step names a concrete file, function, or action. Never a generic "
    "development phase. Banned as standalone steps: identify requirements, "
    "gather libraries, analyze codebase, review, test, push. These describe "
    "how any task is done, not what this task needs.\n"
    "Max four steps total regardless of task size. Merge review, test, and "
    "push into one final step labelled 'verify and commit'. Collapse related "
    "actions into one step (create file and add content = one step)."
)

_NUM = re.compile(r"^\s*\d+[.)]\s*(.+)")


def _parse_steps(text):
    steps = [m.group(1).strip() for line in text.splitlines() if (m := _NUM.match(line))]
    if steps:
        return steps
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def generate_plan(task, model, write=True, extra_system=""):
    system = parser.with_skills(PLAN_SYSTEM)
    if extra_system:
        system = extra_system + "\n\n" + system
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},
    ]
    text = "".join(ollama_client.chat(model, messages, stream=False))
    steps = _parse_steps(text)
    if write and steps:
        body = "# Plan\n\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)) + "\n"
        Path("plan.md").write_text(body)
    return steps
