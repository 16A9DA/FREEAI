import re
from pathlib import Path

from freecode import ollama_client

_MENTION = re.compile(r"@(\S+)")
_SLASH = re.compile(r"/(\w*)$")

# An @ mention can mean "write output here", told apart from a read
# reference by the verb context around it.
_READ_CUES = ("using", "based on", "like", "similar to", "referencing")
_WRITE_VERBS = ("create", "make", "build", "write", "add", "put")
_SHORTHAND = {"documents", "desktop", "downloads", "pictures"}


def resolve_write_target(mention):
    """Resolve a write-target mention to an absolute Path. Shorthand folder names
    map under the home dir; anything path-shaped is used as given."""
    m = mention.rstrip("/.,)")
    if m.lower() in _SHORTHAND:
        return Path.home() / m.capitalize()
    p = Path(m).expanduser()
    return p if p.is_absolute() else (Path.cwd() / p).resolve()


def detect_write_target(text):
    """First @ mention acting as a write target, else None.
    Returns (raw_mention, resolved_path). Defaults to read reference (None) when
    no verb signal, preserving prior read-reference behavior."""
    for m in _MENTION.finditer(text):
        raw = m.group(1)
        before = text[:m.start()].strip().lower()
        after = text[m.end():].strip().lower()
        if any(before.endswith(cue) for cue in _READ_CUES):
            continue
        first = before == ""
        verb_after = any(after == v or after.startswith(v + " ") for v in _WRITE_VERBS)
        if first or verb_after:
            return raw, resolve_write_target(raw)
    return None


def parse_slash_commands(text, available_commands):
    """Return commands whose name starts with the slash-token trailing the cursor, or []."""
    m = _SLASH.search(text)
    if not m:
        return []
    prefix = m.group(1).lower()
    return [c for c in available_commands if c["name"].startswith(prefix)]

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


def load_skills():
    d = Path.cwd()
    for parent in [d, *d.parents]:
        f = parent / ".freeai"
        if f.is_file():
            return f.read_text().strip()
    return ""


def with_skills(base_system):
    skills = load_skills()
    if not skills:
        return base_system
    return f"Project rules (follow strictly):\n{skills}\n\n{base_system}"


def demo():
    here = Path(__file__).parent
    out = parse_mentions(f"check @{here.name}/parser.py and @{here.name}/")
    assert "Referenced context" in out
    assert "parse_mentions" in out  # file content pulled in
    assert "tools/" in out or "tools" in out  # folder tree pulled in
    assert parse_mentions("no mentions here") == "no mentions here"
    base = "BASE"
    assert with_skills(base) == base or "Project rules" in with_skills(base)
    cmds = [{"name": "model", "description": "d", "args_hint": ""}, {"name": "config", "description": "d", "args_hint": ""}]
    assert [c["name"] for c in parse_slash_commands("do /mo", cmds)] == ["model"]
    assert parse_slash_commands("no slash", cmds) == []
    assert parse_slash_commands("/", cmds) == cmds
    print("ok")


if __name__ == "__main__":
    demo()
