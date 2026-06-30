import re
from pathlib import Path

from freecode import ollama_client

_MENTION = re.compile(r"@(\S+)")

_SUMMARY_SYSTEM = (
    "Summarise this file and identify the parts most relevant to a coding task. "
    "Be concise. No preamble."
)


def _tree(root, max_depth=2):
    lines = []
    root = root.resolve()
    for path in sorted(root.rglob("*")):
        depth = len(path.relative_to(root).parts)
        if depth > max_depth:
            continue
        indent = "  " * (depth - 1)
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{indent}{path.name}{suffix}")
    return "\n".join(lines)


def _summarise(content, model):
    messages = [
        {"role": "system", "content": _SUMMARY_SYSTEM},
        {"role": "user", "content": content[:8000]},
    ]
    return "".join(ollama_client.chat(model, messages, stream=False))


def parse_mentions(text, model=None):
    blocks = []
    for raw in _MENTION.findall(text):
        p = Path.cwd() / raw.rstrip("/.,)")
        if p.is_file():
            content = p.read_text(errors="replace")
            body = _summarise(content, model) if model else content[:8000]
            blocks.append(f"### File @{raw}\n{body}")
        elif p.is_dir():
            blocks.append(f"### Folder @{raw}\n{_tree(p)}")
    if not blocks:
        return text
    return text + "\n\n## Referenced context\n\n" + "\n\n".join(blocks)


def demo():
    here = Path(__file__).parent
    out = parse_mentions(f"check @{here.name}/parser.py and @{here.name}/")
    assert "Referenced context" in out
    assert "parse_mentions" in out  # file content pulled in
    assert "tools/" in out or "tools" in out  # folder tree pulled in
    assert parse_mentions("no mentions here") == "no mentions here"
    print("ok")


if __name__ == "__main__":
    demo()
