import re
from pathlib import Path

from freecode import ollama_client

PLAN_SYSTEM = (
    "You are a planning assistant for a coding task. Respond with a numbered "
    "step-by-step plan only, one step per line like '1. ...'. No code, no "
    "explanations, no preamble, no closing remarks."
)

_NUM = re.compile(r"^\s*\d+[.)]\s*(.+)")


def _parse_steps(text):
    steps = [m.group(1).strip() for line in text.splitlines() if (m := _NUM.match(line))]
    if steps:
        return steps
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def generate_plan(task, model, write=True):
    messages = [
        {"role": "system", "content": PLAN_SYSTEM},
        {"role": "user", "content": task},
    ]
    text = "".join(ollama_client.chat(model, messages, stream=False))
    steps = _parse_steps(text)
    if write and steps:
        body = "# Plan\n\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)) + "\n"
        Path("plan.md").write_text(body)
    return steps
